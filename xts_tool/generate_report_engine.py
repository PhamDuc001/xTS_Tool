"""
Generate Report Engine & QThread Worker for xTS Pre-Setup & Report Tool.
Orchestrates multi-server pipeline across Connected Server, APTRA, and GOOGLEQA:
Step 1: Execute ReportGenerator.py on connected server
Step 2: Sync raw archives & analysis inputs to GOOGLEQA & APTRA (100% parallel)
Step 3: Request APTRA analysis (interactive confirmation dialog)
Step 4: Download lightweight result files (*Result.xlsx, template summary, CTS_Verifier XML) to Local Windows
Step 5: Standardize and clean individual suite reports (03.*.xlsx) using local openpyxl
Step 6: Update and generate Google Certification Summary workbook
Step 7: Publish standardized reports and Summary to GOOGLEQA release directory
"""
import os
import re
import time
import shutil
import threading
from typing import Dict, List, Any, Optional, Callable, Tuple
import paramiko
from PyQt6.QtCore import QThread, pyqtSignal

import excel_report_formatter as erf


SUITE_KEY_MAPPING = {
    # AtsIncar
    "AtsIncarResult.xlsx": "AtsIncar",
    "AtsIncarResults.xlsx": "AtsIncar",
    # AtsInteractive
    "AtsInteractiveResult.xlsx": "AtsInteractive",
    "AtsInteractiveResults.xlsx": "AtsInteractive",
    # AtsMultidevice
    "AtsMultideviceResult.xlsx": "AtsMultidevice",
    "AtsMultideviceResults.xlsx": "AtsMultidevice",
    # ATS
    "ATSResult.xlsx": "ATS",
    "ATSResults.xlsx": "ATS",
    # BFG
    "BFGResult.xlsx": "BFG",
    "BFGResults.xlsx": "BFG",
    # CTS
    "CTSResult.xlsx": "CTS",
    "CTSResults.xlsx": "CTS",
    # CTSonGSI
    "CTSonGSIResult.xlsx": "CTSonGSI",
    "CTSonGSIResults.xlsx": "CTSonGSI",
    # STS
    "STSResult.xlsx": "STS",
    "STSResults.xlsx": "STS",
    # VTS
    "VTSResult.xlsx": "VTS",
    "VTSResults.xlsx": "VTS",
}

# Specific suites must be matched before generic substrings (e.g. AtsInteractive before ATS)
SUITE_MATCH_PRIORITY = [
    ("atsinteractive", "AtsInteractive"),
    ("atsmultidevice", "AtsMultidevice"),
    ("atsincar", "AtsIncar"),
    ("ctsongsi", "CTSonGSI"),
    ("ctsverifier", "CTS_Verifier"),
    ("ats", "ATS"),
    ("cts", "CTS"),
    ("bfg", "BFG"),
    ("sts", "STS"),
    ("vts", "VTS"),
]

STEP_TITLES = [
    "1. Chạy ReportGenerator",
    "2. Đồng bộ dữ liệu phân tích sang APTRA",
    "3. Xác nhận phân tích trên APTRA",
    "4. Tải file kết quả về Local Windows",
    "5. Chuẩn hóa các file Excel con (03.*.xlsx)",
    "6. Tạo & Cập nhật file Summary",
    "7. Phát hành báo cáo Excel lên GOOGLEQA",
    "8. Đồng bộ gói lưu trữ nặng sang GOOGLEQA (01.*, 00.OEM, 02.*)",
]


class GenerateReportWorker(QThread):
    # Logging & Progress Signals
    log_signal = pyqtSignal(str, str)  # (message, level: 'INFO', 'WARN', 'ERROR', 'SUCCESS', 'STREAM')
    progress_signal = pyqtSignal(int, int)  # (current_step, total_steps)
    step_started_signal = pyqtSignal(int, str)  # (step_idx, step_name)
    step_finished_signal = pyqtSignal(int, str, bool)  # (step_idx, step_name, success)
    workflow_finished_signal = pyqtSignal(bool, str)  # (overall_success, summary_message)

    # Interactive Signal for Step 4 (APTRA analysis completion)
    request_aptra_confirm_signal = pyqtSignal(str)  # (prompt_message)

    def __init__(self, ssh_mgr, params: Dict[str, Any], single_step_idx: Optional[int] = None):
        super().__init__()
        self.ssh = ssh_mgr
        self.params = params
        self.single_step_idx = single_step_idx
        self._abort_requested = False

        # APTRA Interactive confirmation sync event
        self._aptra_confirm_event = threading.Event()
        self._aptra_confirmed = False

    def request_abort(self):
        """Signals worker to abort execution."""
        self._abort_requested = True
        self._aptra_confirm_event.set()

    def is_aborted(self) -> bool:
        return self._abort_requested

    def provide_aptra_confirmation(self, confirmed: bool):
        """Called by UI when user confirms or cancels APTRA pop-up."""
        self._aptra_confirmed = confirmed
        self._aptra_confirm_event.set()

    def log(self, text: str, level: str = "INFO"):
        self.log_signal.emit(text, level)

    def run(self):
        """Worker main execution entry."""
        self.log("=== BẮT ĐẦU QUY TRÌNH TẠO BÁO CÁO CHỨNG CHỈ (GENERATE REPORT) ===", "INFO")
        
        # Verify SSH connection
        if not self.ssh or not self.ssh.is_connected():
            self.log("[ERROR] Chưa kết nối SSH tới máy chủ!", "ERROR")
            self.workflow_finished_signal.emit(False, "Chưa kết nối SSH tới máy chủ.")
            return

        step_methods = [
            self._step1_run_report_generator,
            self._step2_sync_to_aptra,
            self._step3_wait_aptra_confirmation,
            self._step4_download_to_local,
            self._step5_format_single_suites,
            self._step6_update_summary_workbook,
            self._step7_publish_to_googleqa,
            self._step8_sync_heavy_archives_to_googleqa,
        ]

        if self.single_step_idx is not None:
            if 0 <= self.single_step_idx < len(step_methods):
                steps_to_run = [(self.single_step_idx, STEP_TITLES[self.single_step_idx], step_methods[self.single_step_idx])]
            else:
                self.log(f"[ERROR] Bước không hợp lệ: {self.single_step_idx}", "ERROR")
                self.workflow_finished_signal.emit(False, "Bước không hợp lệ.")
                return
        else:
            auto_heavy = self.params.get("auto_upload_heavy_archives", False)
            num_steps = len(step_methods) if auto_heavy else 7
            steps_to_run = [(idx, STEP_TITLES[idx], step_methods[idx]) for idx in range(num_steps)]

        total = len(steps_to_run)
        all_success = True

        for i, (orig_idx, title, step_fn) in enumerate(steps_to_run):
            if self._abort_requested:
                self.log("\n[WARN] Tiến trình đã bị người dùng dừng lại.", "WARN")
                all_success = False
                break

            self.progress_signal.emit(i + 1, total)
            self.step_started_signal.emit(orig_idx, title)
            self.log(f"\n=======================================================", "INFO")
            self.log(f">>> [{i+1}/{total}] {title}", "INFO")
            self.log(f"=======================================================", "INFO")

            try:
                ok, msg = step_fn()
            except Exception as e:
                ok = False
                msg = f"Ngoại lệ khi thực thi: {str(e)}"
                self.log(f"[EXCEPTION] {msg}", "ERROR")

            if ok:
                self.log(f"[SUCCESS] Hoàn thành: {title} - {msg}", "SUCCESS")
                self.step_finished_signal.emit(orig_idx, title, True)
            else:
                self.log(f"[FAILED] Thất bại: {title} - {msg}", "ERROR")
                self.step_finished_signal.emit(orig_idx, title, False)
                all_success = False
                break

        if all_success:
            self.log("\n🎉 TOÀN BỘ CÁC BƯỚC ĐÃ ĐƯỢC THỰC HIỆN THÀNH CÔNG RỰC RỠ!", "SUCCESS")
            self.workflow_finished_signal.emit(True, "Tất cả các bước báo cáo hoàn tất thành công.")
        else:
            self.log("\n⚠️ QUY TRÌNH KẾT THÚC CÓ LỖI HOẶC BỊ HỦY BỎ.", "WARN")
            self.workflow_finished_signal.emit(False, "Quy trình kết thúc có lỗi.")

    # -------------------------------------------------------------------------
    # Helper: Paths & Config Extraction
    # -------------------------------------------------------------------------
    def _get_paths(self) -> Dict[str, str]:
        raw_path = self.params.get("raw_path", "/home/lge/GoogleQA/Report_tmp/01.Full/").rstrip("/").rstrip("\\")
        # Determine parent folder
        if raw_path.endswith("01.Full"):
            raw_parent = os.path.dirname(raw_path).replace("\\", "/")
        else:
            raw_parent = raw_path

        model_full = self.params.get("model_full", "Nissan_AIVI_Full_12.3_PZ1D_26MY").strip()
        model_code = self.params.get("model_code", "PZ1D").strip()
        sw_version = self.params.get("sw_version", "YAK.31.03.30").strip()
        short_sw = sw_version.split(".", 1)[-1] if "." in sw_version else sw_version

        googleqa_dest_path = self.params.get("googleqa_dest_path", "").strip()
        if not googleqa_dest_path:
            googleqa_dest_path = f"/home/googleqa/GOOGLEQA/Official_Test_results/{model_full}/{sw_version}"
        googleqa_dest_path = googleqa_dest_path.rstrip("/").rstrip("\\")

        aptra_path = self.params.get("aptra_path", "").strip()
        if not aptra_path:
            aptra_path = f"/home/aptra/APTRA/{model_full}/{sw_version}"
        aptra_path = aptra_path.rstrip("/").rstrip("\\")

        tool_root = os.path.dirname(os.path.abspath(__file__))
        local_work_dir = self.params.get(
            "local_work_dir",
            os.path.abspath(os.path.join(tool_root, "temp_report", sw_version))
        )

        return {
            "raw_path": raw_path,
            "raw_parent": raw_parent,
            "model_full": model_full,
            "model_code": model_code,
            "sw_version": sw_version,
            "short_sw": short_sw,
            "googleqa_dest_path": googleqa_dest_path,
            "aptra_path": aptra_path,
            "hw_version": self.params.get("hw_version", "C").strip(),
            "micom_version": self.params.get("micom_version", "v3.27.37").strip(),
            "oem_delivery_date": self.params.get("oem_delivery_date", "").strip(),
            "test_start_date": self.params.get("test_start_date", "").strip(),
            "test_end_date": self.params.get("test_end_date", "").strip(),
            "tester_name": self.params.get("tester_name", "").strip(),
            "prev_summary_path": self.params.get("prev_summary_path", "").strip(),
            "generator_script": self.params.get("report_generator_script", "/home/lge/Environment/tools/GenerReport_Update_0623/ReportGenerator.py").strip(),
            "local_work_dir": local_work_dir,
            "local_raw_dir": os.path.join(local_work_dir, "raw_excel"),
            "local_final_dir": os.path.join(local_work_dir, "final_reports"),
        }

    def _open_sftp_connection(self, host: str, port: int, user: str, password: str) -> Tuple[paramiko.SSHClient, paramiko.SFTPClient]:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=port, username=user, password=password, timeout=15)
        sftp = client.open_sftp()
        return client, sftp

    # -------------------------------------------------------------------------
    # Step 1: Execute ReportGenerator.py
    # -------------------------------------------------------------------------
    def _step1_run_report_generator(self) -> Tuple[bool, str]:
        p = self._get_paths()
        script = p["generator_script"]
        raw_path = p["raw_path"]

        self.log(f"Kiểm tra script ReportGenerator tại: {script}", "INFO")
        c_check, o_check, _ = self.ssh.run_command(f"test -f '{script}' && echo EXISTS")
        if "EXISTS" not in o_check:
            return False, f"Không tìm thấy file kịch bản ReportGenerator tại: {script}"

        # Double protection: pipe 'Y' to stdin AND enable auto_confirm_yn in PTY stream
        cmd = f"printf 'Y\\n' | python3 '{script}' -p '{raw_path}'"
        self.log(f"Thực thi lệnh: {cmd}", "INFO")

        def stream_cb(chunk: str):
            self.log(chunk, "STREAM")

        code, out = self.ssh.run_command_stream(
            cmd,
            output_callback=stream_cb,
            check_abort=self.is_aborted,
            auto_confirm_yn=True
        )

        if code != 0:
            return False, f"ReportGenerator kết thúc với mã lỗi: {code}"

        # Check expected outputs in raw_parent
        raw_parent = p["raw_parent"]
        chk_cmd = f"test -d '{raw_parent}/00.Internal' && echo OK"
        _, o_ok, _ = self.ssh.run_command(chk_cmd)
        if "OK" not in o_ok:
            return False, f"Không tìm thấy thư mục kết quả '00.Internal' tại: {raw_parent}"
        return True, "ReportGenerator đã hoàn tất và cấu trúc 00.Internal/ đã sẵn sàng."

    # -------------------------------------------------------------------------
    # Step 2: Sync Analysis Data (*Results) to APTRA
    # -------------------------------------------------------------------------
    def _step2_sync_to_aptra(self) -> Tuple[bool, str]:
        p = self._get_paths()
        raw_parent = p["raw_parent"]
        dest_aptra = p["aptra_path"]

        aptra_cfg = self.params.get("aptra_server", {})
        aptra_host = aptra_cfg.get("host", "loghub.lge.com")
        aptra_user = aptra_cfg.get("username", "aptra")
        aptra_pass = aptra_cfg.get("password", "aptra")

        self.log(f"Đích APTRA: {dest_aptra} (host: {aptra_host})", "INFO")
        self.log("Bắt đầu đồng bộ thư mục phân tích *Results sang APTRA (4 luồng song song)...", "INFO")

        sync_script = f"""bash -c '
set -e
DEST_APTRA="{dest_aptra}"
USER_PASS_APTRA="{aptra_user}:{aptra_pass}"
SFTP_BASE_APTRA="sftp://{aptra_host}$DEST_APTRA"
MAX_CONCURRENT_APTRA=4

ERR_FLAG_APTRA="/tmp/sync_aptra_err_$$"
rm -f "$ERR_FLAG_APTRA"

if [ ! -d "{raw_parent}/00.Internal" ]; then
    echo "[APTRA] LỖI: Thư mục kết quả {raw_parent}/00.Internal không tồn tại!" >&2
    exit 1
fi

cd "{raw_parent}/00.Internal"

local_dirs=()
while IFS= read -r d; do
    if [ -n "$d" ]; then
        local_dirs+=("$d")
    fi
done <<EOF
$(find *Results -type d 2>/dev/null)
EOF

tmp_aptra_list="/tmp/aptra_remote_list_$$"
rm -f "$tmp_aptra_list"
for d in "${{local_dirs[@]}}"; do
    (
        curl -s -k -u "$USER_PASS_APTRA" "$SFTP_BASE_APTRA/$d/" 2>/dev/null | awk -v dir="$d" '"'"'/^-/{{sz=$5; for(i=1;i<=8;i++)$i=""; sub(/^[ \t]+/, ""); print sz, dir"/"$0}}'"'"' >> "$tmp_aptra_list"
    ) &
done
wait

declare -A remote_sizes_aptra
while IFS=" " read -r rsz relpath; do
    if [ -n "$relpath" ] && [ -n "$rsz" ]; then
        remote_sizes_aptra["$relpath"]="$rsz"
    fi
done < "$tmp_aptra_list"
rm -f "$tmp_aptra_list"

raw_aptra_files=()
while IFS= read -r file; do
    if [ -n "$file" ]; then
        raw_aptra_files+=("$file")
    fi
done <<EOF
$(find *Results -type f 2>/dev/null)
EOF

aptra_files=()
while IFS= read -r sz_and_path; do
    fpath="${{sz_and_path#* }}"
    if [ -n "$fpath" ]; then
        aptra_files+=("$fpath")
    fi
done < <(for f in "${{raw_aptra_files[@]}}"; do
    stat -c "%s %n" "$f" 2>/dev/null || echo "0 $f"
done | sort -rn)

TOTAL_APTRA=${{#aptra_files[@]}}
if [ "$TOTAL_APTRA" -eq 0 ]; then
    echo "[APTRA] CẢNH BÁO: Không tìm thấy file trong các thư mục *Results để upload!"
else
    echo "[APTRA] === Tổng cộng $TOTAL_APTRA file trong *Results cần xử lý sang APTRA (ưu tiên file lớn trước, tối đa $MAX_CONCURRENT_APTRA luồng) ==="
fi

DONE_DIR_APTRA="/tmp/aptra_done_$$"
rm -rf "$DONE_DIR_APTRA"
mkdir -p "$DONE_DIR_APTRA"

idx_a=0
for f in "${{aptra_files[@]}}"; do
    idx_a=$((idx_a + 1))
    local_size=$(stat -c "%s" "$f" 2>/dev/null || echo 0)
    hsize=$(du -h "$f" 2>/dev/null | cut -f1)
    rsize="${{remote_sizes_aptra[$f]}}"

    if [ -n "$rsize" ] && [ "$rsize" -eq "$local_size" ] && [ "$local_size" -gt 0 ]; then
        touch "$DONE_DIR_APTRA/$idx_a"
        done_cnt=$(ls -1 "$DONE_DIR_APTRA" 2>/dev/null | wc -l)
        echo "[APTRA] ⏩ [$done_cnt/$TOTAL_APTRA] Bỏ qua (đã có trên server, khớp $local_size byte): $f"
        continue
    fi

    (
        echo "[APTRA] >>> [Khởi chạy $idx_a/$TOTAL_APTRA] Đang upload: $f ($hsize) ..."
        if curl -sS -k -u "$USER_PASS_APTRA" --ftp-create-dirs -T "$f" "$SFTP_BASE_APTRA/$f"; then
            touch "$DONE_DIR_APTRA/$idx_a"
            done_cnt=$(ls -1 "$DONE_DIR_APTRA" 2>/dev/null | wc -l)
            echo "[APTRA] ✓ [$done_cnt/$TOTAL_APTRA hoàn tất] $f"
        else
            echo "[APTRA] ✗ [Thất bại] $f" >&2
            touch "$ERR_FLAG_APTRA"
        fi
    ) &

    while [ $(jobs -r -p | wc -l) -ge $MAX_CONCURRENT_APTRA ]; do
        wait -n 2>/dev/null || sleep 0.2
    done
done

pending_jobs=$(jobs -r -p | wc -l)
if [ "$pending_jobs" -gt 0 ]; then
    echo "[APTRA] ⏳ Đã điều phối xong toàn bộ $TOTAL_APTRA file. Đang chờ $pending_jobs luồng tải nền (file dung lượng lớn) hoàn tất..."
fi

wait
rm -rf "$DONE_DIR_APTRA"

if [ -f "$ERR_FLAG_APTRA" ]; then
    rm -f "$ERR_FLAG_APTRA"
    echo "LỖI: Upload sang server APTRA có lỗi!" >&2
    exit 1
fi

echo "SYNC_APTRA_COMPLETE"
'"""

        def stream_cb(chunk: str):
            self.log(chunk, "STREAM")

        code, out = self.ssh.run_command_stream(sync_script, output_callback=stream_cb, check_abort=self.is_aborted)
        if code != 0 or "SYNC_APTRA_COMPLETE" not in out:
            return False, f"Lỗi khi đồng bộ sang APTRA (code: {code})"

        return True, f"Đã đồng bộ thành công dữ liệu phân tích sang APTRA ({dest_aptra})"

    # -------------------------------------------------------------------------
    # Step 3: Wait for User Confirmation on APTRA Analysis
    # -------------------------------------------------------------------------
    def _step3_wait_aptra_confirmation(self) -> Tuple[bool, str]:
        p = self._get_paths()
        prompt_msg = (
            f"Dữ liệu kiểm thử đã được upload thành công sang Server APTRA:\n"
            f"{p['aptra_path']}/\n\n"
            "Vui lòng request kích hoạt chạy công cụ phân tích trên APTRA.\n"
            "Sau khi server APTRA hoàn tất xử lý (sinh các file *Result.xlsx), "
            "hãy nhấn nút [ĐÃ CHẠY XONG - TIẾP TỤC] bên dưới để tiếp tục quy trình."
        )

        self.log("\n[INTERACTION] Hiển thị hộp thoại chờ xác nhận hoàn tất chạy trên APTRA...", "WARN")
        self._aptra_confirm_event.clear()
        self._aptra_confirmed = False
        self.request_aptra_confirm_signal.emit(prompt_msg)

        # Wait for user click in GUI
        self._aptra_confirm_event.wait()

        if self._abort_requested or not self._aptra_confirmed:
            return False, "Người dùng đã hủy bỏ xác nhận phân tích APTRA."

        # Quick validation on APTRA server via SFTP
        self.log("Đang kiểm tra kết quả phân tích trên APTRA...", "INFO")
        aptra_cfg = self.params.get("aptra_server", {})
        host = aptra_cfg.get("host", "loghub.lge.com")
        port = aptra_cfg.get("port", 22)
        user = aptra_cfg.get("username", "aptra")
        password = aptra_cfg.get("password", "aptra")

        try:
            client, sftp = self._open_sftp_connection(host, port, user, password)
            remote_dir = p["aptra_path"]
            files = sftp.listdir(remote_dir)
            sftp.close()
            client.close()

            excel_files = [f for f in files if f.endswith("Result.xlsx") or f.endswith("Results.xlsx")]
            csv_files = [f for f in files if f.endswith(".csv")]
            self.log(f"Tìm thấy {len(excel_files)} file Excel kết quả và {len(csv_files)} file CSV trên APTRA.", "SUCCESS")
            if not excel_files:
                self.log("[WARN] Chưa tìm thấy file *Result.xlsx trên APTRA! Tiếp tục với các dữ liệu hiện có.", "WARN")
        except Exception as e:
            self.log(f"[WARN] Không thể kiểm tra trực tiếp APTRA: {e}", "WARN")

        return True, "Người dùng đã xác nhận hoàn tất phân tích trên APTRA."

    # -------------------------------------------------------------------------
    # Step 4: Download lightweight result files to Local Windows
    # -------------------------------------------------------------------------
    def _step4_download_to_local(self) -> Tuple[bool, str]:
        p = self._get_paths()
        local_raw = p["local_raw_dir"]
        local_work = p["local_work_dir"]
        os.makedirs(local_raw, exist_ok=True)
        os.makedirs(p["local_final_dir"], exist_ok=True)

        aptra_cfg = self.params.get("aptra_server", {})
        googleqa_cfg = self.params.get("googleqa_server", {})

        # 1. Download *Result.xlsx from APTRA
        self.log("Kết nối SFTP tới APTRA để tải các file kết quả kiểm thử (.xlsx)...", "INFO")
        try:
            client, sftp = self._open_sftp_connection(
                aptra_cfg.get("host", "loghub.lge.com"),
                aptra_cfg.get("port", 22),
                aptra_cfg.get("username", "aptra"),
                aptra_cfg.get("password", "aptra")
            )
            remote_dir = p["aptra_path"]
            files = sftp.listdir(remote_dir)
            downloaded_suites = 0

            for fname in files:
                if fname.endswith("Result.xlsx") or fname.endswith("Results.xlsx"):
                    rpath = f"{remote_dir}/{fname}"
                    lpath = os.path.join(local_raw, fname)
                    self.log(f"  -> Tải từ APTRA: {fname}", "INFO")
                    sftp.get(rpath, lpath)
                    downloaded_suites += 1

            sftp.close()
            client.close()
            self.log(f"Đã tải {downloaded_suites} file Excel từ APTRA về: {local_raw}", "SUCCESS")
        except Exception as e:
            return False, f"Lỗi khi tải kết quả từ APTRA: {str(e)}"

        # 2. Download or copy Previous Summary Template
        prev_summary_path = p["prev_summary_path"]
        local_template_path = os.path.join(local_work, "template_summary.xlsx")

        if os.path.exists(prev_summary_path):
            self.log(f"Sử dụng file Summary mẫu từ máy Local: {prev_summary_path}", "INFO")
            shutil.copyfile(prev_summary_path, local_template_path)
        elif prev_summary_path.startswith("/") or "googleqa" in prev_summary_path:
            self.log(f"Tải file Summary mẫu từ GOOGLEQA: {prev_summary_path}", "INFO")
            try:
                client_gq, sftp_gq = self._open_sftp_connection(
                    googleqa_cfg.get("host", "loghub.lge.com"),
                    googleqa_cfg.get("port", 22),
                    googleqa_cfg.get("username", "googleqa"),
                    googleqa_cfg.get("password", "googleqa")
                )
                sftp_gq.get(prev_summary_path, local_template_path)
                sftp_gq.close()
                client_gq.close()
                self.log(f"Đã tải file Summary mẫu về: {local_template_path}", "SUCCESS")
            except Exception as e:
                return False, f"Không thể tải file Summary mẫu từ GOOGLEQA: {str(e)}"
        else:
            return False, f"Không tìm thấy file Summary mẫu tại đường dẫn: {prev_summary_path}"

        # 3. Download CTS_Verifier test_result.xml
        raw_parent = p["raw_parent"]
        cts_ver_dir = f"{raw_parent}/01.Full/01.CTS_Verifier"
        cts_ver_xml_local = os.path.join(local_work, "cts_verifier_result.xml")

        self.log("Dò tìm file test_result.xml của CTS_Verifier trên máy chủ...", "INFO")
        find_cmd = f"find '{cts_ver_dir}' -name 'test_result.xml' 2>/dev/null | head -n 1"
        c_ver, o_ver, _ = self.ssh.run_command(find_cmd)
        if c_ver == 0 and o_ver.strip():
            xml_remote = o_ver.strip()
            self.log(f"Tìm thấy CTS_Verifier XML tại: {xml_remote}", "INFO")
            try:
                sftp_remote = self.ssh.client.open_sftp()
                sftp_remote.get(xml_remote, cts_ver_xml_local)
                sftp_remote.close()
                self.log("Đã tải CTS_Verifier test_result.xml về local.", "SUCCESS")
            except Exception as e:
                self.log(f"[WARN] Lỗi khi tải CTS_Verifier XML: {e}", "WARN")
        else:
            self.log("[WARN] Không tìm thấy test_result.xml của CTS_Verifier. Sẽ bỏ qua số liệu verifier.", "WARN")

        return True, "Đã tải toàn bộ các file kết quả và mẫu báo cáo về máy Local thành công."

    # -------------------------------------------------------------------------
    # Step 5: Standardize and clean individual suite reports (03.*.xlsx)
    # -------------------------------------------------------------------------
    def _step5_format_single_suites(self) -> Tuple[bool, str]:
        p = self._get_paths()
        local_raw = p["local_raw_dir"]
        local_final = p["local_final_dir"]

        raw_files = [f for f in os.listdir(local_raw) if f.endswith(".xlsx")]
        if not raw_files:
            return False, f"Không có file Excel nào trong thư mục: {local_raw}"

        formatted_count = 0
        header_metadata = {
            "model_full": p["model_full"],
            "hw_version": p["hw_version"],
            "sw_version": p["sw_version"],
            "micom_version": p["micom_version"],
            "oem_delivery_date": p["oem_delivery_date"],
            "test_start_date": p["test_start_date"],
            "test_end_date": p["test_end_date"],
            "tester_name": p["tester_name"],
        }

        for raw_fname in raw_files:
            suite_name = SUITE_KEY_MAPPING.get(raw_fname)
            if not suite_name:
                clean_name = re.sub(r'[^a-zA-Z0-9]', '', raw_fname).lower()
                for key_pattern, sname in SUITE_MATCH_PRIORITY:
                    if key_pattern in clean_name:
                        suite_name = sname
                        break
            if not suite_name:
                self.log(f"[SKIP] Bỏ qua file không xác định được bộ test: {raw_fname}", "WARN")
                continue

            target_fname = f"03.LGE_Nissan_AIVI_Full_12.3_{p['model_code']}_{suite_name}_Result_Final_{p['sw_version']}.xlsx"
            source_path = os.path.join(local_raw, raw_fname)
            target_path = os.path.join(local_final, target_fname)

            self.log(f"Chuẩn hóa file {suite_name}: {raw_fname} -> {target_fname}", "INFO")
            ok, err_msg = erf.format_single_suite_report(
                source_path=source_path,
                target_path=target_path,
                metadata=header_metadata
            )
            if not ok:
                self.log(f"[ERROR] Lỗi khi format {raw_fname}: {err_msg}", "ERROR")
                return False, f"Lỗi format {raw_fname}: {err_msg}"

            formatted_count += 1

        return True, f"Đã chuẩn hóa thành công {formatted_count} file báo cáo bộ test (03.*.xlsx)."

    # -------------------------------------------------------------------------
    # Step 6: Update Certification Summary workbook
    # -------------------------------------------------------------------------
    def _step6_update_summary_workbook(self) -> Tuple[bool, str]:
        p = self._get_paths()
        local_work = p["local_work_dir"]
        local_final = p["local_final_dir"]
        os.makedirs(local_final, exist_ok=True)

        template_path = os.path.join(local_work, "template_summary.xlsx")
        summary_fname = f"Nissan_{p['model_code']}_Google Certification Summary_{p['short_sw']}.xlsx"
        output_summary_path = os.path.join(local_final, summary_fname)

        # Collect formatted 03.*.xlsx files
        single_suite_files = {}
        for fname in os.listdir(local_final):
            if fname.startswith("03.") and fname.endswith(".xlsx"):
                fpath = os.path.join(local_final, fname)
                for sname in ["AtsIncar", "AtsInteractive", "AtsMultidevice", "CTSonGSI", "ATS", "BFG", "CTS", "STS", "VTS"]:
                    if f"_{sname}_" in fname:
                        single_suite_files[sname] = fpath
                        break

        self.log(f"Tìm thấy {len(single_suite_files)} file 03.* để trích xuất số liệu vào Summary.", "INFO")
        for sname, spath in single_suite_files.items():
            self.log(f"  + {sname}: {os.path.basename(spath)}", "INFO")

        cts_ver_xml = os.path.join(local_work, "cts_verifier_result.xml")
        cts_ver_xml_path = cts_ver_xml if os.path.exists(cts_ver_xml) else None

        self.log(f"Cập nhật file Summary: {summary_fname} ...", "INFO")
        ok, msg = erf.update_summary_workbook(
            template_path=template_path,
            output_path=output_summary_path,
            metadata={
                "hw_version": p["hw_version"],
                "sw_version": p["sw_version"],
                "micom_version": p["micom_version"],
                "model_code": p["model_code"],
                "model_full": p["model_full"],
            },
            single_suite_files=single_suite_files,
            cts_verifier_xml_path=cts_ver_xml_path
        )

        if not ok:
            return False, f"Lỗi khi cập nhật file Summary: {msg}"

        return True, f"Đã sinh file Summary hoàn chỉnh: {summary_fname}"

    # -------------------------------------------------------------------------
    # Step 7: Publish standardized reports and Summary to GOOGLEQA
    # -------------------------------------------------------------------------
    def _step7_publish_to_googleqa(self) -> Tuple[bool, str]:
        p = self._get_paths()
        local_final = p["local_final_dir"]
        googleqa_cfg = self.params.get("googleqa_server", {})

        host = googleqa_cfg.get("host", "loghub.lge.com")
        port = googleqa_cfg.get("port", 22)
        user = googleqa_cfg.get("username", "googleqa")
        password = googleqa_cfg.get("password", "googleqa")
        remote_dest = p["googleqa_dest_path"]

        self.log(f"Kết nối SFTP tới GOOGLEQA để xuất bản báo cáo ({host}:{port})...", "INFO")
        try:
            client, sftp = self._open_sftp_connection(host, port, user, password)

            # Ensure remote dir exists
            try:
                sftp.stat(remote_dest)
            except Exception:
                parts = remote_dest.strip("/").split("/")
                curr = ""
                for part in parts:
                    curr += "/" + part
                    try:
                        sftp.stat(curr)
                    except Exception:
                        sftp.mkdir(curr)

            files_to_upload = [f for f in os.listdir(local_final) if f.endswith(".xlsx")]
            self.log(f"Bắt đầu upload {len(files_to_upload)} file báo cáo lên GOOGLEQA...", "INFO")

            for fname in files_to_upload:
                lpath = os.path.join(local_final, fname)
                rpath = f"{remote_dest}/{fname}"
                self.log(f"  -> Uploading: {fname} ({os.path.getsize(lpath)} bytes)", "INFO")
                sftp.put(lpath, rpath)

            sftp.close()
            client.close()
            self.log(f"Đã xuất bản thành công {len(files_to_upload)} file lên GOOGLEQA: {remote_dest}", "SUCCESS")
            return True, f"Đã phát hành báo cáo chính thức lên GOOGLEQA: {remote_dest}"
        except Exception as e:
            return False, f"Lỗi khi upload báo cáo lên GOOGLEQA: {str(e)}"

    # -------------------------------------------------------------------------
    # Step 8: Sync Heavy Archive Files to GOOGLEQA (Optional / Standalone)
    # -------------------------------------------------------------------------
    def _step8_sync_heavy_archives_to_googleqa(self) -> Tuple[bool, str]:
        p = self._get_paths()
        raw_parent = p["raw_parent"]
        raw_path = p["raw_path"]
        dest_gq = p["googleqa_dest_path"]

        gq_cfg = self.params.get("googleqa_server", {})
        gq_host = gq_cfg.get("host", "loghub.lge.com")
        gq_user = gq_cfg.get("username", "googleqa")
        gq_pass = gq_cfg.get("password", "googleqa")

        self.log(f"Đích GOOGLEQA: {dest_gq} (host: {gq_host})", "INFO")
        self.log("Bắt đầu đồng bộ gói lưu trữ nặng sang GOOGLEQA (01.*.zip, 00.OEM*.zip, 02.*.zip)...", "INFO")

        sync_script = f"""bash -c '
set -e
DEST_GQ="{dest_gq}"
USER_PASS_GQ="{gq_user}:{gq_pass}"
SFTP_BASE_GQ="sftp://{gq_host}$DEST_GQ"
MAX_CONCURRENT_GQ=4

ERR_FLAG_GQ="/tmp/sync_gq_err_$$"
rm -f "$ERR_FLAG_GQ"

all_targets=()
for f in "{raw_path}"/*.zip "{raw_parent}/01.Full"/*.zip; do
    if [ -f "$f" ]; then
        all_targets+=("$f")
    fi
done

for f in "{raw_parent}"/00.OEM*.zip "{raw_path}"/00.OEM*.zip "{raw_parent}"/00.OEM_APFE*.zip; do
    if [ -f "$f" ]; then
        all_targets+=("$f")
    fi
done

for f in "{raw_parent}/00.Internal"/02.*.zip; do
    if [ -f "$f" ]; then
        all_targets+=("$f")
    fi
done

declare -A seen
unique_files=()
for f in "${{all_targets[@]}}"; do
    fname=$(basename "$f")
    if [[ -z "${{seen[$fname]}}" ]]; then
        seen["$fname"]=1
        unique_files+=("$f")
    fi
done

files=()
while IFS= read -r sz_and_path; do
    fpath="${{sz_and_path#* }}"
    if [ -n "$fpath" ]; then
        files+=("$fpath")
    fi
done < <(for f in "${{unique_files[@]}}"; do
    stat -c "%s %n" "$f" 2>/dev/null || echo "0 $f"
done | sort -rn)

TOTAL=${{#files[@]}}
if [ "$TOTAL" -eq 0 ]; then
    echo "[GOOGLEQA ARCHIVES] CẢNH BÁO: Không tìm thấy file zip nào để upload!"
else
    echo "[GOOGLEQA ARCHIVES] === Tổng cộng $TOTAL file zip cần upload sang GOOGLEQA (tối đa $MAX_CONCURRENT_GQ luồng) ==="
fi

declare -A remote_sizes_gq
while IFS=" " read -r rsize fname; do
    if [ -n "$fname" ] && [ -n "$rsize" ]; then
        remote_sizes_gq["$fname"]="$rsize"
    fi
done < <(curl -s -k -u "$USER_PASS_GQ" "$SFTP_BASE_GQ/" 2>/dev/null | awk '"'"'/^-/{{sz=$5; for(i=1;i<=8;i++)$i=""; sub(/^[ \t]+/, ""); print sz, $0}}'"'"')

DONE_DIR_GQ="/tmp/gq_done_$$"
rm -rf "$DONE_DIR_GQ"
mkdir -p "$DONE_DIR_GQ"

idx=0
for f in "${{files[@]}}"; do
    idx=$((idx + 1))
    fname=$(basename "$f")
    local_size=$(stat -c "%s" "$f" 2>/dev/null || echo 0)
    hsize=$(du -h "$f" 2>/dev/null | cut -f1)
    rsize="${{remote_sizes_gq[$fname]}}"

    if [ -n "$rsize" ] && [ "$rsize" -eq "$local_size" ] && [ "$local_size" -gt 0 ]; then
        touch "$DONE_DIR_GQ/$idx"
        done_cnt=$(ls -1 "$DONE_DIR_GQ" 2>/dev/null | wc -l)
        echo "[GOOGLEQA ARCHIVES] ⏩ [$done_cnt/$TOTAL] Bỏ qua (đã có trên server, khớp $local_size byte): $fname"
        continue
    fi

    (
        echo "[GOOGLEQA ARCHIVES] >>> [Khởi chạy $idx/$TOTAL] Đang upload: $fname ($hsize) ..."
        if curl -sS -k -u "$USER_PASS_GQ" --ftp-create-dirs -T "$f" "$SFTP_BASE_GQ/$fname"; then
            touch "$DONE_DIR_GQ/$idx"
            done_cnt=$(ls -1 "$DONE_DIR_GQ" 2>/dev/null | wc -l)
            echo "[GOOGLEQA ARCHIVES] ✓ [$done_cnt/$TOTAL hoàn tất] $fname"
        else
            echo "[GOOGLEQA ARCHIVES] ✗ [Thất bại] $fname" >&2
            touch "$ERR_FLAG_GQ"
        fi
    ) &

    while [ $(jobs -r -p | wc -l) -ge $MAX_CONCURRENT_GQ ]; do
        wait -n 2>/dev/null || sleep 0.2
    done
done

pending_jobs=$(jobs -r -p | wc -l)
if [ "$pending_jobs" -gt 0 ]; then
    echo "[GOOGLEQA ARCHIVES] ⏳ Đã điều phối xong toàn bộ file zip. Đang chờ $pending_jobs luồng tải nền còn lại..."
fi

wait
rm -rf "$DONE_DIR_GQ"

if [ -f "$ERR_FLAG_GQ" ]; then
    rm -f "$ERR_FLAG_GQ"
    echo "LỖI: Upload gói lưu trữ sang GOOGLEQA có lỗi!" >&2
    exit 1
fi

echo "SYNC_GQ_ARCHIVES_COMPLETE"
'"""

        def stream_cb(chunk: str):
            self.log(chunk, "STREAM")

        code, out = self.ssh.run_command_stream(sync_script, output_callback=stream_cb, check_abort=self.is_aborted)
        if code != 0 or "SYNC_GQ_ARCHIVES_COMPLETE" not in out:
            return False, f"Lỗi khi đồng bộ gói lưu trữ sang GOOGLEQA (code: {code})"

        return True, f"Đã đồng bộ thành công các gói lưu trữ nặng sang GOOGLEQA ({dest_gq})"
