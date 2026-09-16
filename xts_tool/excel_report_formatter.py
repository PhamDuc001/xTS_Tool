"""
Excel Report Formatter for Android Automotive OS Google Certification Reports.
Handles:
1. Cleaning and standardizing individual test suite workbooks (03.*.xlsx):
   - Updates header metadata (Project, HW, SW, MICOM, Dates, Tester).
   - Unmerges B17:F17.
   - Deletes rows 15 to 40 while preserving formula (=E12/C12) and child sheets.
2. Updating Google Certification Summary workbook:
   - Adaptively locates previous version block (searches bottom-up for 'Summary' and 'HW version').
   - Appends new version block (2 blank rows separation).
   - Populates 7 test metrics per suite from D3:J3 of 03.* files and XML of CTS_Verifier.
   - Cleans rows 3+ and updates 'Nissan Fail Module List' (filtering Failed > 0).
   - Cleans rows 3+ and updates 'Nissan Fail TestCase List' with sequential No.
"""
import os
import re
import shutil
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# =============================================================================
# Helper & Normalization Functions
# =============================================================================

def _norm_key(name: str) -> str:
    """Normalizes suite names for robust matching (e.g. 'ATS_Interactive' -> 'atsinteractive')."""
    return re.sub(r'[^a-zA-Z0-9]', '', str(name)).lower()


def extract_suite_version_from_c7(c7_val: Any) -> str:
    """
    Extracts version string from cell C7 of Test Summary sheet in 03.*.xlsx or XML suite_version.
    Examples:
    - 'CTS 14_r13' -> '14_r13'
    - 'STS 14_sts-r55' -> '14_sts-r55'
    - 'STS sts-r55' -> 'sts-r55'
    - 'VTS 14_r13' -> '14_r13'
    - 'ATS 2026_r2' -> '2026_r2'
    - '14_r13' -> '14_r13'
    """
    if not c7_val:
        return ""
    val = str(c7_val).strip()
    prefixes = [
        "CTS-VERIFIER", "CTS_VERIFIER", "CTSONGSI",
        "ATS-IN-CAR", "ATS_INTERACTIVE", "ATS-MULTIDEVICE",
        "BFG", "CTS", "STS", "VTS", "ATS"
    ]
    for prefix in prefixes:
        if val.upper().startswith(prefix):
            remainder = val[len(prefix):].strip()
            if remainder:
                return remainder
    parts = val.split(None, 1)
    if len(parts) > 1:
        return parts[1].strip()
    return val


def format_single_suite_report(source_path: str, target_path: str,
                               metadata: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Standardizes individual suite result file (03.*.xlsx):
    - Sets Header cells on sheet 'Test Summary':
        C3: Project (Model) Full
        C4: HW (PCB) version
        C5: SW version
        C6: MICOM version
        G2: OEM Delivery (MM/DD/YYYY)
        G3: Test Start (MM/DD/YYYY)
        G4: Test End (MM/DD/YYYY)
        G6: Tester
    - Unmerges B17:F17
    - Deletes rows 15 to 40 (max_row - 14)
    - Preserves =E12/C12 formula and formatting.
    """
    if not os.path.exists(source_path):
        return False, f"File nguồn không tồn tại: {source_path}"

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.copyfile(source_path, target_path)

    try:
        wb = openpyxl.load_workbook(target_path)
        summary_sheet_name = None
        for s in wb.sheetnames:
            if "summary" in s.lower():
                summary_sheet_name = s
                break

        if not summary_sheet_name:
            wb.save(target_path)
            return True, "Không tìm thấy sheet Test Summary, giữ nguyên file."

        ws = wb[summary_sheet_name]

        # 1. Populate Header Metadata
        if "model_full" in metadata:
            ws["C3"] = str(metadata["model_full"])
        if "hw_version" in metadata:
            ws["C4"] = str(metadata["hw_version"])
        if "sw_version" in metadata:
            ws["C5"] = str(metadata["sw_version"])
        if "micom_version" in metadata:
            ws["C6"] = str(metadata["micom_version"])

        if "oem_delivery_date" in metadata:
            ws["G2"] = str(metadata["oem_delivery_date"])
        if "test_start_date" in metadata:
            ws["G3"] = str(metadata["test_start_date"])
        if "test_end_date" in metadata:
            ws["G4"] = str(metadata["test_end_date"])
        if "tester_name" in metadata:
            ws["G6"] = str(metadata["tester_name"])

        # 2. Unmerge B17:F17 if merged
        merged_to_remove = []
        for mr in ws.merged_cells.ranges:
            coord = str(mr)
            if coord.upper() == "B17:F17" or ("B17" in coord and "F17" in coord):
                merged_to_remove.append(mr)
        for mr in merged_to_remove:
            ws.merged_cells.remove(mr)

        # 3. Clean up extra rows from row 15 downwards
        if ws.max_row >= 15:
            rows_to_delete = ws.max_row - 14
            ws.delete_rows(15, rows_to_delete)

        # 4. Ensure E12 formula (=E12/C12 in percent) or C12/E12 is intact
        e12_val = str(ws["E12"].value or "")
        if not e12_val or not e12_val.startswith("="):
            ws["E12"] = "=E12/C12"

        wb.save(target_path)
        return True, "Chuẩn hóa file 03 thành công."
    except Exception as e:
        return False, f"Lỗi xử lý file Excel {target_path}: {str(e)}"


def extract_suite_metrics_from_xlsx(filepath: str, suite_category: str) -> Dict[str, Any]:
    """
    Extracts 7 metrics from sheet 'Test Result_Detail' row 3 (D3:J3):
    - Pass, Fail, Assumption Failure, Ignored, Total Tests, Module Done, Total Module
    Also extracts:
    - Failed modules from row 5+ where Failed > 0
    - Failed testcases from sheet 'Failed Test Cases' (Col C: Module, Col D: TestCase)
    """
    results = {
        "category": suite_category,
        "test_suite_raw": None,
        "pass": 0, "fail": 0, "assumption": 0, "ignored": 0,
        "total": 0, "done": 0, "total_module": 0,
        "failed_modules": [],
        "failed_testcases": []
    }

    if not os.path.exists(filepath):
        return results

    try:
        wb = openpyxl.load_workbook(filepath, data_only=True)

        # Extract Test Suite version from cell C7 on 'Test Summary' sheet
        for s in wb.sheetnames:
            if "summary" in s.lower():
                ws_sum_info = wb[s]
                v_c7 = ws_sum_info["C7"].value
                if v_c7 is not None:
                    results["test_suite_raw"] = str(v_c7).strip()
                break

        detail_sheet_name = None
        for s in wb.sheetnames:
            if "result" in s.lower() and "detail" in s.lower():
                detail_sheet_name = s
                break

        if detail_sheet_name:
            ws_det = wb[detail_sheet_name]

            def safe_int(val, default=0):
                if val is None:
                    return default
                try:
                    return int(float(str(val).strip()))
                except Exception:
                    return default

            calc_pass = 0
            calc_fail = 0
            calc_af = 0
            calc_ign = 0
            calc_tot = 0
            calc_done = 0
            calc_tot_mod = 0

            # Iterate module rows from row 5 downwards
            for r in range(5, ws_det.max_row + 1):
                mod_name = ws_det.cell(r, 3).value  # Col C: Module Name
                if not mod_name or str(mod_name).strip() == "":
                    continue

                v_pass = safe_int(ws_det.cell(r, 4).value)
                v_fail = safe_int(ws_det.cell(r, 5).value)
                v_af = safe_int(ws_det.cell(r, 6).value)
                v_ign = safe_int(ws_det.cell(r, 7).value)
                v_tot = safe_int(ws_det.cell(r, 8).value)
                v_done = str(ws_det.cell(r, 9).value or "").strip().lower()

                calc_pass += v_pass
                calc_fail += v_fail
                calc_af += v_af
                calc_ign += v_ign
                calc_tot += v_tot
                calc_tot_mod += 1
                if v_done in ["true", "1"]:
                    calc_done += 1

                if v_fail > 0:
                    results["failed_modules"].append({
                        "category": suite_category,
                        "module": str(mod_name).strip(),
                        "passed": v_pass,
                        "failed": v_fail,
                        "assumption": v_af,
                        "ignored": v_ign,
                        "total_tests": v_tot,
                        "done": "true" if v_done in ["true", "1"] else "false",
                        "remark": ""
                    })

            # Check if Row 3 has cached numeric values from Excel
            row3_vals = [ws_det.cell(3, c).value for c in range(4, 11)]
            has_cached_row3 = any(isinstance(v, (int, float)) and v > 0 for v in row3_vals)

            if has_cached_row3:
                results["pass"] = safe_int(ws_det.cell(3, 4).value)
                results["fail"] = safe_int(ws_det.cell(3, 5).value)
                results["assumption"] = safe_int(ws_det.cell(3, 6).value)
                results["ignored"] = safe_int(ws_det.cell(3, 7).value)
                results["total"] = safe_int(ws_det.cell(3, 8).value)
                results["done"] = safe_int(ws_det.cell(3, 9).value)
                results["total_module"] = safe_int(ws_det.cell(3, 10).value)
            else:
                results["pass"] = calc_pass
                results["fail"] = calc_fail
                results["assumption"] = calc_af
                results["ignored"] = calc_ign
                results["total"] = calc_tot
                results["done"] = calc_done
                results["total_module"] = calc_tot_mod

        # 3. Parse Failed Test Cases
        fail_sheet_name = None
        for s in wb.sheetnames:
            if "failed" in s.lower() and "test" in s.lower():
                fail_sheet_name = s
                break

        if fail_sheet_name:
            ws_fail = wb[fail_sheet_name]
            for r in range(5, ws_fail.max_row + 1):
                mod_val = ws_fail.cell(r, 3).value  # Col C: Module
                tc_val = ws_fail.cell(r, 4).value   # Col D: Test Case
                if mod_val and tc_val:
                    results["failed_testcases"].append({
                        "category": suite_category,
                        "module": str(mod_val).strip(),
                        "test_case": str(tc_val).strip()
                    })

    except Exception as e:
        print(f"Lỗi trích xuất số liệu từ {filepath}: {e}")

    return results


def extract_verifier_metrics_from_xml(xml_path: str) -> Dict[str, Any]:
    """
    Parses CTS_Verifier test_result.xml directly.
    Looks for: <Summary pass="50" failed="0" modules_done="1" modules_total="1" />
    """
    metrics = {
        "category": "CTS-Verifier",
        "test_suite_raw": None,
        "pass": 0, "fail": 0, "assumption": 0, "ignored": 0,
        "total": 0, "done": 1, "total_module": 1,
        "failed_modules": [], "failed_testcases": []
    }
    if not os.path.exists(xml_path):
        return metrics

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        s_ver = root.get("suite_version")
        if s_ver:
            metrics["test_suite_raw"] = str(s_ver).strip()
        summary_elem = root.find("Summary")
        if summary_elem is not None:
            p = int(summary_elem.get("pass", "0"))
            f = int(summary_elem.get("failed", "0"))
            md = int(summary_elem.get("modules_done", "1"))
            mt = int(summary_elem.get("modules_total", "1"))
            metrics["pass"] = p
            metrics["fail"] = f
            metrics["total"] = p + f
            metrics["done"] = md
            metrics["total_module"] = mt
    except Exception as e:
        print(f"Lỗi phân tích XML Verifier {xml_path}: {e}")

    return metrics


def update_summary_workbook(template_path: str, output_path: str,
                            all_suite_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
                            metadata: Optional[Dict[str, Any]] = None,
                            hw_version: str = "",
                            sw_version: str = "",
                            micom_version: str = "",
                            single_suite_files: Optional[Dict[str, str]] = None,
                            cts_verifier_xml_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Updates Google Certification Summary workbook:
    1. Locates last version block in sheet 'Summary' adaptively.
    2. Copies format and appends new block (leaving 2 blank rows).
    3. Populates 7 metrics for each suite from all_suite_metrics.
    4. Clears old data and writes new entries to 'Nissan Fail Module List' (Failed > 0)
       and 'Nissan Fail TestCase List'.
    5. Saves as output_path.
    """
    if not os.path.exists(template_path):
        return False, f"File Summary template không tồn tại: {template_path}"

    # Build all_suite_metrics if not supplied directly
    if all_suite_metrics is None:
        all_suite_metrics = {}
        if single_suite_files:
            for sname, sfilepath in single_suite_files.items():
                if os.path.exists(sfilepath):
                    all_suite_metrics[sname] = extract_suite_metrics_from_xlsx(sfilepath, sname)
        if cts_verifier_xml_path and os.path.exists(cts_verifier_xml_path):
            all_suite_metrics["CTS_Verifier"] = extract_verifier_metrics_from_xml(cts_verifier_xml_path)

    if metadata is None:
        metadata = {
            "hw_version": hw_version,
            "sw_version": sw_version,
            "micom_version": micom_version,
        }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    shutil.copyfile(template_path, output_path)

    try:
        wb = openpyxl.load_workbook(output_path)
        if "Summary" not in wb.sheetnames:
            return False, "File template không có sheet 'Summary'!"

        ws_sum = wb["Summary"]

        # -------------------------------------------------------------
        # 1. Adaptive Block Detection
        # -------------------------------------------------------------
        last_block_end = None
        for r in range(ws_sum.max_row, 0, -1):
            val = ws_sum.cell(r, 3).value  # Col C
            if val and str(val).strip().lower() == "summary":
                last_block_end = r
                break

        if not last_block_end:
            return False, "Không tìm thấy dòng 'Summary' của khối bảng version trước trong template!"

        last_block_start = None
        for r in range(last_block_end, 0, -1):
            val = ws_sum.cell(r, 2).value  # Col B
            if val and "hw" in str(val).strip().lower() and "version" in str(val).strip().lower():
                last_block_start = r
                break

        if not last_block_start:
            return False, "Không tìm thấy dòng bắt đầu ('HW version') của khối bảng version trước!"

        block_height = last_block_end - last_block_start + 1
        new_block_start = last_block_end + 3  # Leave 2 blank rows
        new_block_end = new_block_start + block_height - 1

        # 2. Copy structure and styling from previous block
        row_offset = new_block_start - last_block_start
        for i in range(block_height):
            src_r = last_block_start + i
            dst_r = new_block_start + i

            if src_r in ws_sum.row_dimensions and ws_sum.row_dimensions[src_r].height:
                ws_sum.row_dimensions[dst_r].height = ws_sum.row_dimensions[src_r].height

            for c in range(1, 12):
                src_cell = ws_sum.cell(src_r, c)
                dst_cell = ws_sum.cell(dst_r, c)

                # Copy styles
                if src_cell.has_style:
                    dst_cell.font = Font(
                        name=src_cell.font.name, size=src_cell.font.size,
                        bold=src_cell.font.bold, italic=src_cell.font.italic,
                        color=src_cell.font.color
                    )
                    dst_cell.alignment = Alignment(
                        horizontal=src_cell.alignment.horizontal,
                        vertical=src_cell.alignment.vertical,
                        wrap_text=src_cell.alignment.wrap_text
                    )
                    if src_cell.fill and src_cell.fill.fill_type:
                        dst_cell.fill = PatternFill(
                            fill_type=src_cell.fill.fill_type,
                            start_color=src_cell.fill.start_color,
                            end_color=src_cell.fill.end_color
                        )
                    if src_cell.border:
                        dst_cell.border = Border(
                            left=src_cell.border.left,
                            right=src_cell.border.right,
                            top=src_cell.border.top,
                            bottom=src_cell.border.bottom
                        )
                    if src_cell.number_format:
                        dst_cell.number_format = src_cell.number_format

            # Copy text values
            c3_val = str(ws_sum.cell(src_r, 3).value or "").strip().lower()
            if c3_val == "test category":
                # Header row: copy all column titles from col 3 to 10
                for c in range(3, 11):
                    ws_sum.cell(dst_r, c).value = ws_sum.cell(src_r, c).value
            elif c3_val == "summary":
                ws_sum.cell(dst_r, 3).value = ws_sum.cell(src_r, 3).value
            else:
                if ws_sum.cell(src_r, 2).value is not None:
                    ws_sum.cell(dst_r, 2).value = ws_sum.cell(src_r, 2).value
                if ws_sum.cell(src_r, 3).value is not None:
                    ws_sum.cell(dst_r, 3).value = ws_sum.cell(src_r, 3).value

        # Replicate merged cells within the block (e.g. B6:B16 -> B23:B33)
        for mr in list(ws_sum.merged_cells.ranges):
            if mr.min_row >= last_block_start and mr.max_row <= last_block_end:
                new_min_r = mr.min_row + row_offset
                new_max_r = mr.max_row + row_offset
                new_min_c = mr.min_col
                new_max_c = mr.max_col
                ws_sum.merge_cells(
                    start_row=new_min_r, end_row=new_max_r,
                    start_column=new_min_c, end_column=new_max_c
                )
                if new_min_c == 2 and metadata.get("model_code"):
                    ws_sum.cell(new_min_r, new_min_c).value = f"Nissan {metadata['model_code']}"

        # 3. Populate new block metadata
        hw_row = new_block_start
        sw_row = new_block_start + 1
        micom_row = new_block_start + 2

        ws_sum.cell(hw_row, 3, metadata.get("hw_version", "C"))
        ws_sum.cell(sw_row, 3, metadata.get("sw_version", ""))
        ws_sum.cell(micom_row, 3, metadata.get("micom_version", "v3.27.37"))

        # Build normalized lookup for all_suite_metrics
        norm_metrics = {}
        for k, v in all_suite_metrics.items():
            norm_metrics[_norm_key(k)] = v

        # 4. Suite Mapping: Map rows in block to suite names
        suite_rows_start = new_block_start + 4  # First test row (ATS)
        suite_rows_end = new_block_end - 1      # Last test row (CTS-Verifier)

        for r in range(suite_rows_start, suite_rows_end + 1):
            cell_val = str(ws_sum.cell(r, 3).value or "").strip()
            if not cell_val:
                continue

            # Determine suite key
            c_clean = _norm_key(cell_val)
            matched_key = None
            if "atsinteractive" in c_clean or "interactive" in c_clean:
                matched_key = "atsinteractive"
            elif "atsmultidevice" in c_clean or "multidevice" in c_clean:
                matched_key = "atsmultidevice"
            elif "atsincar" in c_clean or "incar" in c_clean:
                matched_key = "atsincar"
            elif c_clean.startswith("ats"):
                matched_key = "ats"
            elif "ctsongsi" in c_clean or "gsi" in c_clean:
                matched_key = "ctsongsi"
            elif "ctsverifier" in c_clean or "verifier" in c_clean:
                matched_key = "ctsverifier"
            elif c_clean.startswith("cts"):
                matched_key = "cts"
            elif "bfg" in c_clean:
                matched_key = "bfg"
            elif "sts" in c_clean:
                matched_key = "sts"
            elif "vts" in c_clean:
                matched_key = "vts"

            m = norm_metrics.get(matched_key) if matched_key else None
            if m:
                # Update Test Category name with version from C7 / XML for all test suites
                raw_suite_c7 = m.get("test_suite_raw")
                if raw_suite_c7:
                    ver_str = extract_suite_version_from_c7(raw_suite_c7)
                    if ver_str:
                        base_suite_name = cell_val.split("(")[0].strip() if "(" in cell_val else cell_val.strip()
                        ws_sum.cell(r, 3, f"{base_suite_name} ({ver_str})")

                ws_sum.cell(r, 4, m["pass"])            # Col D: Pass
                ws_sum.cell(r, 5, m["fail"])            # Col E: Fail
                ws_sum.cell(r, 6, m["assumption"])      # Col F: Assumption Failure
                ws_sum.cell(r, 7, m["ignored"])         # Col G: Ignored
                ws_sum.cell(r, 8, m["total"])           # Col H: Total Tests
                ws_sum.cell(r, 9, m["done"])            # Col I: Module Done
                ws_sum.cell(r, 10, m["total_module"])   # Col J: Total Module
            else:
                for c in range(4, 11):
                    ws_sum.cell(r, c, None)

        # 5. Populate Summary Row formulas
        sum_r = new_block_end
        for col_idx, col_letter in enumerate(["D", "E", "F", "G", "H", "I", "J"], start=4):
            ws_sum.cell(sum_r, col_idx, f"=SUM({col_letter}{suite_rows_start}:{col_letter}{suite_rows_end})")

        # -------------------------------------------------------------
        # 6. Update Sheet: Nissan Fail Module List
        # -------------------------------------------------------------
        SUITE_CANONICAL_ORDER = [
            "ats", "atsincar", "atsinteractive", "atsmultidevice",
            "bfg", "cts", "ctsongsi", "sts", "vts", "ctsverifier"
        ]
        def get_order_key(item):
            cat = _norm_key(item.get("category", ""))
            for idx, k in enumerate(SUITE_CANONICAL_ORDER):
                if k in cat or cat in k:
                    return idx
            return 99

        all_failed_modules = []
        all_failed_testcases = []
        for s_data in all_suite_metrics.values():
            all_failed_modules.extend(s_data.get("failed_modules", []))
            all_failed_testcases.extend(s_data.get("failed_testcases", []))

        all_failed_modules.sort(key=get_order_key)
        all_failed_testcases.sort(key=get_order_key)

        if "Nissan Fail Module List" in wb.sheetnames:
            ws_fmod = wb["Nissan Fail Module List"]

            # Only clear DATA (values), preserving existing green fill, font, and borders!
            for r in range(3, ws_fmod.max_row + 1):
                for c in range(2, 11):
                    ws_fmod.cell(r, c).value = None

            green_fill = PatternFill(fill_type='solid', start_color='FFD4E9A9', end_color='FFD4E9A9')
            font_arial = Font(name='Arial', size=11.0, bold=False)
            align_center = Alignment(horizontal='center', vertical='center')

            for idx, fmod in enumerate(all_failed_modules):
                cur_r = 3 + idx
                ws_fmod.cell(cur_r, 2, fmod["category"])
                ws_fmod.cell(cur_r, 3, fmod["module"])
                ws_fmod.cell(cur_r, 4, fmod["passed"])
                ws_fmod.cell(cur_r, 5, fmod["failed"])
                ws_fmod.cell(cur_r, 6, fmod["assumption"])
                ws_fmod.cell(cur_r, 7, fmod["ignored"])
                ws_fmod.cell(cur_r, 8, fmod["total_tests"])
                ws_fmod.cell(cur_r, 9, fmod["done"])
                ws_fmod.cell(cur_r, 10, fmod.get("remark") or None)

                for c in range(2, 11):
                    cell = ws_fmod.cell(cur_r, c)
                    if not cell.fill or not cell.fill.fill_type:
                        cell.fill = green_fill
                    if not cell.font or not cell.font.name:
                        cell.font = font_arial
                    if not cell.alignment or not cell.alignment.horizontal:
                        cell.alignment = align_center

                    ref_cell = ws_fmod.cell(3, c)
                    if ref_cell.border and (not cell.border or not cell.border.top or not cell.border.top.style):
                        cell.border = Border(
                            left=ref_cell.border.left,
                            right=ref_cell.border.right,
                            top=ref_cell.border.top,
                            bottom=ref_cell.border.bottom
                        )

        # -------------------------------------------------------------
        # 7. Update Sheet: Nissan Fail TestCase List
        # -------------------------------------------------------------
        if "Nissan Fail TestCase List" in wb.sheetnames:
            ws_ftc = wb["Nissan Fail TestCase List"]

            # Only clear DATA (values), preserving existing green fill, font, and borders!
            for r in range(3, ws_ftc.max_row + 1):
                for c in range(1, 5):
                    ws_ftc.cell(r, c).value = None

            green_fill = PatternFill(fill_type='solid', start_color='FFD4E9A9', end_color='FFD4E9A9')
            font_arial = Font(name='Arial', size=11.0, bold=False)
            align_center = Alignment(horizontal='center', vertical='center')

            for idx, ftc in enumerate(all_failed_testcases):
                cur_r = 3 + idx
                ws_ftc.cell(cur_r, 1, idx + 1)              # Col A: No
                ws_ftc.cell(cur_r, 2, ftc["category"])      # Col B: Category
                ws_ftc.cell(cur_r, 3, ftc["module"])        # Col C: Module
                ws_ftc.cell(cur_r, 4, ftc["test_case"])     # Col D: Test Case

                for c in range(1, 5):
                    cell = ws_ftc.cell(cur_r, c)
                    if not cell.fill or not cell.fill.fill_type:
                        cell.fill = green_fill
                    if not cell.font or not cell.font.name:
                        cell.font = font_arial
                    if not cell.alignment or not cell.alignment.horizontal:
                        cell.alignment = align_center

                    ref_cell = ws_ftc.cell(3, c)
                    if ref_cell.border and (not cell.border or not cell.border.top or not cell.border.top.style):
                        cell.border = Border(
                            left=ref_cell.border.left,
                            right=ref_cell.border.right,
                            top=ref_cell.border.top,
                            bottom=ref_cell.border.bottom
                        )

        wb.save(output_path)
        return True, "Cập nhật Summary workbook thành công."
    except Exception as e:
        return False, f"Lỗi cập nhật file Summary {output_path}: {str(e)}"
