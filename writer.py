"""
JSON writer module.
Writes structured material records and review reports to disk with clean formatting.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List
from reporter import ReviewReport


class JsonWriter:
    """Handles writing extracted records and reports to JSON files."""

    @staticmethod
    def write_records(
        records: List[Dict[str, Any]],
        output_path: str | Path,
        indent: int = 2
    ) -> Path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=indent, ensure_ascii=False)

        return out_path

    @staticmethod
    def write_review_report(
        report: ReviewReport,
        output_path: str | Path,
        indent: int = 2
    ) -> Path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=indent, ensure_ascii=False)

        return out_path
