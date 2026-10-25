"""
Configuration manager for Excel to Structured JSON extraction.
Loads and validates configuration from JSON files and provides structured lookup
for aliases, regex patterns, group-specific rules, and column mappings.
"""

from __future__ import annotations
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent / "default_config.json"


class Config:
    def __init__(self, raw_config: Dict[str, Any]):
        self.raw = raw_config
        self.sheet_mappings: Dict[str, List[str]] = raw_config.get("sheet_mappings", {})
        self.column_mappings: Dict[str, Dict[str, List[str]]] = raw_config.get("column_mappings", {})
        self.options: Dict[str, Any] = raw_config.get("options", {})
        self.delimiters: List[str] = raw_config.get("delimiters", [";", ",", "\n", "|", "/"])
        self.key_value_separators: List[str] = raw_config.get("key_value_separators", [":", "=", " - ", " -- "])
        self.global_aliases: Dict[str, List[str]] = raw_config.get("global_aliases", {})
        self.patterns: Dict[str, List[str]] = raw_config.get("patterns", {})
        self.known_values: Dict[str, List[str]] = raw_config.get("known_values", {})
        self.group_rules: Dict[str, Dict[str, Any]] = raw_config.get("group_rules", {})

        # Precompile regex patterns for performance and validation
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        for field, pat_list in self.patterns.items():
            compiled = []
            for pat in pat_list:
                try:
                    compiled.append(re.compile(pat, re.IGNORECASE))
                except re.error as e:
                    logger.warning(f"Invalid regex pattern for {field}: {pat} - {e}")
            self._compiled_patterns[field] = compiled

        # Group-specific compiled patterns
        self._compiled_group_patterns: Dict[str, Dict[str, List[re.Pattern]]] = {}
        for grp, rules in self.group_rules.items():
            self._compiled_group_patterns[str(grp)] = {}
            grp_pats = rules.get("patterns", {})
            for field, pat_or_list in grp_pats.items():
                p_list = [pat_or_list] if isinstance(pat_or_list, str) else pat_or_list
                comp = []
                for p in p_list:
                    try:
                        comp.append(re.compile(p, re.IGNORECASE))
                    except re.error as e:
                        logger.warning(f"Invalid group {grp} regex pattern for {field}: {p} - {e}")
                self._compiled_group_patterns[str(grp)][field] = comp

    @classmethod
    def load(cls, config_path: Optional[str | Path] = None) -> Config:
        target_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        if not target_path.exists():
            if config_path:
                logger.warning(f"Config path {target_path} not found. Falling back to default: {DEFAULT_CONFIG_PATH}")
                target_path = DEFAULT_CONFIG_PATH
            if not target_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {target_path}")

        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)

    def get_sheet_candidates(self, sheet_type: str) -> List[str]:
        return self.sheet_mappings.get(sheet_type, [])

    def get_column_candidates(self, sheet_type: str, column_role: str) -> List[str]:
        return self.column_mappings.get(sheet_type, {}).get(column_role, [])

    def get_aliases_for_field(self, field_name: str, group_number: Optional[str] = None) -> List[str]:
        """
        Get field aliases. If group-specific aliases exist, they override or extend global aliases.
        """
        canonical = field_name.strip().lower()
        aliases = list(self.global_aliases.get(canonical, []))
        if canonical not in aliases:
            aliases.append(canonical)

        # Check group-specific rules
        if group_number and str(group_number) in self.group_rules:
            grp_rules = self.group_rules[str(group_number)]
            grp_aliases = grp_rules.get("aliases", {}).get(canonical)
            if grp_aliases:
                for a in grp_aliases:
                    if a not in aliases:
                        aliases.append(a)

        return aliases

    def get_compiled_patterns_for_field(self, field_name: str, group_number: Optional[str] = None) -> List[re.Pattern]:
        canonical = field_name.strip().lower()
        patterns: List[re.Pattern] = []

        # Group-specific patterns first
        if group_number and str(group_number) in self._compiled_group_patterns:
            grp_pats = self._compiled_group_patterns[str(group_number)].get(canonical, [])
            patterns.extend(grp_pats)

        # Global patterns
        patterns.extend(self._compiled_patterns.get(canonical, []))
        return patterns

    def get_known_values_for_field(self, field_name: str, group_number: Optional[str] = None) -> Set[str]:
        canonical = field_name.strip().lower()
        vals = set(v.strip().upper() for v in self.known_values.get(canonical, []))

        if group_number and str(group_number) in self.group_rules:
            grp_known = self.group_rules[str(group_number)].get("known_values", {}).get(canonical, [])
            vals.update(v.strip().upper() for v in grp_known)

        return vals

    def get_group_rule(self, group_number: Optional[str]) -> Optional[Dict[str, Any]]:
        if not group_number:
            return None
        return self.group_rules.get(str(group_number))

    def is_positional_allowed(self, group_number: Optional[str]) -> bool:
        if not group_number or str(group_number) not in self.group_rules:
            return False
        return bool(self.group_rules[str(group_number)].get("allow_positional_extraction", False))

    def get_positional_mapping(self, group_number: Optional[str]) -> List[str]:
        if not group_number or str(group_number) not in self.group_rules:
            return []
        return self.group_rules[str(group_number)].get("positional_mapping", [])

    @property
    def fallback_to_short_desc(self) -> bool:
        return bool(self.options.get("fallback_to_short_desc", False))

    @property
    def include_unmatched_property_if_no_additional(self) -> bool:
        return bool(self.options.get("include_unmatched_property_if_no_additional", True))
