"""
Unit tests for deterministic MaterialExtractor logic.
"""

import unittest
from config import Config
from extractor import MaterialExtractor
from group_parser import GroupDefinition
from reporter import ReviewReport


class TestExtractor(unittest.TestCase):
    def setUp(self):
        self.config = Config.load()
        self.report = ReviewReport()
        self.extractor = MaterialExtractor(self.config, self.report)

    def test_group_1007_illustration_exact(self):
        group_1007 = GroupDefinition(
            group_number="1007",
            category_name="PUMPS & COMPONENTS",
            raw_columns="brand; model; manufacturer; size; additional",
            fields=["brand", "model", "manufacturer", "size", "additional"]
        )

        record = self.extractor.process_material(
            material_code="1234678",
            group_number="1007",
            short_desc="PUMP SPARES PMC 3X3",
            long_desc="pmc,23445,3x3 etc.",
            group_def=group_1007
        )

        self.assertEqual(record["material_code"], "1234678")
        self.assertEqual(record["group_number"], "1007")
        self.assertEqual(record["brand"], "pmc")
        self.assertEqual(record["model"], "23445")
        self.assertIsNone(record["manufacturer"])
        self.assertEqual(record["size"], "3x3")
        self.assertEqual(record["additional"], "etc.")

    def test_labeled_key_value_extraction(self):
        group_1025 = GroupDefinition(
            group_number="1025",
            category_name="VALVES & PIPING",
            raw_columns="brand; drawing_number; manufacturer; material; size; specification; additional",
            fields=["brand", "drawing_number", "manufacturer", "material", "size", "specification", "additional"]
        )

        record = self.extractor.process_material(
            material_code="2001001",
            group_number="1025",
            short_desc="GATE VALVE",
            long_desc="MAKE: L&T; SIZE: 2 INCH; MATL: WCB; DRG NO: DRG-VALVE-9981; SPEC: ASME B16.34; LEVER OPERATED",
            group_def=group_1025
        )

        self.assertEqual(record["brand"], "L&T")
        self.assertEqual(record["drawing_number"], "DRG-VALVE-9981")
        self.assertEqual(record["size"], "2 INCH")
        self.assertEqual(record["material"], "WCB")
        self.assertEqual(record["specification"], "ASME B16.34")
        self.assertEqual(record["additional"], "LEVER OPERATED")
        self.assertIsNone(record["manufacturer"])

    def test_unlabeled_numeric_ambiguity_flagged(self):
        group_1010 = GroupDefinition(
            group_number="1010",
            category_name="BEARINGS",
            raw_columns="brand; model; part_number; size; additional",
            fields=["brand", "model", "part_number", "size", "additional"]
        )

        # 6205 could be model or part_number
        record = self.extractor.process_material(
            material_code="3001002",
            group_number="1010",
            short_desc="BEARING",
            long_desc="MAKE: SKF, 6205, 25x52x15 mm",
            group_def=group_1010
        )

        self.assertEqual(record["brand"], "SKF")
        self.assertIsNone(record["model"])
        self.assertIsNone(record["part_number"])
        self.assertEqual(record["size"], "25x52x15 mm")
        self.assertTrue(len(self.report.ambiguous_extractions) > 0)
        self.assertIn("6205", self.report.ambiguous_extractions[0].candidate_values)

    def test_unrecognized_group_handling(self):
        record = self.extractor.process_material(
            material_code="9999001",
            group_number="9999",
            short_desc="UNKNOWN",
            long_desc="SOME LONG DESCRIPTION",
            group_def=None
        )

        self.assertEqual(record["material_code"], "9999001")
        self.assertEqual(record["group_number"], "9999")
        self.assertEqual(record["unmatched_text"], "SOME LONG DESCRIPTION")
        self.assertEqual(len(self.report.unrecognized_groups), 1)
        self.assertEqual(self.report.unrecognized_groups[0].material_code, "9999001")


if __name__ == "__main__":
    unittest.main()
