#!/usr/bin/env python3
# ==============================================================================
# Script: parse_tradefed_results.py
# Mục đích: Phân tích nhanh test_result.xml của session mới nhất trong android-cts/results/
# Sử dụng: python3 parse_tradefed_results.py [path_to_results_dir]
# ==============================================================================

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

def get_latest_session_dir(results_dir):
    p = Path(results_dir)
    if not p.is_dir():
        print(f"❌ Thư mục không tồn tại: {results_dir}")
        sys.exit(1)
    
    subdirs = [d for d in p.iterdir() if d.is_dir() and (d / "test_result.xml").is_file()]
    if not subdirs:
        print(f"❌ Không tìm thấy session nào có test_result.xml trong {results_dir}")
        sys.exit(1)
    
    # Sắp xếp theo tên thư mục (timestamp yyyy.mm.dd_hh.mm.ss)
    subdirs.sort(key=lambda x: x.name)
    return subdirs[-1], len(subdirs) - 1

def parse_session(session_dir, session_idx):
    xml_path = session_dir / "test_result.xml"
    print(f"\n=======================================================")
    print(f"📊 PHÂN TÍCH KẾT QUẢ CTS ON GSI - SESSION #{session_idx}")
    print(f"📁 Thư mục: {session_dir.name}")
    print(f"📄 XML: {xml_path}")
    print(f"=======================================================")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    summary = root.find("Summary")
    if summary is None:
        print("❌ Không tìm thấy thẻ <Summary> trong XML.")
        return

    pass_count = int(summary.get("pass", 0))
    failed_count = int(summary.get("failed", 0))
    not_exec_count = int(summary.get("notExecuted", 0))
    modules_done = int(summary.get("modules_done", 0))
    modules_total = int(summary.get("modules_total", 0))
    total_cases = pass_count + failed_count + not_exec_count

    pass_rate = (pass_count / total_cases * 100) if total_cases > 0 else 0.0

    print(f"\n📈 TỔNG KẾT:")
    print(f"  • Modules:       {modules_done}/{modules_total} Done")
    print(f"  • Pass:          {pass_count:,}")
    print(f"  • Failed:        {failed_count:,}")
    print(f"  • Not Executed:  {not_exec_count:,}")
    print(f"  • Tỷ lệ Pass:    {pass_rate:.2f}%")

    if failed_count == 0 and not_exec_count == 0:
        print("\n🎉 CHÚC MỪNG: KẾT QUẢ ĐẠT 100% PASS (0 FAILS, 0 NOT_EXECUTED)!")
        return

    # Liệt kê chi tiết các ca thất bại
    failures = {}
    for module in root.findall("Module"):
        mod_name = module.get("name")
        mod_abi = module.get("abi", "")
        for testcase in module.findall(".//TestCase"):
            tc_name = testcase.get("name")
            for test in testcase.findall("Test"):
                if test.get("result") == "fail":
                    t_name = test.get("name")
                    full_name = f"{tc_name}#{t_name}"
                    failures.setdefault(mod_name, []).append(full_name)

    print(f"\n🔍 DANH SÁCH MODULE & TEST CASES BỊ FAIL ({len(failures)} modules):")
    for mod, tests in failures.items():
        print(f"\n  📦 Module: {mod} ({len(tests)} fails)")
        for t in tests[:10]:
            print(f"     ❌ {t}")
        if len(tests) > 10:
            print(f"     ... và {len(tests) - 10} ca khác")

    # Gợi ý lệnh Tradefed
    print(f"\n💡 GỢI Ý CÂU LỆNH RETRY TIẾP THEO:")
    print(f"  1. Retry toàn bộ FAILED của session này (Tầng 3):")
    print(f"     run retry --retry {session_idx} --retry-type FAILED -s <serial>")
    if not_exec_count > 0:
        print(f"  2. Retry các test NOT_EXECUTED (nếu bị gián đoạn):")
        print(f"     run retry --retry {session_idx} --retry-type NOT_EXECUTED -s <serial>")
    print(f"  3. Retry từng module bị fail (Tầng 2):")
    for mod in list(failures.keys())[:3]:
        print(f"     run cts-on-gsi -m {mod} -s <serial>")

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    latest_dir, idx = get_latest_session_dir(target_dir)
    parse_session(latest_dir, idx)
