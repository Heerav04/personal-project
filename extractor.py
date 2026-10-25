"""
Deterministic extraction engine for material master records.
Extracts structured fields from long descriptions using configurable aliases,
patterns, known values, and group-specific rules without LLMs or machine learning.
"""

from __future__ import annotations
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from config import Config
from group_parser import GroupDefinition
from normalizer import (
    clean_leftover_text,
    normalize_whitespace,
    parse_key_value_segment,
    split_into_segments,
)
from reporter import ReviewReport
from workbook_loader import normalize_header

logger = logging.getLogger(__name__)


class MaterialExtractor:
    """
    Performs deterministic, conservative extraction on material records according
    to the group's Standard Columns and configuration rules.
    """

    def __init__(self, config: Config, review_report: ReviewReport):
        self.config = config
        self.report = review_report

    def process_material(
        self,
        material_code: str,
        group_number: Optional[str],
        short_desc: Optional[str],
        long_desc: Optional[str],
        group_def: Optional[GroupDefinition],
        fallback_short_desc: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Processes a single material row and returns a structured record.
        """
        self.report.total_materials_processed += 1
        mat_code_str = str(material_code).strip() if material_code is not None else "UNKNOWN"
        group_num_str = str(group_number).strip() if group_number is not None else ""
        if group_num_str.endswith(".0") and group_num_str[:-2].isdigit():
            group_num_str = group_num_str[:-2]

        if group_num_str:
            self.report.total_groups_encountered.add(group_num_str)

        # Base output record
        record: Dict[str, Any] = {
            "material_code": mat_code_str,
            "group_number": group_num_str if group_num_str else None,
            "short_description": short_desc,
            "long_description": long_desc,
        }

        # Case 1: Unrecognized / Missing group in Standardisation
        if group_def is None:
            self.report.record_unrecognized_group(
                material_code=mat_code_str,
                group_number=group_num_str or None,
                short_desc=short_desc,
                long_desc=long_desc,
                reason=f"Group '{group_num_str}' has no matching row in Standardisation sheet."
            )
            # Retain original text in unmatched_text for unmapped groups
            if long_desc:
                record["unmatched_text"] = long_desc
            return record

        # Initialize all standard fields defined for this group as None
        for f in group_def.fields:
            record[f] = None

        desc_to_parse = long_desc or ""

        # Step 1: Delimit description into mutable segment buffers
        grp_rules = self.config.get_group_rule(group_num_str)
        delims = grp_rules.get("delimiters") if grp_rules and "delimiters" in grp_rules else self.config.delimiters
        raw_segments = split_into_segments(desc_to_parse, delimiters=delims)
        # We track each segment as a string buffer so substrings can be cleanly consumed
        segment_buffers: List[str] = [s for s in raw_segments]

        # Track candidate field values: field_name -> list of candidate values
        field_candidates: Dict[str, List[str]] = {f: [] for f in group_def.fields}

        # Step 2: Labeled Key-Value Extraction (highest confidence)
        self._extract_labeled_key_values(
            segment_buffers=segment_buffers,
            group_def=group_def,
            group_num_str=group_num_str,
            mat_code_str=mat_code_str,
            field_candidates=field_candidates
        )

        # Step 3: Pattern & Known Value Extraction (e.g. Dimensions, Sizes, Standard Materials)
        self._extract_patterns_and_known_values(
            segment_buffers=segment_buffers,
            group_def=group_def,
            group_num_str=group_num_str,
            mat_code_str=mat_code_str,
            field_candidates=field_candidates
        )

        # Step 4: Group-Specific Rules & Positional Extraction (if enabled for this group)
        if self.config.is_positional_allowed(group_num_str):
            self._extract_positional(
                segment_buffers=segment_buffers,
                group_def=group_def,
                group_num_str=group_num_str,
                mat_code_str=mat_code_str,
                field_candidates=field_candidates
            )
        else:
            # Check for ambiguous unlabeled numeric tokens among remaining segments
            self._check_unlabeled_numeric_ambiguity(
                segment_buffers=segment_buffers,
                group_def=group_def,
                group_num_str=group_num_str,
                mat_code_str=mat_code_str
            )

        # Step 5: Optional fallback to short description if configured
        use_fallback = fallback_short_desc if fallback_short_desc is not None else self.config.fallback_to_short_desc
        if use_fallback and short_desc:
            self._fallback_to_short_description(
                short_desc=short_desc,
                group_def=group_def,
                group_num_str=group_num_str,
                mat_code_str=mat_code_str,
                field_candidates=field_candidates
            )

        # Step 6: Commit candidates to record and handle intra-field conflicts
        for f in group_def.fields:
            if f == "additional":
                continue  # Handled in step 7

            cands = field_candidates.get(f, [])
            if not cands:
                record[f] = None
                self.report.total_fields_null += 1
            elif len(cands) == 1:
                record[f] = cands[0]
                self.report.total_fields_extracted += 1
            else:
                # Check if multiple candidates have the exact same value
                distinct_vals = list(dict.fromkeys(cands))
                if len(distinct_vals) == 1:
                    record[f] = distinct_vals[0]
                    self.report.total_fields_extracted += 1
                else:
                    # Conflicting values for the same field -> ambiguity!
                    record[f] = None
                    self.report.total_fields_null += 1
                    self.report.record_ambiguity(
                        material_code=mat_code_str,
                        group_number=group_num_str,
                        field_name=f,
                        source_text=desc_to_parse,
                        candidate_values=distinct_vals,
                        reason=f"Multiple conflicting values extracted for field '{f}'."
                    )

        # Step 7: Unmatched text handling from remaining segment buffers
        leftover_pieces = []
        for buf in segment_buffers:
            cleaned_buf = clean_leftover_text(buf)
            if cleaned_buf:
                leftover_pieces.append(cleaned_buf)

        leftover_clean = clean_leftover_text(", ".join(leftover_pieces))

        if leftover_clean:
            if group_def.has_additional:
                record["additional"] = leftover_clean
                self.report.record_unmatched_text(
                    material_code=mat_code_str,
                    group_number=group_num_str,
                    unmatched_text=leftover_clean,
                    target_field="additional"
                )
            else:
                if self.config.include_unmatched_property_if_no_additional:
                    record["unmatched_text"] = leftover_clean
                self.report.record_unmatched_text(
                    material_code=mat_code_str,
                    group_number=group_num_str,
                    unmatched_text=leftover_clean,
                    target_field="unmatched_text"
                )

        return record

    def _extract_labeled_key_values(
        self,
        segment_buffers: List[str],
        group_def: GroupDefinition,
        group_num_str: str,
        mat_code_str: str,
        field_candidates: Dict[str, List[str]]
    ) -> None:
        """Extract key-value pairs where key matches a known alias for a group field."""
        seps = self.config.key_value_separators

        for idx, seg in enumerate(segment_buffers):
            if not seg:
                continue

            kv = parse_key_value_segment(seg, separators=seps)
            if not kv:
                continue

            raw_key, raw_val = kv
            norm_key = normalize_header(raw_key)
            if not norm_key or not raw_val:
                continue

            # Find matching fields in group definition
            matched_fields: List[str] = []
            for f in group_def.fields:
                aliases = self.config.get_aliases_for_field(f, group_number=group_num_str)
                norm_aliases = [normalize_header(a) for a in aliases]
                if norm_key in norm_aliases:
                    matched_fields.append(f)

            if len(matched_fields) == 1:
                target_field = matched_fields[0]
                field_candidates[target_field].append(raw_val)
                segment_buffers[idx] = ""  # Fully consumed
            elif len(matched_fields) > 1:
                # Ambiguous label matching multiple fields
                segment_buffers[idx] = ""  # Consumed from unmatched text, but logged to review
                self.report.record_ambiguity(
                    material_code=mat_code_str,
                    group_number=group_num_str,
                    field_name=f"multiple ({', '.join(matched_fields)})",
                    source_text=seg,
                    candidate_values=[raw_val],
                    reason=f"Label '{raw_key}' matches multiple fields ({matched_fields}) in group."
                )

    def _extract_patterns_and_known_values(
        self,
        segment_buffers: List[str],
        group_def: GroupDefinition,
        group_num_str: str,
        mat_code_str: str,
        field_candidates: Dict[str, List[str]]
    ) -> None:
        """Extract physical dimensions, ratings, and known values, preserving segment remainders."""
        for idx in range(len(segment_buffers)):
            seg = segment_buffers[idx]
            if not seg:
                continue

            # 1. Size / Dimension Pattern
            if "size" in group_def.fields and not field_candidates["size"]:
                size_patterns = self.config.get_compiled_patterns_for_field("size", group_number=group_num_str)
                for pat in size_patterns:
                    m = pat.search(seg)
                    if m:
                        matched_val = m.group(0).strip()
                        field_candidates["size"].append(matched_val)
                        # Remove the matched portion from the segment buffer, preserving remainder
                        rem = seg[:m.start()] + " " + seg[m.end():]
                        segment_buffers[idx] = normalize_whitespace(rem)
                        seg = segment_buffers[idx]
                        break

            if not seg:
                continue

            # 2. Known Values (e.g. Material)
            for f in group_def.fields:
                if field_candidates[f]:
                    continue
                known = self.config.get_known_values_for_field(f, group_number=group_num_str)
                if not known:
                    continue

                seg_upper = seg.upper()
                # Check for exact or boundary match of known material/value
                matched_known = None
                for k_val in known:
                    # Match known value with word boundaries
                    k_pat = r"\b" + re.escape(k_val) + r"\b"
                    m = re.search(k_pat, seg_upper)
                    if m:
                        # Extract the actual case from seg
                        matched_known = seg[m.start():m.end()]
                        rem = seg[:m.start()] + " " + seg[m.end():]
                        segment_buffers[idx] = normalize_whitespace(rem)
                        seg = segment_buffers[idx]
                        break

                if matched_known:
                    field_candidates[f].append(matched_known)
                    break

            if not seg:
                continue

            # 3. Patterns for other patterned fields (voltage, power, speed, pressure)
            for f in group_def.fields:
                if f in ("size", "additional") or field_candidates[f]:
                    continue
                patterns = self.config.get_compiled_patterns_for_field(f, group_number=group_num_str)
                for pat in patterns:
                    m = pat.search(seg)
                    if m:
                        matched_val = m.group(0).strip()
                        field_candidates[f].append(matched_val)
                        rem = seg[:m.start()] + " " + seg[m.end():]
                        segment_buffers[idx] = normalize_whitespace(rem)
                        seg = segment_buffers[idx]
                        break
                if not seg:
                    break

    def _extract_positional(
        self,
        segment_buffers: List[str],
        group_def: GroupDefinition,
        group_num_str: str,
        mat_code_str: str,
        field_candidates: Dict[str, List[str]]
    ) -> None:
        """
        Extracts fields based on group-specific positional mapping and validation patterns.
        Used for groups where positional structures are explicitly authorized in configuration.
        """
        mapping = self.config.get_positional_mapping(group_num_str)
        if not mapping:
            return

        for target_field in mapping:
            if target_field not in group_def.fields:
                continue
            if field_candidates[target_field]:
                continue

            # Find the first available non-empty segment buffer
            found_idx = None
            found_val = None

            for idx, buf in enumerate(segment_buffers):
                clean_buf = clean_leftover_text(buf)
                if not clean_buf:
                    continue

                patterns = self.config.get_compiled_patterns_for_field(target_field, group_number=group_num_str)
                if patterns:
                    if any(p.search(clean_buf) for p in patterns):
                        found_idx = idx
                        found_val = clean_buf
                        break
                else:
                    found_idx = idx
                    found_val = clean_buf
                    break

            if found_idx is not None and found_val is not None:
                field_candidates[target_field].append(found_val)
                segment_buffers[found_idx] = ""

    def _check_unlabeled_numeric_ambiguity(
        self,
        segment_buffers: List[str],
        group_def: GroupDefinition,
        group_num_str: str,
        mat_code_str: str
    ) -> None:
        """
        Checks unconsumed segments for bare numeric tokens.
        If a number could belong to multiple fields (model, part_number, drawing_number),
        conservative rules require flagging ambiguity rather than guessing.
        """
        numeric_candidate_fields = [
            f for f in ("model", "part_number", "drawing_number")
            if f in group_def.fields
        ]

        if len(numeric_candidate_fields) <= 1:
            return

        for idx, buf in enumerate(segment_buffers):
            seg_clean = clean_leftover_text(buf)
            if not seg_clean:
                continue

            # If token looks purely numeric or alphanumeric code without label (e.g., '6205' or 'P-9872')
            if re.match(r"^[A-Za-z0-9\-_]{4,15}$", seg_clean) and any(c.isdigit() for c in seg_clean):
                self.report.record_ambiguity(
                    material_code=mat_code_str,
                    group_number=group_num_str,
                    field_name=f"ambiguous ({'/'.join(numeric_candidate_fields)})",
                    source_text=seg_clean,
                    candidate_values=[seg_clean],
                    reason=(
                        f"Unlabeled token '{seg_clean}' could be {', '.join(numeric_candidate_fields)}; "
                        f"left null per conservative extraction rule."
                    )
                )

    def _fallback_to_short_description(
        self,
        short_desc: str,
        group_def: GroupDefinition,
        group_num_str: str,
        mat_code_str: str,
        field_candidates: Dict[str, List[str]]
    ) -> None:
        """Secondary extraction pass on short description for still-empty fields."""
        unpopulated_fields = [f for f in group_def.fields if not field_candidates[f] and f != "additional"]
        if not unpopulated_fields:
            return

        short_buffers = split_into_segments(short_desc, delimiters=self.config.delimiters)

        # Try labeled extraction first
        self._extract_labeled_key_values(
            segment_buffers=short_buffers,
            group_def=group_def,
            group_num_str=group_num_str,
            mat_code_str=mat_code_str,
            field_candidates=field_candidates
        )

        # Try pattern & known value extraction
        self._extract_patterns_and_known_values(
            segment_buffers=short_buffers,
            group_def=group_def,
            group_num_str=group_num_str,
            mat_code_str=mat_code_str,
            field_candidates=field_candidates
        )
