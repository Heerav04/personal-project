"""
Unit tests for text normalization, segment splitting, and key-value parsing.
"""

import unittest
from normalizer import (
    clean_leftover_text,
    normalize_whitespace,
    parse_key_value_segment,
    split_into_segments,
)


class TestNormalizer(unittest.TestCase):
    def test_normalize_whitespace(self):
        text = "  Item   with \u00a0 non-breaking   space  \n and \t tabs  "
        self.assertEqual(normalize_whitespace(text), "Item with non-breaking space and tabs")

    def test_split_into_segments(self):
        text = "MAKE: SIEMENS; MODEL: 12345, SIZE: 2 INCH / SPEC: ASME"
        segments = split_into_segments(text, delimiters=[";", ",", "/"])
        self.assertEqual(len(segments), 4)
        self.assertEqual(segments[0], "MAKE: SIEMENS")
        self.assertEqual(segments[1], "MODEL: 12345")
        self.assertEqual(segments[2], "SIZE: 2 INCH")
        self.assertEqual(segments[3], "SPEC: ASME")

    def test_parse_key_value_colon(self):
        res = parse_key_value_segment("Brand: PMC")
        self.assertIsNotNone(res)
        self.assertEqual(res, ("Brand", "PMC"))

    def test_parse_key_value_equals(self):
        res = parse_key_value_segment("Model = 23445")
        self.assertIsNotNone(res)
        self.assertEqual(res, ("Model", "23445"))

    def test_parse_key_value_dash(self):
        res = parse_key_value_segment("DRG NO - 99812")
        self.assertIsNotNone(res)
        self.assertEqual(res, ("DRG NO", "99812"))

    def test_parse_key_value_abbreviation_dot(self):
        res = parse_key_value_segment("PART NO. ABC-100")
        self.assertIsNotNone(res)
        self.assertEqual(res, ("PART NO", "ABC-100"))

    def test_clean_leftover_text(self):
        self.assertEqual(clean_leftover_text(", ; etc. - ;"), "etc.")
        self.assertIsNone(clean_leftover_text(" , ; - / "))
        self.assertEqual(clean_leftover_text(" HEAVY DUTY CAGE "), "HEAVY DUTY CAGE")


if __name__ == "__main__":
    unittest.main()
