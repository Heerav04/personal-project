"""
Unit tests for configuration loader and lookup functions.
"""

import unittest
from config import Config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.config = Config.load()

    def test_default_config_loaded(self):
        self.assertIsNotNone(self.config)
        self.assertIn("material_master_sheets", self.config.sheet_mappings)
        self.assertIn("standardisation_sheets", self.config.sheet_mappings)

    def test_alias_lookup(self):
        aliases = self.config.get_aliases_for_field("brand")
        self.assertIn("make", aliases)
        self.assertIn("brand", aliases)

    def test_group_specific_alias_override(self):
        # Group 1007 has specific alias for model: 'mod'
        aliases_1007 = self.config.get_aliases_for_field("model", group_number="1007")
        self.assertIn("mod", aliases_1007)

    def test_patterns_compilation(self):
        size_patterns = self.config.get_compiled_patterns_for_field("size")
        self.assertTrue(len(size_patterns) > 0)
        matched = any(p.search("10x20 mm") for p in size_patterns)
        self.assertTrue(matched)

    def test_known_values(self):
        materials = self.config.get_known_values_for_field("material")
        self.assertIn("SS316", materials)
        self.assertIn("BRASS", materials)


if __name__ == "__main__":
    unittest.main()
