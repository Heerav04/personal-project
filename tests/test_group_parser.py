"""
Unit tests for group parser and field name standardizer.
"""

import unittest
from group_parser import GroupDefinition, clean_field_name


class TestGroupParser(unittest.TestCase):
    def test_clean_field_name(self):
        self.assertEqual(clean_field_name("Drawing Number"), "drawing_number")
        self.assertEqual(clean_field_name("part-number"), "part_number")
        self.assertEqual(clean_field_name("  Size  "), "size")
        self.assertEqual(clean_field_name("Rating / Size"), "rating_size")

    def test_group_definition_has_additional(self):
        grp_with_add = GroupDefinition(
            group_number="1007",
            category_name="PUMPS",
            raw_columns="brand; model; additional",
            fields=["brand", "model", "additional"]
        )
        self.assertTrue(grp_with_add.has_additional)

        grp_without_add = GroupDefinition(
            group_number="1008",
            category_name="VALVES",
            raw_columns="brand; model; size",
            fields=["brand", "model", "size"]
        )
        self.assertFalse(grp_without_add.has_additional)


if __name__ == "__main__":
    unittest.main()
