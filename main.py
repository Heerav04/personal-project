"""
Main CLI entrypoint for Excel to Structured JSON extraction program.
Provides commands to inspect workbooks, run deterministic extractions,
and generate structured JSON along with review and summary reports.
"""

from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path
from typing import List

from config import Config
from extractor import MaterialExtractor
from group_parser import GroupParser
from reporter import ReviewReport
from workbook_loader import WorkbookInspector, WorkbookLoader
from writer import JsonWriter


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


def run_pipeline(
    input_file: str | Path,
    output_file: str | Path,
    review_file: str | Path,
    config: Config,
    fallback_short_desc: bool = False
) -> None:
    logger = logging.getLogger("pipeline")
    logger.info(f"Opening workbook: {input_file}")

    review_report = ReviewReport()
    extractor = MaterialExtractor(config=config, review_report=review_report)

    with WorkbookLoader(input_file, config=config) as loader:
        # 1. Parse Standardisation Sheet
        logger.info("Parsing Standardisation sheet...")
        group_parser = GroupParser(config=config)
        groups = group_parser.parse_from_workbook(loader)
        logger.info(f"Successfully loaded {len(groups)} group definitions from Standardisation sheet.")

        # 2. Map Material Master Sheet
        logger.info("Locating Material Master sheet...")
        mat_sheet_name = loader.resolve_sheet_name("material_master_sheets")
        mat_col_candidates = config.column_mappings.get("material_master", {})
        role_to_idx, raw_headers = loader.map_sheet_columns(mat_sheet_name, mat_col_candidates)

        if "material_code" not in role_to_idx:
            raise ValueError(
                f"Required column 'material_code' could not be found in sheet '{mat_sheet_name}'. "
                f"Candidates: {mat_col_candidates.get('material_code')}. Available headers: {raw_headers}"
            )
        if "group_number" not in role_to_idx:
            raise ValueError(
                f"Required column 'group_number' could not be found in sheet '{mat_sheet_name}'. "
                f"Candidates: {mat_col_candidates.get('group_number')}. Available headers: {raw_headers}"
            )

        logger.info(f"Reading Material Master rows from '{mat_sheet_name}'...")
        records: List[dict] = []

        for row in loader.read_rows_as_dicts(mat_sheet_name, role_to_idx):
            mat_code = row.get("material_code")
            if mat_code is None or str(mat_code).strip() == "":
                continue

            grp_num = row.get("group_number")
            short_desc = row.get("short_description")
            long_desc = row.get("long_description")

            group_def = group_parser.get_group(grp_num)

            rec = extractor.process_material(
                material_code=mat_code,
                group_number=grp_num,
                short_desc=short_desc,
                long_desc=long_desc,
                group_def=group_def,
                fallback_short_desc=fallback_short_desc
            )
            records.append(rec)

    # 3. Write outputs
    logger.info(f"Writing {len(records)} structured records to: {output_file}")
    JsonWriter.write_records(records, output_file)

    logger.info(f"Writing review report to: {review_file}")
    JsonWriter.write_review_report(review_report, review_file)

    # 4. Display terminal summary
    print("\n" + review_report.generate_text_summary())
    print(f"\n[OK] Processing complete!")
    print(f"     Structured Records JSON: {Path(output_file).resolve()}")
    print(f"     Review Report JSON:      {Path(review_file).resolve()}\n")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic Excel to Structured JSON extractor for Material Master & Standardisation sheets."
    )
    parser.add_argument(
        "-i", "--input",
        dest="input_file",
        help="Path to input Excel workbook (.xlsx / .xlsm)"
    )
    parser.add_argument(
        "-o", "--output",
        dest="output_file",
        default="output_materials.json",
        help="Path for output structured JSON file (default: output_materials.json)"
    )
    parser.add_argument(
        "-r", "--review-output",
        dest="review_file",
        default="review_report.json",
        help="Path for review report JSON file (default: review_report.json)"
    )
    parser.add_argument(
        "-c", "--config",
        dest="config_file",
        help="Path to custom JSON configuration file (default: default_config.json)"
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Inspect sheets and headers in the input workbook and exit without processing."
    )
    parser.add_argument(
        "--fallback-short-desc",
        action="store_true",
        help="Enable secondary extraction from short description if long description lacks fields."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable detailed debug logging."
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)

    if not args.input_file:
        parser.print_help()
        print("\nError: Please specify an input Excel workbook using -i or --input.")
        sys.exit(1)

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"\nError: Specified input file does not exist: {input_path}")
        sys.exit(1)

    if args.inspect:
        WorkbookInspector.print_inspection(input_path)
        sys.exit(0)

    try:
        config = Config.load(args.config_file)
        if args.fallback_short_desc:
            config.options["fallback_to_short_desc"] = True

        run_pipeline(
            input_file=input_path,
            output_file=args.output_file,
            review_file=args.review_file,
            config=config,
            fallback_short_desc=args.fallback_short_desc
        )
    except Exception as e:
        logging.error(f"Execution failed: {e}", exc_info=args.verbose)
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
