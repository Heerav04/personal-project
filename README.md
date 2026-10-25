# Excel to Structured JSON Converter (Deterministic Rule-Based)

A modular, deterministic Python program that reads an Excel workbook containing **Material Master** and **Standardisation** sheets, extracts structured technical attributes based on group-specific column definitions, and outputs:
1. **Structured JSON**: One JSON object per material code, containing the group's defined standard fields.
2. **Review Report JSON**: Detailed diagnostics covering unrecognized groups, ambiguous extractions, unmatched description text, and a processing summary.

> **Deterministic Guarantee**: Uses **100% deterministic Python rules** (regular expressions, labeled key-value parsing, dimension extractors, and group-specific rules). **No LLMs, machine-learning models, or external AI services** are used.

---

## Features

- **Dynamic Group Schema**: Each material's output schema is dynamically derived from its group's semicolon-separated `Standard Columns` in the `Standardisation` sheet.
- **Tolerant Sheet & Column Discovery**: Case-insensitive and whitespace-tolerant matching for sheet names and column headers. Does not assume rigid names or casing.
- **Interactive Workbook Inspector (`--inspect`)**: Inspects sheet names, row counts, and detected column headers without executing the extraction.
- **Conservative Extraction & Ambiguity Handling**:
  - Never classifies a bare number as a model, drawing number, or part number unless explicitly labeled or authorized by group-specific rules.
  - If multiple fields conflict or multiple interpretations exist, the field is left `null` and flagged in the review report.
  - **No invented values**: Any unpopulated field is serialized as JSON `null`.
- **Unmatched Description & `additional` Field**:
  - Captures leftover meaningful text into `additional` if the group schema includes it.
  - Captures it into `unmatched_text` if `additional` is not part of the group's standard columns.
- **Unrecognized Group Safeguard**: Reports materials with unmapped groups in the review report instead of silently dropping them.
- **Editable Configuration**: All sheet candidates, column aliases, regex patterns, known values, and group-specific rules are defined in an editable JSON configuration (`default_config.json`).
- **Optional Secondary Fallback**: Configurable fallback to `short_description` if `long_description` lacks specific fields.

---

## Project Structure

```
├── default_config.json         # Editable configuration (aliases, patterns, group rules)
├── config.py                   # Configuration loader and lookup helper
├── workbook_loader.py          # Workbook inspection, sheet & column resolution
├── group_parser.py             # Parses semicolon-separated Standard Columns
├── normalizer.py               # Text cleaning, tokenizer, and key-value segment parser
├── extractor.py                # Deterministic multi-stage extraction engine
├── reporter.py                 # Review metrics aggregator & summary generator
├── writer.py                   # Structured JSON records & review report writer
├── main.py                     # CLI entrypoint
├── create_sample_workbook.py   # Generates test workbook (sample_materials.xlsx)
├── requirements.txt            # Python dependencies (openpyxl)
├── tests/                      # Comprehensive test suite (19 tests)
│   ├── test_config.py
│   ├── test_normalizer.py
│   ├── test_group_parser.py
│   ├── test_extractor.py
│   └── test_pipeline.py
└── README.md
```

---

## Installation & Setup

### 1. Prerequisites
Python 3.10+ is required.

### 2. Create Virtual Environment & Install Dependencies
On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

On Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Quick Start & Usage

### 1. Generate the Sample Test Workbook
Run the generator script to create `sample_materials.xlsx` demonstrating various real-world scenarios:
```powershell
.\.venv\Scripts\python create_sample_workbook.py
```

### 2. Inspect Workbook Sheets and Headers
Before running extraction, you can inspect the workbook's layout:
```powershell
.\.venv\Scripts\python main.py -i sample_materials.xlsx --inspect
```
Example Output:
```text
=======================================================
 WORKBOOK INSPECTION REPORT: sample_materials.xlsx
=======================================================

Sheet: 'Material Master' (Total Rows: 7)
  Detected Headers (5):
    [1] Material Code
    [2] Short Description
    [3] Long Description
    [4] Proposed Material Group
    [5] Proposed Material Group Desc
-------------------------------------------------------
Sheet: 'Standardisation' (Total Rows: 5)
  Detected Headers (3):
    [1] Group
    [2] Category Name
    [3] Standard Columns
-------------------------------------------------------
```

### 3. Run the Extraction Pipeline
```powershell
.\.venv\Scripts\python main.py -i sample_materials.xlsx -o output_materials.json -r review_report.json
```

### 4. CLI Arguments Reference

| Argument | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `--input` | `-i` | Path to the Excel workbook (`.xlsx`, `.xlsm`) | *Required* |
| `--output` | `-o` | Path for the output structured JSON file | `output_materials.json` |
| `--review-output` | `-r` | Path for the review report JSON file | `review_report.json` |
| `--config` | `-c` | Path to custom configuration file | `default_config.json` |
| `--inspect` | | Inspect sheets and column headers and exit | `False` |
| `--fallback-short-desc` | | Enable secondary fallback to short description | `False` |
| `--verbose` | `-v` | Enable detailed debug logging | `False` |

---

## Sample Outputs

### 1. Structured JSON Record (`output_materials.json`)

#### Group `1007` Example (Positional PMC Token Extraction):
```json
{
  "material_code": "1234678",
  "group_number": "1007",
  "short_description": "PUMP SPARES PMC 3X3",
  "long_description": "pmc,23445,3x3 etc.",
  "brand": "pmc",
  "model": "23445",
  "manufacturer": null,
  "size": "3x3",
  "additional": "etc."
}
```

#### Group `1025` Example (Key-Value & Physical Dimension Extraction):
```json
{
  "material_code": "2001001",
  "group_number": "1025",
  "short_description": "GATE VALVE 2 INCH 150# WCB",
  "long_description": "MAKE: L&T; SIZE: 2 INCH; MATL: WCB; DRG NO: DRG-VALVE-9981; SPEC: ASME B16.34; LEVER OPERATED",
  "brand": "L&T",
  "drawing_number": "DRG-VALVE-9981",
  "manufacturer": null,
  "material": "WCB",
  "size": "2 INCH",
  "specification": "ASME B16.34",
  "additional": "LEVER OPERATED"
}
```

### 2. Review Report (`review_report.json`)
The review report captures all edge cases, unresolved ambiguities, unmapped groups, and leftover text:

```json
{
  "summary": {
    "total_materials_processed": 6,
    "total_unique_groups_encountered": 5,
    "unrecognized_group_records_count": 1,
    "ambiguous_extractions_count": 1,
    "records_with_unmatched_text_count": 5,
    "total_field_values_extracted": 18,
    "total_fields_left_null": 10
  },
  "unrecognized_groups": [
    {
      "material_code": "9999001",
      "group_number": "9999",
      "short_description": "SPECIAL EXPERIMENTAL TOOL",
      "long_description": "CUSTOM TOOLING UNIT V-900, GRADE 40",
      "reason": "Group '9999' has no matching row in Standardisation sheet."
    }
  ],
  "ambiguous_extractions": [
    {
      "material_code": "3001002",
      "group_number": "1010",
      "field_name": "ambiguous (model/part_number)",
      "source_text": "6205",
      "candidate_values": [
        "6205"
      ],
      "reason": "Unlabeled token '6205' could be model, part_number; left null per conservative extraction rule."
    }
  ],
  "unmatched_descriptions": [
    {
      "material_code": "2001001",
      "group_number": "1025",
      "unmatched_text": "LEVER OPERATED",
      "target_field": "additional"
    }
  ]
}
```

---

## Configuration Guide (`default_config.json`)

You can edit `default_config.json` (or pass a custom JSON via `--config`) to customize:

### Sheet & Column Aliases
```json
"sheet_mappings": {
  "material_master_sheets": ["Material Master", "Materials", "MasterData"],
  "standardisation_sheets": ["Standardisation", "Standardization", "Standards"]
}
```

### Global Field Aliases
```json
"global_aliases": {
  "brand": ["brand", "make", "mfr brand", "brand name"],
  "drawing_number": ["drawing number", "drawing no", "drg no", "drgno", "dgno", "dno"],
  "model": ["model", "model no", "model number", "mod no"],
  "manufacturer": ["manufacturer", "mfr", "mfg", "maker"],
  "size": ["size", "dimension", "dimensions", "dim", "bore"]
}
```

### Group-Specific Rules
Group-specific rules override global behavior for specific material groups:
```json
"group_rules": {
  "1007": {
    "description": "Rules for Group 1007 (PMC pump spares)",
    "allow_positional_extraction": true,
    "positional_mapping": ["brand", "model", "size"],
    "aliases": {
      "model": ["mod", "model", "type"],
      "brand": ["brand", "make"]
    },
    "patterns": {
      "model": "^[0-9]{4,8}$",
      "brand": "^[a-zA-Z]{2,12}$"
    }
  }
}
```

---

## Running Automated Tests

Run the full test suite using Python's `unittest`:
```powershell
.\.venv\Scripts\python -m unittest discover tests
```
All 19 tests verify configuration loading, normalizers, group definition parsing, conservative extraction, ambiguity resolution, and end-to-end execution.
#   p e r s o n a l - p r o j e c t  
 