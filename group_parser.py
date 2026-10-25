"""
Standardisation group definition parser.
Parses the Standardisation worksheet into structured group definitions with
standard fields parsed from semicolon-separated text.
"""

from __future__ import annotations
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from config import Config
from workbook_loader import WorkbookLoader

logger = logging.getLogger(__name__)


def clean_field_name(raw_name: str) -> str:
    """
    Standardize field names from Standard Columns (e.g., 'Drawing Number' -> 'drawing_number').
    Converts spaces, hyphens, and slashes to underscores, lowercases, and strips non-alphanumeric chars.
    """
    cleaned = raw_name.strip().lower()
    cleaned = re.sub(r"[\s\-_/]+", "_", cleaned)
    cleaned = re.sub(r"[^a-z0-9_]", "", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


@dataclass
class GroupDefinition:
    group_number: str
    category_name: Optional[str]
    raw_columns: str
    fields: List[str] = field(default_factory=list)
    has_additional: bool = False

    def __post_init__(self):
        self.has_additional = "additional" in self.fields


class GroupParser:
    """Parses Standardisation rows into an efficient group lookup cache."""

    def __init__(self, config: Config):
        self.config = config
        self.groups: Dict[str, GroupDefinition] = {}

    def parse_from_workbook(self, loader: WorkbookLoader) -> Dict[str, GroupDefinition]:
        sheet_name = loader.resolve_sheet_name("standardisation_sheets")
        col_mappings = self.config.column_mappings.get("standardisation", {})
        role_to_idx, raw_headers = loader.map_sheet_columns(sheet_name, col_mappings)

        if "group" not in role_to_idx:
            raise ValueError(
                f"Required column 'group' not found in '{sheet_name}'. "
                f"Candidate names: {col_mappings.get('group')}. Available headers: {raw_headers}"
            )
        if "standard_columns" not in role_to_idx:
            raise ValueError(
                f"Required column 'standard_columns' not found in '{sheet_name}'. "
                f"Candidate names: {col_mappings.get('standard_columns')}. Available headers: {raw_headers}"
            )

        self.groups.clear()

        for row_dict in loader.read_rows_as_dicts(sheet_name, role_to_idx):
            raw_grp = row_dict.get("group")
            if raw_grp is None or str(raw_grp).strip() == "":
                continue

            grp_key = str(raw_grp).strip()
            # If group is numeric float string like '1007.0', clean it
            if grp_key.endswith(".0") and grp_key[:-2].isdigit():
                grp_key = grp_key[:-2]

            cat_name = row_dict.get("category_name")
            raw_cols = row_dict.get("standard_columns") or ""

            # Split semicolon-separated list
            raw_field_list = [f.strip() for f in str(raw_cols).split(";") if f.strip()]
            cleaned_fields = []
            for f in raw_field_list:
                c_name = clean_field_name(f)
                if c_name and c_name not in cleaned_fields:
                    cleaned_fields.append(c_name)

            group_def = GroupDefinition(
                group_number=grp_key,
                category_name=cat_name,
                raw_columns=str(raw_cols),
                fields=cleaned_fields
            )

            if grp_key in self.groups:
                logger.warning(f"Duplicate group definition for group '{grp_key}'. Overwriting with later row.")

            self.groups[grp_key] = group_def

        return self.groups

    def get_group(self, group_number: Optional[str]) -> Optional[GroupDefinition]:
        if group_number is None:
            return None
        key = str(group_number).strip()
        if key.endswith(".0") and key[:-2].isdigit():
            key = key[:-2]
        return self.groups.get(key)
