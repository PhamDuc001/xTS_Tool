#!/usr/bin/env python3
# ==============================================================================
# Script: generate_full_cts_report.py
# Mục đích: Hợp nhất toàn bộ 14 Single modules + Multiple main run thành bộ báo cáo chuẩn
# Sử dụng: python3 generate_full_cts_report.py [output_path]
# ==============================================================================

import os
import sys
import subprocess

DEFAULT_OUTPUT = "/home/lge/GoogleQA/P33B_26MY/03.REPORT/01.Full/"
REPORT_GENERATOR_TOOL = "/home/lge/Environment/tools/GenerReport_Update_0623/ReportGenerator.py"

def generate_report(output_dir):
    print(f"📊 [Report Generator] Đang khởi chạy tổng hợp báo cáo kiểm chuẩn CTS...")
    print(f"📁 Thư mục xuất: {output_dir}")

    if not os.path.isfile(REPORT_GENERATOR_TOOL):
        print(f"❌ Không tìm thấy công cụ ReportGenerator tại: {REPORT_GENERATOR_TOOL}")
        sys.exit(1)

    cmd = ["python3", REPORT_GENERATOR_TOOL, "-p", output_dir]
    print(f"🚀 Lệnh: {' '.join(cmd)}")
    
    try:
        res = subprocess.run(cmd, check=True)
        print("\n✅ Tổng hợp báo cáo hoàn tất thành công!")
        print(f"📦 Các gói báo cáo sẵn sàng nộp tại: {output_dir}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi khi tổng hợp báo cáo: {e}")
        sys.exit(1)

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    generate_report(out)
