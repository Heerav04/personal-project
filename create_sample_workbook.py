"""
Sample workbook generator.
Creates realistic, comprehensive Excel workbooks and CSV files representing
industrial 'Material Master' and 'Standardisation' sheets.
"""

import csv
from pathlib import Path
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


# Standardisation sheet data: Group, Category Name, Standard Columns
STANDARDISATION_DATA = [
    (
        "1007",
        "PUMPS & ROTATING EQUIPMENT SPARES",
        "brand; model; manufacturer; size; additional"
    ),
    (
        "1010",
        "BEARINGS & POWER TRANSMISSION",
        "brand; model; part_number; size; material; specification; additional"
    ),
    (
        "1025",
        "VALVES & PIPING ACCESSORIES",
        "brand; drawing_number; manufacturer; material; size; specification; additional"
    ),
    (
        "1050",
        "ELECTRICAL MOTORS & DRIVES",
        "brand; model; voltage; power; speed; frame; additional"
    ),
    (
        "1060",
        "SWITCHGEAR & CONTROLGEAR",
        "brand; model; part_number; voltage; current_rating; specification; additional"
    ),
    (
        "1080",
        "FASTENERS & HARDWARE",
        "material; size; specification; finish; additional"
    ),
    (
        "1100",
        "PRESSURE & TEMPERATURE INSTRUMENTS",
        "brand; model; range; connection_size; mounting; material; additional"
    ),
    (
        "1120",
        "GASKETS & SEALING",
        "brand; size; rating; material; thickness; specification; additional"
    )
]

# Material Master sheet data: Material Code, Short Description, Long Description, Proposed Group, Group Desc
MATERIAL_MASTER_DATA = [
    # --- Group 1007: Pumps & Components (including prompt's exact illustration) ---
    (
        "1234678",
        "PUMP SPARES PMC 3X3",
        "pmc,23445,3x3 etc.",
        "1007",
        "PUMPS & ROTATING EQUIPMENT SPARES"
    ),
    (
        "1234679",
        "KSB CENTRIFUGAL PUMP IMPELLER",
        "MAKE: KSB, MODEL: ETA-100-250, SIZE: 210MM, BRONZE, IMPELLER DYNAMICALLY BALANCED",
        "1007",
        "PUMPS & ROTATING EQUIPMENT SPARES"
    ),
    (
        "1234680",
        "SULZER SHAFT SLEEVE",
        "SULZER, 54321, 4x3 SHAFT SLEEVE SS316 HARD CHROME PLATED",
        "1007",
        "PUMPS & ROTATING EQUIPMENT SPARES"
    ),
    (
        "1234681",
        "FLOWSERVE MECHANICAL SEAL",
        "BRAND: FLOWSERVE; MODEL: QB-50; SIZE: 50MM; MATL: CARBON/SIC/VITON; CARTRIDGE TYPE",
        "1007",
        "PUMPS & ROTATING EQUIPMENT SPARES"
    ),

    # --- Group 1025: Valves & Piping Accessories ---
    (
        "2001001",
        "GATE VALVE 2 INCH 150# WCB",
        "MAKE: L&T; SIZE: 2 INCH; MATL: WCB; DRG NO: DRG-VALVE-9981; SPEC: ASME B16.34; LEVER OPERATED",
        "1025",
        "VALVES & PIPING ACCESSORIES"
    ),
    (
        "2001002",
        "AUDCO BALL VALVE 1 INCH 300#",
        "BRAND: AUDCO, DRG NO: BV-300-01, SIZE: 1 INCH, MATL: CF8M, SPEC: API 6D, FLANGED FULL BORE",
        "1025",
        "VALVES & PIPING ACCESSORIES"
    ),
    (
        "2001003",
        "NON RETURN CHECK VALVE DN80",
        "MAKE: ADVANCE; SIZE: DN80; DRG NO: CV-80-CI; MATL: CAST IRON; SPEC: BS 5153; WAFER DUAL PLATE",
        "1025",
        "VALVES & PIPING ACCESSORIES"
    ),
    (
        "2001004",
        "GLOBE VALVE 3 INCH 150# WCB",
        "MAKE: KITZ / SIZE: 3 INCH / MATL: WCB / SPEC: BS 1873 / DRG NO: GV-150-03 / HANDWHEEL OPERATED",
        "1025",
        "VALVES & PIPING ACCESSORIES"
    ),

    # --- Group 1010: Bearings & Power Transmission ---
    (
        "3001001",
        "SKF DEEP GROOVE BALL BEARING",
        "MFR: SKF / PART NO: 6205-2RS1 / SIZE: 25x52x15 mm / SPEC: C3 / RUBBER SEALS BOTH SIDES",
        "1010",
        "BEARINGS & POWER TRANSMISSION"
    ),
    (
        "3001002",
        "DEEP GROOVE BALL BEARING AMBIGUOUS",
        "MAKE: SKF, 6205, 25x52x15 mm, C3 CLEARANCE",
        "1010",
        "BEARINGS & POWER TRANSMISSION"
    ),
    (
        "3001003",
        "FAG SPHERICAL ROLLER BEARING",
        "MAKE: FAG / PART NO: 22212-E1 / SIZE: 60x110x28 mm / MATL: STEEL / BRASS CAGE HEAVY DUTY",
        "1010",
        "BEARINGS & POWER TRANSMISSION"
    ),
    (
        "3001004",
        "TIMKEN TAPER ROLLER BEARING",
        "BRAND: TIMKEN; MODEL: 32008X; PART NO: 32008X-CONE; SIZE: 40x68x19 mm; HIGH PRECISION",
        "1010",
        "BEARINGS & POWER TRANSMISSION"
    ),

    # --- Group 1050: Electrical Motors & Drives ---
    (
        "4001001",
        "SIEMENS 3PH INDUCTION MOTOR",
        "MAKE: SIEMENS, MODEL: 1LA7080, 415V, 15KW, 1440 RPM, FRAME: 160M, ENCLOSURE IP55",
        "1050",
        "ELECTRICAL MOTORS & DRIVES"
    ),
    (
        "4001002",
        "ABB FLANGE MOUNTED MOTOR 30KW",
        "BRAND: ABB, MODEL: M3BP-200, VOLTAGE: 415V, POWER: 30KW, SPEED: 2950 RPM, FRAME: 200L, EFFICIENCY IE3",
        "1050",
        "ELECTRICAL MOTORS & DRIVES"
    ),
    (
        "4001003",
        "BHARAT BIJLEE FOOT MOUNT MOTOR",
        "MAKE: BHARAT BIJLEE; 415V; 7.5KW; 960 RPM; FRAME: 132M; CAST IRON BODY",
        "1050",
        "ELECTRICAL MOTORS & DRIVES"
    ),

    # --- Group 1060: Switchgear & Controlgear ---
    (
        "5001001",
        "SCHNEIDER POWER CONTACTOR",
        "BRAND: SCHNEIDER, MODEL: LC1D25M7, PART NO: 25M7-COIL, VOLTAGE: 220VAC, CURRENT: 25A, SPEC: IEC 60947-4-1, 3 POLE WITH 1NO+1NC",
        "1060",
        "SWITCHGEAR & CONTROLGEAR"
    ),
    (
        "5001002",
        "ABB MOULDED CASE CIRCUIT BREAKER",
        "MAKE: ABB, MODEL: TMAX-XT2, PART NO: 1SDA067000R1, VOLTAGE: 415V, CURRENT: 160A, SPEC: 36KA, 4 POLE FIXED",
        "1060",
        "SWITCHGEAR & CONTROLGEAR"
    ),

    # --- Group 1080: Fasteners & Hardware ---
    (
        "6001001",
        "HEX HEAD BOLT FULL THREAD M12X50",
        "SIZE: M12 x 50 mm, MATL: CARBON STEEL, SPEC: ISO 4017 GRADE 8.8, FINISH: ZINC PLATED",
        "1080",
        "FASTENERS & HARDWARE"
    ),
    (
        "6001002",
        "HEX NUT M16 SS316",
        "MATL: SS316, SIZE: M16, SPEC: DIN 934 A4-70, FINISH: PASSIVATED, CORROSION RESISTANT",
        "1080",
        "FASTENERS & HARDWARE"
    ),
    (
        "6001003",
        "SPRING WASHER M20",
        "MATL: CARBON STEEL, SIZE: M20, SPEC: DIN 127B, FINISH: BLACK PHOSPHATE",
        "1080",
        "FASTENERS & HARDWARE"
    ),

    # --- Group 1100: Pressure & Temperature Instruments ---
    (
        "7001001",
        "WIKA BOURDON TUBE PRESSURE GAUGE",
        "BRAND: WIKA, MODEL: 232.50, RANGE: 0-10 BAR, CONN: 1/2 INCH NPT, MOUNTING: BOTTOM, MATL: SS316, GLYCERIN FILLED",
        "1100",
        "PRESSURE & TEMPERATURE INSTRUMENTS"
    ),
    (
        "7001002",
        "BIMETAL TEMPERATURE GAUGE 0-150C",
        "MAKE: BAUMER, MODEL: TB-100, RANGE: 0-150 DEG C, CONN: 1/2 INCH BSP, MOUNTING: EVERY ANGLE, MATL: SS304, STEM LENGTH 150MM",
        "1100",
        "PRESSURE & TEMPERATURE INSTRUMENTS"
    ),

    # --- Group 1120: Gaskets & Sealing ---
    (
        "8001001",
        "SPIRAL WOUND GASKET 2 INCH 150#",
        "BRAND: KLINGER, SIZE: 2 INCH, RATING: 150#, MATL: SS316/GRAPHITE, THICKNESS: 4.5MM, SPEC: ASME B16.20, WITH INNER AND OUTER RINGS",
        "1120",
        "GASKETS & SEALING"
    ),
    (
        "8001002",
        "CAF GASKET 3 INCH 150#",
        "BRAND: CHAMPION, SIZE: 3 INCH, RATING: 150#, MATL: RUBBER/ASBESTOS-FREE, THICKNESS: 3MM, SPEC: EN 1514-1, FULL FACE",
        "1120",
        "GASKETS & SEALING"
    ),

    # --- Unrecognized / Unmapped Group Test Case ---
    (
        "9999001",
        "SPECIAL EXPERIMENTAL TOOL UNIT",
        "CUSTOM TOOLING UNIT V-900, GRADE 40, SPECIAL HEAT TREATED ALLOY",
        "9999",
        "UNMAPPED TEST GROUP"
    )
]


def create_sample_workbook(
    file_path: str = "sample_materials.xlsx",
    export_csv: bool = True
) -> Path:
    wb = openpyxl.Workbook()

    # Sheet 1: Material Master
    ws_mat = wb.active
    ws_mat.title = "Material Master"

    mat_headers = [
        "Material Code",
        "Short Description",
        "Long Description",
        "Proposed Material Group",
        "Proposed Material Group Desc"
    ]
    ws_mat.append(mat_headers)
    for row in MATERIAL_MASTER_DATA:
        ws_mat.append(row)

    # Sheet 2: Standardisation
    ws_std = wb.create_sheet(title="Standardisation")
    std_headers = [
        "Group",
        "Category Name",
        "Standard Columns"
    ]
    ws_std.append(std_headers)
    for row in STANDARDISATION_DATA:
        ws_std.append(row)

    # Styling for professional readability
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )

    for ws in (ws_mat, ws_std):
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.border = thin_border
                cell.font = Font(name="Calibri", size=10)

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 14), 70)

    out_path = Path(file_path).resolve()
    wb.save(out_path)
    wb.close()

    # Optional CSV export for immediate text viewing
    if export_csv:
        csv_dir = out_path.parent / "sample_data_csv"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Export Material Master CSV
        mat_csv = csv_dir / "material_master.csv"
        with open(mat_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(mat_headers)
            w.writerows(MATERIAL_MASTER_DATA)

        # Export Standardisation CSV
        std_csv = csv_dir / "standardisation.csv"
        with open(std_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(std_headers)
            w.writerows(STANDARDISATION_DATA)

    return out_path


if __name__ == "__main__":
    path = create_sample_workbook()
    print(f"Sample workbook created successfully at: {path}")
    print(f"CSV files exported to: {path.parent / 'sample_data_csv'}")
