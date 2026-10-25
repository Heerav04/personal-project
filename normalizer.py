"""
Text normalization and segment tokenization utilities for material descriptions.
Handles delimiter splitting, key-value candidate extraction, and leftover text cleanup.
"""

from __future__ import annotations
import re
from typing import List, Optional, Tuple


def normalize_whitespace(text: str) -> str:
    """Normalize non-standard spaces, tabs, newlines into standard single spaces."""
    if not text:
        return ""
    # Replace non-breaking spaces and other unicode spaces
    cleaned = re.sub(r"[\u00A0\u1680\u2000-\u200B\u202F\u205F\u3000]", " ", text)
    # Replace unicode quotes with standard ascii quotes
    cleaned = re.sub(r"[\u2018\u2019\u201A\u201B]", "'", cleaned)
    cleaned = re.sub(r"[\u201C\u201D\u201E\u201F]", '"', cleaned)
    # Replace unicode dashes with standard hyphen
    cleaned = re.sub(r"[\u2010-\u2015\u2212]", "-", cleaned)
    # Collapse multiple whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def split_into_segments(text: str, delimiters: Optional[List[str]] = None) -> List[str]:
    """
    Splits text into constituent segments based on specified or default delimiters.
    Preserves order of segments.
    """
    if not text:
        return []

    delims = delimiters or [";", ",", "\n", "|", "/"]
    # Build regex character class / alternation for delimiters
    escaped_delims = [re.escape(d) for d in sorted(delims, key=len, reverse=True)]
    pattern = "|".join(escaped_delims)

    raw_segments = re.split(pattern, text)
    segments = []
    for s in raw_segments:
        s_clean = normalize_whitespace(s)
        if s_clean:
            segments.append(s_clean)
    return segments


def parse_key_value_segment(
    segment: str,
    separators: Optional[List[str]] = None
) -> Optional[Tuple[str, str]]:
    """
    Attempts to parse a segment into (Key, Value).
    Recognizes separators like ':', '=', ' - ', or abbreviations followed by dot/space.
    E.g.:
      'MAKE: SIEMENS' -> ('MAKE', 'SIEMENS')
      'MODEL NO. 23445' -> ('MODEL NO', '23445')
      'BRAND = PMC' -> ('BRAND', 'PMC')
      'DRG NO - 12345' -> ('DRG NO', '12345')
    """
    seg = normalize_whitespace(segment)
    if not seg:
        return None

    # Check explicit separators first
    seps = separators or [":", "=", " - ", " -- "]
    for sep in seps:
        if sep in seg:
            parts = seg.split(sep, 1)
            k = normalize_whitespace(parts[0])
            v = normalize_whitespace(parts[1])
            if k and v:
                return (k, v)

    # Check dot separator for common abbreviation prefixes, e.g. "DRG NO. 12345", "PART NO. ABC"
    match_dot = re.match(
        r"^([A-Za-z0-9\s/]+(?:NO|NUM|NUMBER|REV|SPEC|CODE))\.\s*(.+)$",
        seg,
        re.IGNORECASE
    )
    if match_dot:
        k = normalize_whitespace(match_dot.group(1))
        v = normalize_whitespace(match_dot.group(2))
        if k and v:
            return (k, v)

    return None


def clean_leftover_text(text: str) -> Optional[str]:
    """
    Cleans leftover unmapped text by removing orphaned punctuation and whitespace.
    Returns None if no meaningful alphanumeric characters remain.
    """
    if not text:
        return None

    cleaned = normalize_whitespace(text)
    # Strip leading/trailing punctuation like commas, semicolons, dashes, slashes
    cleaned = re.sub(r"^[\s,;:/\-|]+", "", cleaned)
    cleaned = re.sub(r"[\s,;:/\-|]+$", "", cleaned)
    cleaned = normalize_whitespace(cleaned)

    # Must contain at least one alphanumeric character
    if not re.search(r"[A-Za-z0-9]", cleaned):
        return None

    return cleaned
