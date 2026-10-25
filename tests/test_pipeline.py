"""
End-to-end integration test for the extraction pipeline.
"""

import json
import tempfile
import unittest
from pathlib import Path

from config import Config
from create_sample_workbook import create_sample_workbook
from main import run_pipeline


class TestPipelineE2E(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.excel_path = self.temp_path / "test_wb.xlsx"
        self.output_json = self.temp_path / "out.json"
        self.review_json = self.temp_path / "review.json"

        # Generate sample workbook in temp directory
        create_sample_workbook(str(self.excel_path))
        self.config = Config.load()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pipeline_execution(self):
        run_pipeline(
            input_file=self.excel_path,
            output_file=self.output_json,
            review_file=self.review_json,
            config=self.config
        )

        self.assertTrue(self.output_json.exists())
        self.assertTrue(self.review_json.exists())

        with open(self.output_json, "r", encoding="utf-8") as f:
            records = json.load(f)

        self.assertEqual(len(records), 25)

        # Check prompt illustration record: 1234678
        rec_1007 = next((r for r in records if r["material_code"] == "1234678"), None)
        self.assertIsNotNone(rec_1007)
        self.assertEqual(rec_1007["brand"], "pmc")
        self.assertEqual(rec_1007["model"], "23445")
        self.assertIsNone(rec_1007["manufacturer"])
        self.assertEqual(rec_1007["size"], "3x3")
        self.assertEqual(rec_1007["additional"], "etc.")

        # Check review report
        with open(self.review_json, "r", encoding="utf-8") as f:
            review_data = json.load(f)

        summary = review_data["summary"]
        self.assertEqual(summary["total_materials_processed"], 25)
        self.assertEqual(summary["unrecognized_group_records_count"], 1)
        self.assertEqual(summary["ambiguous_extractions_count"], 1)


if __name__ == "__main__":
    unittest.main()
