import os
import re
import json
from typing import Dict, List, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal


class ReportOrganizeWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, ssh_mgr, test_root: str):
        super().__init__()
        self.ssh = ssh_mgr
        self.test_root = test_root
        self._abort = False

    def request_abort(self):
        self._abort = True

    def run(self):
        self.log_signal.emit(f"Bắt đầu thu thập & tổ chức báo cáo tại: {self.test_root}", "INFO")
        
        def output_cb(txt):
            self.log_signal.emit(txt, "STREAM")

        exit_code, out = self.ssh.run_report_organize_stream(
            self.test_root,
            output_callback=output_cb,
            check_abort=lambda: self._abort
        )

        if exit_code == 0:
            self.log_signal.emit("Thu thập & tổ chức Report hoàn tất thành công!", "SUCCESS")
            self.finished_signal.emit(True, "Đã sao chép và tái cấu trúc thư mục Report thành công.")
        else:
            self.log_signal.emit(f"Quá trình tổ chức Report kết thúc với mã lỗi: {exit_code}", "ERROR")
            self.finished_signal.emit(False, f"Có lỗi xảy ra trong quá trình tổ chức Report (code {exit_code}).")



REMOTE_SCAN_SCRIPT = r"""
import os, glob, re, json, sys

def extract_modules_info_from_html(content, tot_mods):
    idx = content.find("testsummary")
    raw_modules = []
    if idx != -1:
        end_idx = content.find("</table>", idx)
        table_html = content[idx:end_idx] if end_idx != -1 else content[idx:idx+50000]
        rows = re.findall(r"<tr>(.*?)</tr>", table_html, re.DOTALL)
        for row in rows[1:]:
            m_td = re.search(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            if not m_td:
                continue
            clean_text = re.sub(r"<[^>]+>", "", m_td.group(1))
            clean_text = clean_text.replace("&nbsp;", " ").replace("\xa0", " ").strip()
            parts = clean_text.split()
            if len(parts) >= 2 and any(arch in parts[0].lower() for arch in ["arm", "x86", "mips", "riscv"]):
                raw_modules.append(parts[1])
            elif len(parts) >= 1:
                raw_modules.append(parts[0])

    if not raw_modules:
        for m_mod in re.finditer(r"<td class=[\"']module[\"'][^>]*>(.*?)</td>", content, re.DOTALL):
            clean_text = re.sub(r"<[^>]+>", "", m_mod.group(1))
            clean_text = clean_text.replace("&nbsp;", " ").replace("\xa0", " ").strip()
            parts = clean_text.split()
            if len(parts) >= 2 and any(arch in parts[0].lower() for arch in ["arm", "x86", "mips", "riscv"]):
                raw_modules.append(parts[1])
            elif len(parts) >= 1:
                raw_modules.append(parts[0])

    # Strip [instant] or bracketed parameters to determine unique base module names
    base_names = []
    for m in raw_modules:
        base = re.sub(r"\[.*?\]", "", m).strip()
        if base and base not in base_names:
            base_names.append(base)

    if len(base_names) == 1:
        return "single", base_names[0]
    elif len(base_names) > 1:
        return "multiple", "Multiple"
    else:
        if tot_mods == 1:
            return "single", "Unknown"
        else:
            return "multiple", "Multiple"

def parse_html_session(dir_path):
    html_path = os.path.join(dir_path, "test_result_failures_suite.html")
    if not os.path.exists(html_path):
        return None
    try:
        with open(html_path, "r", errors="ignore") as f:
            content = f.read(60000)
            
        m_pass = re.search(r"Tests Passed</td><td>(\d+)</td>", content)
        m_fail = re.search(r"Tests Failed</td><td>(\d+)</td>", content)
        m_tot = re.search(r"Modules Total</td><td>(\d+)</td>", content)
        m_done = re.search(r"Modules Done</td><td>(\d+)</td>", content)
        
        pass_cnt = int(m_pass.group(1)) if m_pass else 0
        fail_cnt = int(m_fail.group(1)) if m_fail else -1
        tot_mods = int(m_tot.group(1)) if m_tot else 0
        done_mods = int(m_done.group(1)) if m_done else 0
        
        sess_type, mod_name = extract_modules_info_from_html(content, tot_mods)
            
        return {
            "pass": pass_cnt,
            "fail": fail_cnt,
            "total_modules": tot_mods,
            "done_modules": done_mods,
            "module_name": mod_name,
            "is_pass": (fail_cnt == 0 and tot_mods > 0 and done_mods == tot_mods),
            "type": sess_type
        }
    except Exception as e:
        return None



def match_folder_for_module(folders, mod_name, is_multi=False):
    if is_multi:
        for f in folders:
            if "multiple" in f.lower():
                return f
        return None
    
    # Exact match after removing prefix like '01.'
    for f in folders:
        clean = re.sub(r"^\d+\.\s*", "", f).strip()
        if clean.lower() == mod_name.lower():
            return f
            
    # Fallback substring match
    for f in folders:
        if mod_name.lower() in f.lower():
            return f
    return None


def scan_and_analyze(test_root):
    results_dir = os.path.join(test_root, "results")
    logs_dir = os.path.join(test_root, "logs")
    report_dir = os.path.join(test_root, "Report")
    
    if not os.path.exists(results_dir):
        return {"error": f"results directory not found at {results_dir}"}
        
    sessions = []
    if os.path.exists(results_dir):
        for item in sorted(os.listdir(results_dir)):
            dir_path = os.path.join(results_dir, item)
            if not os.path.isdir(dir_path) or item == "latest":
                continue
            parsed = parse_html_session(dir_path)
            if parsed:
                parsed["timestamp"] = item
                parsed["has_zip"] = os.path.exists(os.path.join(results_dir, item + ".zip"))
                parsed["has_log"] = os.path.exists(os.path.join(logs_dir, item))
                sessions.append(parsed)

    # Find latest pass
    latest_pass_map = {}
    for s in sessions:
        if s["is_pass"]:
            k = "__MULTIPLE__" if s["type"] == "multiple" else s["module_name"]
            if k not in latest_pass_map or s["timestamp"] > latest_pass_map[k]["timestamp"]:
                latest_pass_map[k] = s

    # Check Report structure
    single_dir = os.path.join(report_dir, "single")
    root_report_folders = [f for f in os.listdir(report_dir) if os.path.isdir(os.path.join(report_dir, f))] if os.path.exists(report_dir) else []
    single_subfolders = [f for f in os.listdir(single_dir) if os.path.isdir(os.path.join(single_dir, f))] if os.path.exists(single_dir) else []
    
    # Combine folders to search
    all_known_folders = {}
    for f in root_report_folders:
        if f not in ["single", "results", "logs"]:
            all_known_folders[f] = {"loc": "root", "path": os.path.join(report_dir, f)}
    for f in single_subfolders:
        all_known_folders[f] = {"loc": "single", "path": os.path.join(single_dir, f)}

    # Build analysis for each session
    analyzed_sessions = []
    for s in sessions:
        k = "__MULTIPLE__" if s["type"] == "multiple" else s["module_name"]
        is_latest_pass = (s["is_pass"] and latest_pass_map.get(k, {}).get("timestamp") == s["timestamp"])
        
        # Target folder & copy status check
        target_folder = ""
        copy_status = "NOT_COPIED"
        already_copied = False
        has_res = False
        has_log = False
        
        if s["type"] == "multiple":
            # Check for 00. Multiple folder or root results
            m_f = match_folder_for_module(list(all_known_folders.keys()), "Multiple", is_multi=True)
            if m_f:
                target_folder = m_f
                dest_res = os.path.join(all_known_folders[m_f]["path"], "results", s["timestamp"])
                dest_log = os.path.join(all_known_folders[m_f]["path"], "logs", s["timestamp"])
            else:
                target_folder = "Report/results (Root)"
                dest_res = os.path.join(report_dir, "results", s["timestamp"])
                dest_log = os.path.join(report_dir, "logs", s["timestamp"])
            has_res = os.path.exists(dest_res)
            has_log = os.path.exists(dest_log)
        else:
            s_f = match_folder_for_module(list(all_known_folders.keys()), s["module_name"], is_multi=False)
            if s_f:
                loc = all_known_folders[s_f]["loc"]
                target_folder = f"{loc}/{s_f}"
                dest_res = os.path.join(all_known_folders[s_f]["path"], "results", s["timestamp"])
                dest_log = os.path.join(all_known_folders[s_f]["path"], "logs", s["timestamp"])
                has_res = os.path.exists(dest_res)
                has_log = os.path.exists(dest_log)
            else:
                target_folder = "[Chưa có folder mẫu]"

        # Evaluate copy completeness (Must have BOTH result AND log)
        if has_res and has_log:
            copy_status = "COPIED_FULL"
            already_copied = True
        elif has_res and not has_log:
            copy_status = "MISSING_LOG"
            already_copied = False
        elif not has_res and has_log:
            copy_status = "MISSING_RES"
            already_copied = False
        else:
            copy_status = "NOT_COPIED"
            already_copied = False

        status_tag = "FAIL"
        if s["is_pass"]:
            status_tag = "LATEST_PASS" if is_latest_pass else "OUTDATED_PASS"

        analyzed_sessions.append({
            "timestamp": s["timestamp"],
            "type": s["type"],
            "module_name": s["module_name"],
            "pass": s["pass"],
            "fail": s["fail"],
            "total_modules": s["total_modules"],
            "done_modules": s["done_modules"],
            "is_pass": s["is_pass"],
            "is_latest_pass": is_latest_pass,
            "status_tag": status_tag,
            "target_folder": target_folder,
            "already_copied": already_copied,
            "copy_status": copy_status
        })

    return {
        "test_root": test_root,
        "total_sessions": len(sessions),
        "passed_sessions_count": len([s for s in sessions if s["is_pass"]]),
        "latest_pass_count": len(latest_pass_map),
        "sessions": analyzed_sessions,
        "latest_pass_keys": list(latest_pass_map.keys())
    }

if __name__ == "__main__":
    t_root = sys.argv[1] if len(sys.argv) > 1 else ""
    res = scan_and_analyze(t_root)
    print(json.dumps(res))
"""


REMOTE_ORGANIZE_SCRIPT = r"""
import os, glob, re, shutil, json, sys

def log(msg):
    print(msg, flush=True)

def extract_modules_info_from_html(content, tot_mods):
    idx = content.find("testsummary")
    raw_modules = []
    if idx != -1:
        end_idx = content.find("</table>", idx)
        table_html = content[idx:end_idx] if end_idx != -1 else content[idx:idx+50000]
        rows = re.findall(r"<tr>(.*?)</tr>", table_html, re.DOTALL)
        for row in rows[1:]:
            m_td = re.search(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            if not m_td:
                continue
            clean_text = re.sub(r"<[^>]+>", "", m_td.group(1))
            clean_text = clean_text.replace("&nbsp;", " ").replace("\xa0", " ").strip()
            parts = clean_text.split()
            if len(parts) >= 2 and any(arch in parts[0].lower() for arch in ["arm", "x86", "mips", "riscv"]):
                raw_modules.append(parts[1])
            elif len(parts) >= 1:
                raw_modules.append(parts[0])

    if not raw_modules:
        for m_mod in re.finditer(r"<td class=[\"']module[\"'][^>]*>(.*?)</td>", content, re.DOTALL):
            clean_text = re.sub(r"<[^>]+>", "", m_mod.group(1))
            clean_text = clean_text.replace("&nbsp;", " ").replace("\xa0", " ").strip()
            parts = clean_text.split()
            if len(parts) >= 2 and any(arch in parts[0].lower() for arch in ["arm", "x86", "mips", "riscv"]):
                raw_modules.append(parts[1])
            elif len(parts) >= 1:
                raw_modules.append(parts[0])

    # Strip [instant] or bracketed parameters to determine unique base module names
    base_names = []
    for m in raw_modules:
        base = re.sub(r"\[.*?\]", "", m).strip()
        if base and base not in base_names:
            base_names.append(base)

    if len(base_names) == 1:
        return "single", base_names[0]
    elif len(base_names) > 1:
        return "multiple", "Multiple"
    else:
        if tot_mods == 1:
            return "single", "Unknown"
        else:
            return "multiple", "Multiple"

def parse_html_session(dir_path):
    html_path = os.path.join(dir_path, "test_result_failures_suite.html")
    if not os.path.exists(html_path):
        return None
    try:
        with open(html_path, "r", errors="ignore") as f:
            content = f.read(60000)
            
        m_pass = re.search(r"Tests Passed</td><td>(\d+)</td>", content)
        m_fail = re.search(r"Tests Failed</td><td>(\d+)</td>", content)
        m_tot = re.search(r"Modules Total</td><td>(\d+)</td>", content)
        m_done = re.search(r"Modules Done</td><td>(\d+)</td>", content)
        
        pass_cnt = int(m_pass.group(1)) if m_pass else 0
        fail_cnt = int(m_fail.group(1)) if m_fail else -1
        tot_mods = int(m_tot.group(1)) if m_tot else 0
        done_mods = int(m_done.group(1)) if m_done else 0
        
        sess_type, mod_name = extract_modules_info_from_html(content, tot_mods)
            
        return {
            "pass": pass_cnt,
            "fail": fail_cnt,
            "total_modules": tot_mods,
            "done_modules": done_mods,
            "module_name": mod_name,
            "is_pass": (fail_cnt == 0 and tot_mods > 0 and done_mods == tot_mods),
            "type": sess_type
        }
    except Exception:
        return None


def folder_has_pass_result(folder_path):
    res_dir = os.path.join(folder_path, "results")
    logs_dir = os.path.join(folder_path, "logs")
    if not os.path.exists(res_dir):
        return False
    for item in os.listdir(res_dir):
        sub_res = os.path.join(res_dir, item)
        if os.path.isdir(sub_res):
            parsed = parse_html_session(sub_res)
            if parsed and parsed["is_pass"]:
                # Đảm bảo cả log cũng phải tồn tại cho session pass này
                sub_log = os.path.join(logs_dir, item)
                if os.path.exists(sub_log) and os.path.isdir(sub_log):
                    return True
    return False

def match_folder_for_module(folders, mod_name, is_multi=False):
    if is_multi:
        for f in folders:
            if "multiple" in f.lower():
                return f
        return None
    for f in folders:
        clean = re.sub(r"^\d+\.\s*", "", f).strip()
        if clean.lower() == mod_name.lower():
            return f
    for f in folders:
        if mod_name.lower() in f.lower():
            return f
    return None

def execute_organize(test_root):
    results_dir = os.path.join(test_root, "results")
    logs_dir = os.path.join(test_root, "logs")
    report_dir = os.path.join(test_root, "Report")
    
    log(f"=== BẮT ĐẦU THU THẬP & TỔ CHỨC REPORT TẠI: {report_dir} ===")
    
    if not os.path.exists(results_dir):
        log(f"[ERROR] Không tìm thấy thư mục results tại: {results_dir}")
        return False
    if not os.path.exists(report_dir):
        log(f"[ERROR] Không tìm thấy thư mục Report tại: {report_dir}")
        return False

    # 1. Scan results and find latest pass per module
    log("[BƯỚC 1] Quét các session kết quả trong results/...")
    sessions = []
    for item in sorted(os.listdir(results_dir)):
        p = os.path.join(results_dir, item)
        if not os.path.isdir(p) or item == "latest":
            continue
        parsed = parse_html_session(p)
        if parsed:
            parsed["timestamp"] = item
            sessions.append(parsed)

    latest_pass_map = {}
    for s in sessions:
        if s["is_pass"]:
            k = "__MULTIPLE__" if s["type"] == "multiple" else s["module_name"]
            if k not in latest_pass_map or s["timestamp"] > latest_pass_map[k]["timestamp"]:
                latest_pass_map[k] = s

    log(f"-> Tìm thấy tổng cộng {len(sessions)} sessions. Trong đó có {len(latest_pass_map)} module đạt chuẩn Pass (Fail=0).")
    for k, v in latest_pass_map.items():
        log(f"   [PASS] {k} -> Session: {v['timestamp']} (Pass: {v['pass']})")

    # 2. Map existing Report folders
    single_dir = os.path.join(report_dir, "single")
    os.makedirs(single_dir, exist_ok=True)

    root_report_folders = [f for f in os.listdir(report_dir) if os.path.isdir(os.path.join(report_dir, f))]
    single_subfolders = [f for f in os.listdir(single_dir) if os.path.isdir(os.path.join(single_dir, f))]
    
    all_known_folders = {}
    for f in root_report_folders:
        if f not in ["single", "results", "logs"]:
            all_known_folders[f] = {"loc": "root", "path": os.path.join(report_dir, f)}
    for f in single_subfolders:
        all_known_folders[f] = {"loc": "single", "path": os.path.join(single_dir, f)}

    # 3. Copy files
    log("\n[BƯỚC 2] Tiến hành kiểm tra và sao chép log & result (bổ sung nếu thiếu)...")
    copied_count = 0
    skipped_count = 0

    # Multiple copy
    if "__MULTIPLE__" in latest_pass_map:
        m_s = latest_pass_map["__MULTIPLE__"]
        ts = m_s["timestamp"]
        m_f = match_folder_for_module(list(all_known_folders.keys()), "Multiple", is_multi=True)
        
        if m_f:
            dest_res_dir = os.path.join(all_known_folders[m_f]["path"], "results")
            dest_log_dir = os.path.join(all_known_folders[m_f]["path"], "logs")
        else:
            dest_res_dir = os.path.join(report_dir, "results")
            dest_log_dir = os.path.join(report_dir, "logs")

        os.makedirs(dest_res_dir, exist_ok=True)
        os.makedirs(dest_log_dir, exist_ok=True)

        # Copy result folder
        src_res = os.path.join(results_dir, ts)
        dst_res = os.path.join(dest_res_dir, ts)
        if not os.path.exists(dst_res):
            log(f"-> [COPY RESULT] Multiple: {ts} -> {dest_res_dir}")
            shutil.copytree(src_res, dst_res)
            copied_count += 1
        else:
            log(f"-> [SKIP RESULT] Multiple result đã có sẵn: {ts}")
            skipped_count += 1

        # Copy result zip
        src_zip = os.path.join(results_dir, ts + ".zip")
        dst_zip = os.path.join(dest_res_dir, ts + ".zip")
        if os.path.exists(src_zip) and not os.path.exists(dst_zip):
            shutil.copy2(src_zip, dst_zip)

        # Copy log folder - CHECK VÀ COPY BỔ SUNG NẾU THIẾU
        src_log = os.path.join(logs_dir, ts)
        dst_log = os.path.join(dest_log_dir, ts)
        if os.path.exists(src_log):
            if not os.path.exists(dst_log):
                log(f"-> [COPY BỔ SUNG LOG] Multiple log: {ts} -> {dest_log_dir}")
                shutil.copytree(src_log, dst_log)
                copied_count += 1
            else:
                log(f"-> [SKIP LOG] Multiple log đã có sẵn: {ts}")
                skipped_count += 1
        else:
            log(f"-> [CẢNH BÁO] Không tìm thấy source log của Multiple tại {src_log}!")

    # Single modules copy
    for mod_key, s_info in latest_pass_map.items():
        if mod_key == "__MULTIPLE__":
            continue
        ts = s_info["timestamp"]
        s_f = match_folder_for_module(list(all_known_folders.keys()), mod_key, is_multi=False)
        if not s_f:
            log(f"[CẢNH BÁO] Không tìm thấy folder mẫu nào cho module: {mod_key} trong Report!")
            continue

        target_base = all_known_folders[s_f]["path"]
        dest_res_dir = os.path.join(target_base, "results")
        dest_log_dir = os.path.join(target_base, "logs")
        os.makedirs(dest_res_dir, exist_ok=True)
        os.makedirs(dest_log_dir, exist_ok=True)

        # Copy result folder
        src_res = os.path.join(results_dir, ts)
        dst_res = os.path.join(dest_res_dir, ts)
        if not os.path.exists(dst_res):
            log(f"-> [COPY RESULT] Module {mod_key}: {ts} -> {s_f}/results/")
            shutil.copytree(src_res, dst_res)
            copied_count += 1
        else:
            log(f"-> [SKIP RESULT] Module {mod_key} result đã có sẵn: {ts}")
            skipped_count += 1

        # Copy zip
        src_zip = os.path.join(results_dir, ts + ".zip")
        dst_zip = os.path.join(dest_res_dir, ts + ".zip")
        if os.path.exists(src_zip) and not os.path.exists(dst_zip):
            shutil.copy2(src_zip, dst_zip)

        # Copy log folder - CHECK VÀ COPY BỔ SUNG NẾU THIẾU
        src_log = os.path.join(logs_dir, ts)
        dst_log = os.path.join(dest_log_dir, ts)
        if os.path.exists(src_log):
            if not os.path.exists(dst_log):
                log(f"-> [COPY BỔ SUNG LOG] Module {mod_key} log: {ts} -> {s_f}/logs/")
                shutil.copytree(src_log, dst_log)
                copied_count += 1
            else:
                log(f"-> [SKIP LOG] Module {mod_key} log đã có sẵn: {ts}")
                skipped_count += 1
        else:
            log(f"-> [CẢNH BÁO] Không tìm thấy source log của Module {mod_key} tại {src_log}!")

    # 4. Reorganize Report structure
    log("\n[BƯỚC 3] Tái cấu trúc thư mục Report theo trạng thái Pass / Chưa Pass...")

    # Refresh root folders
    current_root_folders = [f for f in os.listdir(report_dir) if os.path.isdir(os.path.join(report_dir, f))]
    
    # Process Multiple folder
    m_folder = match_folder_for_module(current_root_folders, "Multiple", is_multi=True)
    if m_folder:
        m_path = os.path.join(report_dir, m_folder)
        if folder_has_pass_result(m_path) or ("__MULTIPLE__" in latest_pass_map):
            log(f"-> Multiple ĐÃ PASS: Di chuyển results/ và logs/ từ '{m_folder}' ra ngoài Report/")
            # Move results
            inner_res = os.path.join(m_path, "results")
            outer_res = os.path.join(report_dir, "results")
            os.makedirs(outer_res, exist_ok=True)
            if os.path.exists(inner_res):
                for item in os.listdir(inner_res):
                    s_item = os.path.join(inner_res, item)
                    d_item = os.path.join(outer_res, item)
                    if not os.path.exists(d_item):
                        shutil.move(s_item, d_item)

            # Move logs
            inner_log = os.path.join(m_path, "logs")
            outer_log = os.path.join(report_dir, "logs")
            os.makedirs(outer_log, exist_ok=True)
            if os.path.exists(inner_log):
                for item in os.listdir(inner_log):
                    s_item = os.path.join(inner_log, item)
                    d_item = os.path.join(outer_log, item)
                    if not os.path.exists(d_item):
                        shutil.move(s_item, d_item)

            # Remove empty folder
            try:
                shutil.rmtree(m_path)
                log(f"-> Đã dọn dẹp thư mục rỗng '{m_folder}' thành công.")
            except Exception as e:
                log(f"-> Lưu ý: Không thể xóa '{m_folder}': {e}")
        else:
            log(f"-> Multiple CHƯA PASS: Giữ nguyên thư mục '{m_folder}' ngang cấp với single/")

    # Process single folders currently at root
    current_root_folders = [f for f in os.listdir(report_dir) if os.path.isdir(os.path.join(report_dir, f))]
    for folder in current_root_folders:
        if folder in ["single", "results", "logs"]:
            continue
        if "multiple" in folder.lower():
            continue
        
        folder_path = os.path.join(report_dir, folder)
        has_passed = folder_has_pass_result(folder_path)
        
        if has_passed:
            dest_in_single = os.path.join(single_dir, folder)
            log(f"-> Module '{folder}' ĐÃ PASS: Di chuyển vào Report/single/{folder}")
            if os.path.exists(dest_in_single):
                # Merge into existing single folder
                for sub in ["results", "logs"]:
                    src_sub = os.path.join(folder_path, sub)
                    dst_sub = os.path.join(dest_in_single, sub)
                    os.makedirs(dst_sub, exist_ok=True)
                    if os.path.exists(src_sub):
                        for f_item in os.listdir(src_sub):
                            src_f = os.path.join(src_sub, f_item)
                            dst_f = os.path.join(dst_sub, f_item)
                            if not os.path.exists(dst_f):
                                shutil.move(src_f, dst_f)
                shutil.rmtree(folder_path, ignore_errors=True)
            else:
                shutil.move(folder_path, dest_in_single)
        else:
            log(f"-> Module '{folder}' CHƯA PASS: Giữ nguyên vị trí ngoài root (ngang cấp single/)")

    log("\n🎉 HOÀN TẤT THU THẬP VÀ TỔ CHỨC BÁO CÁO REPORT THÀNH CÔNG! 🎉")
    return True

if __name__ == "__main__":
    t_root = sys.argv[1] if len(sys.argv) > 1 else ""
    execute_organize(t_root)
"""
