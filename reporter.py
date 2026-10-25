"""
Review reporter and metrics tracker.
Tracks unrecognized groups, ambiguous values, unmatched text, and generates
comprehensive processing summaries and reports in JSON and Markdown formats.
"""

from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class UnrecognizedGroupItem:
    material_code: str
    group_number: Optional[str]
    short_description: Optional[str]
    long_description: Optional[str]
    reason: str


@dataclass
class AmbiguousFieldItem:
    material_code: str
    group_number: str
    field_name: str
    source_text: str
    candidate_values: List[str]
    reason: str


@dataclass
class UnmatchedTextItem:
    material_code: str
    group_number: str
    unmatched_text: str
    target_field: str  # 'additional' or 'unmatched_text'


class ReviewReport:
    """Collects review issues and summary statistics during pipeline execution."""

    def __init__(self):
        self.total_materials_processed: int = 0
        self.total_groups_encountered: set[str] = set()
        self.total_fields_extracted: int = 0
        self.total_fields_null: int = 0

        self.unrecognized_groups: List[UnrecognizedGroupItem] = []
        self.ambiguous_extractions: List[AmbiguousFieldItem] = []
        self.unmatched_items: List[UnmatchedTextItem] = []

    def record_unrecognized_group(
        self,
        material_code: str,
        group_number: Optional[str],
        short_desc: Optional[str],
        long_desc: Optional[str],
        reason: Optional[str] = None
    ) -> None:
        if group_number:
            self.total_groups_encountered.add(str(group_number))
        self.unrecognized_groups.append(
            UnrecognizedGroupItem(
                material_code=material_code,
                group_number=group_number,
                short_description=short_desc,
                long_description=long_desc,
                reason=reason or f"Group '{group_number}' does not exist in Standardisation sheet."
            )
        )

    def record_ambiguity(
        self,
        material_code: str,
        group_number: str,
        field_name: str,
        source_text: str,
        candidate_values: List[str],
        reason: str
    ) -> None:
        self.ambiguous_extractions.append(
            AmbiguousFieldItem(
                material_code=material_code,
                group_number=group_number,
                field_name=field_name,
                source_text=source_text,
                candidate_values=candidate_values,
                reason=reason
            )
        )

    def record_unmatched_text(
        self,
        material_code: str,
        group_number: str,
        unmatched_text: str,
        target_field: str
    ) -> None:
        self.unmatched_items.append(
            UnmatchedTextItem(
                material_code=material_code,
                group_number=group_number,
                unmatched_text=unmatched_text,
                target_field=target_field
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_materials_processed": self.total_materials_processed,
                "total_unique_groups_encountered": len(self.total_groups_encountered),
                "unrecognized_group_records_count": len(self.unrecognized_groups),
                "ambiguous_extractions_count": len(self.ambiguous_extractions),
                "records_with_unmatched_text_count": len(self.unmatched_items),
                "total_field_values_extracted": self.total_fields_extracted,
                "total_fields_left_null": self.total_fields_null,
            },
            "unrecognized_groups": [asdict(item) for item in self.unrecognized_groups],
            "ambiguous_extractions": [asdict(item) for item in self.ambiguous_extractions],
            "unmatched_descriptions": [asdict(item) for item in self.unmatched_items],
        }

    def write_json(self, output_path: str | Path) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def generate_text_summary(self) -> str:
        s = self.to_dict()["summary"]
        lines = [
            "=" * 60,
            "               PROCESSING REVIEW SUMMARY",
            "=" * 60,
            f"Total Materials Processed:          {s['total_materials_processed']}",
            f"Unique Groups Encountered:          {s['total_unique_groups_encountered']}",
            f"Materials with Unrecognized Group:  {s['unrecognized_group_records_count']}",
            f"Ambiguous Extractions Flagged:      {s['ambiguous_extractions_count']}",
            f"Materials with Unmatched Text:      {s['records_with_unmatched_text_count']}",
            f"Successfully Populated Fields:      {s['total_field_values_extracted']}",
            f"Fields Remaining Null:              {s['total_fields_left_null']}",
            "=" * 60
        ]
        if self.unrecognized_groups:
            lines.append("\n[!] UNRECOGNIZED GROUPS:")
            for item in self.unrecognized_groups[:5]:
                lines.append(f"  - Material {item.material_code}: Group '{item.group_number}' -> {item.reason}")
            if len(self.unrecognized_groups) > 5:
                lines.append(f"  ... and {len(self.unrecognized_groups) - 5} more.")

        if self.ambiguous_extractions:
            lines.append("\n[?] AMBIGUOUS EXTRACTIONS (Left as null):")
            for item in self.ambiguous_extractions[:5]:
                lines.append(
                    f"  - Material {item.material_code} [{item.group_number}]: "
                    f"Field '{item.field_name}' -> {item.reason} (Candidates: {item.candidate_values})"
                )
            if len(self.ambiguous_extractions) > 5:
                lines.append(f"  ... and {len(self.ambiguous_extractions) - 5} more.")

        return "\n".join(lines)
