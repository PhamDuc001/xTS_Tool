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
from collections import defaultdict

def sanitize_name(name):
    return re.sub(r'[\s\[\]#:$]+', '_', name).strip('_')

def find_effective_report_dir(test_root):
    r_dir = os.path.join(test_root, "Report")
    if not os.path.exists(r_dir):
        return r_dir
    for item in os.listdir(r_dir):
        p = os.path.join(r_dir, item)
        if os.path.isdir(p) and re.match(r"^\d+\.", item):
            if os.path.exists(os.path.join(p, "single")) or os.path.exists(os.path.join(p, "results")):
                return p
    return r_dir

def parse_session(dir_path):
    xml_path = os.path.join(dir_path, "test_result.xml")
    html_path = os.path.join(dir_path, "test_result_failures_suite.html")
    
    cmd_args = ""
    mod_name = ""
    test_method = ""
    total_tests = 0
    pass_cnt = 0
    fail_cnt = -1
    tot_mods = 0
    done_mods = 0
    failed_tests = []
    
    if os.path.exists(xml_path):
        try:
            with open(xml_path, "r", errors="ignore") as f:
                header = f.read(35000)
            m_cmd = re.search(r'command_line_args="([^"]*)"', header)
            if m_cmd:
                cmd_args = m_cmd.group(1)
            m_sum = re.search(r'<Summary\s+pass="(\d+)"\s+failed="(\d+)"[^>]*modules_done="(\d+)"\s+modules_total="(\d+)"', header)
            if m_sum:
                pass_cnt = int(m_sum.group(1))
                fail_cnt = int(m_sum.group(2))
                done_mods = int(m_sum.group(3))
                tot_mods = int(m_sum.group(4))
            m_mod = re.search(r'<Module\s+name="([^"]+)"[^>]*total_tests="(\d+)"', header)
            if m_mod:
                mod_name = m_mod.group(1)
                total_tests = int(m_mod.group(2))
            
            for tm in re.finditer(r'<Test\s+result="([^"]*)"\s+name="([^"]+)"', header):
                res_type, t_name = tm.group(1), tm.group(2)
                if not test_method:
                    test_method = t_name
                if res_type == "fail":
                    failed_tests.append(t_name)
        except Exception:
            pass

    if not mod_name and os.path.exists(html_path):
        try:
            with open(html_path, "r", errors="ignore") as f:
                content = f.read(60000)
            m_pass = re.search(r"Tests Passed</td><td>(\d+)</td>", content)
            m_fail = re.search(r"Tests Failed</td><td>(\d+)</td>", content)
            m_tot = re.search(r"Modules Total</td><td>(\d+)</td>", content)
            m_done = re.search(r"Modules Done</td><td>(\d+)</td>", content)
            if m_pass: pass_cnt = int(m_pass.group(1))
            if m_fail: fail_cnt = int(m_fail.group(1))
            if m_tot: tot_mods = int(m_tot.group(1))
            if m_done: done_mods = int(m_done.group(1))
            
            idx = content.find("testsummary")
            if idx != -1:
                end_idx = content.find("</table>", idx)
                t_html = content[idx:end_idx] if end_idx != -1 else content[idx:idx+50000]
                rows = re.findall(r"<tr>(.*?)</tr>", t_html, re.DOTALL)
                for row in rows[1:]:
                    m_td = re.search(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
                    if m_td:
                        clean = re.sub(r"<[^>]+>", "", m_td.group(1)).replace("&nbsp;", " ").strip()
                        parts = clean.split()
                        if len(parts) >= 2 and any(a in parts[0].lower() for a in ["arm", "x86", "mips", "riscv"]):
                            mod_name = parts[1]
                        elif len(parts) >= 1:
                            mod_name = parts[0]
                        break
        except Exception:
            pass

    is_testcase = False
    if (" -t " in cmd_args or "#" in cmd_args) and test_method:
        is_testcase = True
    elif tot_mods == 1 and total_tests == 1 and test_method:
        if "#" in cmd_args or " -t " in cmd_args or "filter" in cmd_args:
            is_testcase = True

    if is_testcase:
        sess_type = "testcase"
    elif tot_mods > 1 or "Multiple" in cmd_args or mod_name.lower() == "multiple":
        sess_type = "multiple"
        mod_name = "Multiple"
    else:
        sess_type = "single"

    is_pass = (fail_cnt == 0 and tot_mods > 0 and done_mods == tot_mods and pass_cnt > 0)

    return {
        "pass": pass_cnt,
        "fail": fail_cnt,
        "total_modules": tot_mods,
        "done_modules": done_mods,
        "module_name": mod_name or "Unknown",
        "testcase_name": test_method if is_testcase else "",
        "failed_tests": failed_tests,
        "is_pass": is_pass,
        "type": sess_type,
        "cmd": cmd_args
    }

def select_history_sessions(sessions):
    if len(sessions) < 5:
        return sessions
    return [sessions[0], sessions[1], sessions[-2], sessions[-1]]

def get_max_existing_id(report_dir):
    single_dir = os.path.join(report_dir, "single")
    folders = []
    if os.path.exists(report_dir):
        folders.extend(os.listdir(report_dir))
    if os.path.exists(single_dir):
        folders.extend(os.listdir(single_dir))
    max_id = 0
    for f in folders:
        m = re.match(r"^(\d+)\.", f)
        if m:
            val = int(m.group(1))
            if val > max_id:
                max_id = val
    return max_id

def match_module_folder(all_known_folders, mod_name):
    for f in all_known_folders:
        clean = re.sub(r"^\d+\.\s*", "", f).strip()
        if clean.lower() == mod_name.lower():
            return f
    mod_base = re.sub(r'(Device)?TestCases$', '', mod_name, flags=re.I).lower()
    for f in all_known_folders:
        clean = re.sub(r"^\d+\.\s*", "", f).strip()
        clean_base = re.sub(r'((Device)?TestCases)?(_multi)?$', '', clean, flags=re.I).lower()
        if clean_base == mod_base:
            return f
    for f in all_known_folders:
        if mod_name.lower() in f.lower():
            return f
    return None

def match_testcase_folder(all_known_folders, mod_name, tc_name):
    mod_base = re.sub(r'(Device)?TestCases$', '', mod_name, flags=re.I).lower()
    tc_clean = tc_name.lower()
    for f in all_known_folders:
        f_lower = f.lower()
        if mod_base in f_lower:
            if tc_clean in f_lower:
                return f
            tc_stem = re.sub(r'ifsupported|test', '', tc_clean)
            if tc_stem and tc_stem in f_lower:
                return f
            if any(part in f_lower for part in tc_clean.split('_') if len(part) > 6):
                return f
    return None

def scan_and_analyze(test_root):
    results_dir = os.path.join(test_root, "results")
    logs_dir = os.path.join(test_root, "logs")
    report_dir = find_effective_report_dir(test_root)
    single_dir = os.path.join(report_dir, "single")
    
    if not os.path.exists(results_dir):
        return {"error": f"results directory not found at {results_dir}"}
        
    sessions = []
    if os.path.exists(results_dir):
        for item in sorted(os.listdir(results_dir)):
            dir_path = os.path.join(results_dir, item)
            if not os.path.isdir(dir_path) or item == "latest":
                continue
            parsed = parse_session(dir_path)
            if parsed:
                parsed["timestamp"] = item
                parsed["has_zip"] = os.path.exists(os.path.join(results_dir, item + ".zip"))
                parsed["has_log"] = os.path.exists(os.path.join(logs_dir, item))
                sessions.append(parsed)

    multi_sessions = [s for s in sessions if s["type"] == "multiple"]
    single_sessions = defaultdict(list)
    tc_sessions = defaultdict(list)

    failed_in_multiple = set()
    for s in multi_sessions:
        xml_p = os.path.join(results_dir, s["timestamp"], "test_result.xml")
        if os.path.exists(xml_p):
            try:
                with open(xml_p, "r", errors="ignore") as f:
                    for line in f:
                        if "<Module " in line:
                            m_m = re.search(r'name="([^"]+)"[^>]*done="([^"]+)"', line)
                            if m_m and m_m.group(2).lower() != "true":
                                failed_in_multiple.add(m_m.group(1))
                            m_f = re.search(r'name="([^"]+)"[^>]*failed="([1-9]\d*)"', line)
                            if m_f:
                                failed_in_multiple.add(m_f.group(1))
            except Exception:
                pass

    for s in sessions:
        if s["type"] == "single":
            single_sessions[s["module_name"]].append(s)
        elif s["type"] == "testcase":
            tc_sessions[(s["module_name"], s["testcase_name"])].append(s)

    all_known_folders = {}
    if os.path.exists(report_dir):
        for f in os.listdir(report_dir):
            p = os.path.join(report_dir, f)
            if os.path.isdir(p) and f not in ["single", "results", "logs"]:
                all_known_folders[f] = {"loc": "root", "path": p}
    if os.path.exists(single_dir):
        for f in os.listdir(single_dir):
            p = os.path.join(single_dir, f)
            if os.path.isdir(p):
                all_known_folders[f] = {"loc": "single", "path": p}

    next_id = get_max_existing_id(report_dir)

    single_target_map = {}
    for mod_name, s_list in single_sessions.items():
        matched = match_module_folder(all_known_folders, mod_name)
        if matched:
            single_target_map[mod_name] = f"single/{matched}" if all_known_folders[matched]["loc"] == "single" else matched
        else:
            next_id += 1
            suffix = "_multi" if mod_name in failed_in_multiple else ""
            new_folder = f"{next_id:02d}.{mod_name}{suffix}"
            single_target_map[mod_name] = f"single/{new_folder}"
            all_known_folders[new_folder] = {"loc": "single", "path": os.path.join(single_dir, new_folder)}

    tc_target_map = {}
    for (mod_name, tc_name), s_list in tc_sessions.items():
        matched = match_testcase_folder(all_known_folders, mod_name, tc_name)
        if matched:
            tc_target_map[(mod_name, tc_name)] = f"single/{matched}" if all_known_folders[matched]["loc"] == "single" else matched
        else:
            next_id += 1
            new_folder = f"{next_id:02d}.{mod_name}_{sanitize_name(tc_name)}"
            tc_target_map[(mod_name, tc_name)] = f"single/{new_folder}"
            all_known_folders[new_folder] = {"loc": "single", "path": os.path.join(single_dir, new_folder)}

    pruned_selection = set()
    for s in select_history_sessions(multi_sessions):
        pruned_selection.add(s["timestamp"])
    for mod_name, s_list in single_sessions.items():
        for s in select_history_sessions(s_list):
            pruned_selection.add(s["timestamp"])
    for (mod_name, tc_name), s_list in tc_sessions.items():
        passes = [s for s in s_list if s["is_pass"]]
        if passes:
            pruned_selection.add(passes[-1]["timestamp"])

    latest_pass_map = {}
    for s in sessions:
        if s["is_pass"]:
            if s["type"] == "multiple":
                k = "__MULTIPLE__"
            elif s["type"] == "testcase":
                k = f"TESTCASE:{s['module_name']}#{s['testcase_name']}"
            else:
                k = s["module_name"]
            if k not in latest_pass_map or s["timestamp"] > latest_pass_map[k]["timestamp"]:
                latest_pass_map[k] = s

    analyzed_sessions = []
    for s in sessions:
        ts = s["timestamp"]
        stype = s["type"]
        is_selected = ts in pruned_selection

        if stype == "multiple":
            k = "__MULTIPLE__"
            target_folder = "Report/results (Root)"
            dest_res = os.path.join(report_dir, "results", ts)
            dest_log = os.path.join(report_dir, "logs", ts)
        elif stype == "testcase":
            k = f"TESTCASE:{s['module_name']}#{s['testcase_name']}"
            target_folder = tc_target_map.get((s["module_name"], s["testcase_name"]), "[Chưa xác định]")
            f_clean = target_folder.replace("single/", "")
            dest_res = os.path.join(single_dir, f_clean, "results", ts)
            dest_log = os.path.join(single_dir, f_clean, "logs", ts)
        else:
            k = s["module_name"]
            target_folder = single_target_map.get(s["module_name"], "[Chưa xác định]")
            f_clean = target_folder.replace("single/", "")
            dest_res = os.path.join(single_dir, f_clean, "results", ts)
            dest_log = os.path.join(single_dir, f_clean, "logs", ts)

        has_res = os.path.exists(dest_res)
        has_log = os.path.exists(dest_log)
        already_copied = (has_res and has_log)

        if has_res and has_log:
            copy_status = "COPIED_FULL"
        elif has_res and not has_log:
            copy_status = "MISSING_LOG"
        elif not has_res and has_log:
            copy_status = "MISSING_RES"
        else:
            if is_selected:
                copy_status = "WILL_COPY"
            elif not s["is_pass"] and stype == "testcase":
                copy_status = "NOT_COPIED"
            else:
                copy_status = "PRUNED_SKIP"

        is_latest_pass = (s["is_pass"] and latest_pass_map.get(k, {}).get("timestamp") == ts)
        if stype == "testcase":
            status_tag = "TESTCASE_PASS" if s["is_pass"] else "FAIL"
        else:
            if s["is_pass"]:
                status_tag = "LATEST_PASS" if is_latest_pass else "OUTDATED_PASS"
            else:
                status_tag = "FAIL"

        analyzed_sessions.append({
            "timestamp": ts,
            "type": stype,
            "module_name": s["module_name"],
            "testcase_name": s.get("testcase_name", ""),
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
        "effective_report_dir": report_dir,
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
from collections import defaultdict

def log(msg):
    print(msg, flush=True)

def sanitize_name(name):
    return re.sub(r'[\s\[\]#:$]+', '_', name).strip('_')

def find_effective_report_dir(test_root):
    r_dir = os.path.join(test_root, "Report")
    if not os.path.exists(r_dir):
        return r_dir
    for item in os.listdir(r_dir):
        p = os.path.join(r_dir, item)
        if os.path.isdir(p) and re.match(r"^\d+\.", item):
            if os.path.exists(os.path.join(p, "single")) or os.path.exists(os.path.join(p, "results")):
                return p
    return r_dir

def parse_session(dir_path):
    xml_path = os.path.join(dir_path, "test_result.xml")
    html_path = os.path.join(dir_path, "test_result_failures_suite.html")
    
    cmd_args = ""
    mod_name = ""
    test_method = ""
    total_tests = 0
    pass_cnt = 0
    fail_cnt = -1
    tot_mods = 0
    done_mods = 0
    
    if os.path.exists(xml_path):
        try:
            with open(xml_path, "r", errors="ignore") as f:
                header = f.read(35000)
            m_cmd = re.search(r'command_line_args="([^"]*)"', header)
            if m_cmd:
                cmd_args = m_cmd.group(1)
            m_sum = re.search(r'<Summary\s+pass="(\d+)"\s+failed="(\d+)"[^>]*modules_done="(\d+)"\s+modules_total="(\d+)"', header)
            if m_sum:
                pass_cnt = int(m_sum.group(1))
                fail_cnt = int(m_sum.group(2))
                done_mods = int(m_sum.group(3))
                tot_mods = int(m_sum.group(4))
            m_mod = re.search(r'<Module\s+name="([^"]+)"[^>]*total_tests="(\d+)"', header)
            if m_mod:
                mod_name = m_mod.group(1)
                total_tests = int(m_mod.group(2))
            m_test = re.search(r'<Test\s+result="[^"]*"\s+name="([^"]+)"', header)
            if m_test:
                test_method = m_test.group(1)
        except Exception:
            pass

    if not mod_name and os.path.exists(html_path):
        try:
            with open(html_path, "r", errors="ignore") as f:
                content = f.read(60000)
            m_pass = re.search(r"Tests Passed</td><td>(\d+)</td>", content)
            m_fail = re.search(r"Tests Failed</td><td>(\d+)</td>", content)
            m_tot = re.search(r"Modules Total</td><td>(\d+)</td>", content)
            m_done = re.search(r"Modules Done</td><td>(\d+)</td>", content)
            if m_pass: pass_cnt = int(m_pass.group(1))
            if m_fail: fail_cnt = int(m_fail.group(1))
            if m_tot: tot_mods = int(m_tot.group(1))
            if m_done: done_mods = int(m_done.group(1))
            
            idx = content.find("testsummary")
            if idx != -1:
                end_idx = content.find("</table>", idx)
                t_html = content[idx:end_idx] if end_idx != -1 else content[idx:idx+50000]
                rows = re.findall(r"<tr>(.*?)</tr>", t_html, re.DOTALL)
                for row in rows[1:]:
                    m_td = re.search(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
                    if m_td:
                        clean = re.sub(r"<[^>]+>", "", m_td.group(1)).replace("&nbsp;", " ").strip()
                        parts = clean.split()
                        if len(parts) >= 2 and any(a in parts[0].lower() for a in ["arm", "x86", "mips", "riscv"]):
                            mod_name = parts[1]
                        elif len(parts) >= 1:
                            mod_name = parts[0]
                        break
        except Exception:
            pass

    is_testcase = False
    if (" -t " in cmd_args or "#" in cmd_args) and test_method:
        is_testcase = True
    elif tot_mods == 1 and total_tests == 1 and test_method:
        if "#" in cmd_args or " -t " in cmd_args or "filter" in cmd_args:
            is_testcase = True

    if is_testcase:
        sess_type = "testcase"
    elif tot_mods > 1 or "Multiple" in cmd_args or mod_name.lower() == "multiple":
        sess_type = "multiple"
        mod_name = "Multiple"
    else:
        sess_type = "single"

    is_pass = (fail_cnt == 0 and tot_mods > 0 and done_mods == tot_mods and pass_cnt > 0)

    return {
        "pass": pass_cnt,
        "fail": fail_cnt,
        "total_modules": tot_mods,
        "done_modules": done_mods,
        "module_name": mod_name or "Unknown",
        "testcase_name": test_method if is_testcase else "",
        "is_pass": is_pass,
        "type": sess_type,
        "cmd": cmd_args
    }

def select_history_sessions(sessions):
    if len(sessions) < 5:
        return sessions
    return [sessions[0], sessions[1], sessions[-2], sessions[-1]]

def get_max_existing_id(report_dir):
    single_dir = os.path.join(report_dir, "single")
    folders = []
    if os.path.exists(report_dir):
        folders.extend(os.listdir(report_dir))
    if os.path.exists(single_dir):
        folders.extend(os.listdir(single_dir))
    max_id = 0
    for f in folders:
        m = re.match(r"^(\d+)\.", f)
        if m:
            val = int(m.group(1))
            if val > max_id:
                max_id = val
    return max_id

def match_module_folder(all_known_folders, mod_name):
    for f in all_known_folders:
        clean = re.sub(r"^\d+\.\s*", "", f).strip()
        if clean.lower() == mod_name.lower():
            return f
    mod_base = re.sub(r'(Device)?TestCases$', '', mod_name, flags=re.I).lower()
    for f in all_known_folders:
        clean = re.sub(r"^\d+\.\s*", "", f).strip()
        clean_base = re.sub(r'((Device)?TestCases)?(_multi)?$', '', clean, flags=re.I).lower()
        if clean_base == mod_base:
            return f
    for f in all_known_folders:
        if mod_name.lower() in f.lower():
            return f
    return None

def match_testcase_folder(all_known_folders, mod_name, tc_name):
    mod_base = re.sub(r'(Device)?TestCases$', '', mod_name, flags=re.I).lower()
    tc_clean = tc_name.lower()
    for f in all_known_folders:
        f_lower = f.lower()
        if mod_base in f_lower:
            if tc_clean in f_lower:
                return f
            tc_stem = re.sub(r'ifsupported|test', '', tc_clean)
            if tc_stem and tc_stem in f_lower:
                return f
            if any(part in f_lower for part in tc_clean.split('_') if len(part) > 6):
                return f
    return None

def copy_session(src_res_dir, src_logs_dir, dst_res_dir, dst_logs_dir, ts):
    copied = False
    os.makedirs(dst_res_dir, exist_ok=True)
    os.makedirs(dst_logs_dir, exist_ok=True)

    s_rf = os.path.join(src_res_dir, ts)
    d_rf = os.path.join(dst_res_dir, ts)
    if os.path.exists(s_rf) and not os.path.exists(d_rf):
        log(f"   -> [COPY RESULT] {ts} -> {dst_res_dir}")
        shutil.copytree(s_rf, d_rf)
        copied = True
    elif os.path.exists(d_rf):
        log(f"   -> [SKIP RESULT] Đã có: {ts}")

    s_zip = os.path.join(src_res_dir, ts + ".zip")
    d_zip = os.path.join(dst_res_dir, ts + ".zip")
    if os.path.exists(s_zip) and not os.path.exists(d_zip):
        shutil.copy2(s_zip, d_zip)

    s_lf = os.path.join(src_logs_dir, ts)
    d_lf = os.path.join(dst_logs_dir, ts)
    if os.path.exists(s_lf) and not os.path.exists(d_lf):
        log(f"   -> [COPY LOG] {ts} -> {dst_logs_dir}")
        shutil.copytree(s_lf, d_lf)
        copied = True
    elif os.path.exists(d_lf):
        log(f"   -> [SKIP LOG] Đã có: {ts}")

    return copied

def execute_organize(test_root):
    results_dir = os.path.join(test_root, "results")
    logs_dir = os.path.join(test_root, "logs")
    report_dir = find_effective_report_dir(test_root)
    single_dir = os.path.join(report_dir, "single")
    
    log(f"=== BẮT ĐẦU THU THẬP & TỔ CHỨC REPORT TẠI: {report_dir} ===")
    
    if not os.path.exists(results_dir):
        log(f"[ERROR] Không tìm thấy thư mục results tại: {results_dir}")
        return False

    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(single_dir, exist_ok=True)

    log("[BƯỚC 1] Quét và phân loại các session kết quả trong results/...")
    sessions = []
    for item in sorted(os.listdir(results_dir)):
        p = os.path.join(results_dir, item)
        if not os.path.isdir(p) or item == "latest":
            continue
        parsed = parse_session(p)
        if parsed:
            parsed["timestamp"] = item
            sessions.append(parsed)

    multi_sessions = [s for s in sessions if s["type"] == "multiple"]
    single_sessions = defaultdict(list)
    tc_sessions = defaultdict(list)

    failed_in_multiple = set()
    for s in multi_sessions:
        xml_p = os.path.join(results_dir, s["timestamp"], "test_result.xml")
        if os.path.exists(xml_p):
            try:
                with open(xml_p, "r", errors="ignore") as f:
                    for line in f:
                        if "<Module " in line:
                            m_m = re.search(r'name="([^"]+)"[^>]*done="([^"]+)"', line)
                            if m_m and m_m.group(2).lower() != "true":
                                failed_in_multiple.add(m_m.group(1))
                            m_f = re.search(r'name="([^"]+)"[^>]*failed="([1-9]\d*)"', line)
                            if m_f:
                                failed_in_multiple.add(m_f.group(1))
            except Exception:
                pass

    for s in sessions:
        if s["type"] == "single":
            single_sessions[s["module_name"]].append(s)
        elif s["type"] == "testcase":
            tc_sessions[(s["module_name"], s["testcase_name"])].append(s)

    log(f"-> Quét được: {len(multi_sessions)} Multiple, {len(single_sessions)} Single Modules, {len(tc_sessions)} Testcase groups.")

    all_known_folders = {}
    if os.path.exists(report_dir):
        for f in os.listdir(report_dir):
            p = os.path.join(report_dir, f)
            if os.path.isdir(p) and f not in ["single", "results", "logs"]:
                all_known_folders[f] = {"loc": "root", "path": p}
    if os.path.exists(single_dir):
        for f in os.listdir(single_dir):
            p = os.path.join(single_dir, f)
            if os.path.isdir(p):
                all_known_folders[f] = {"loc": "single", "path": p}

    next_id = get_max_existing_id(report_dir)

    log("\n[BƯỚC 2] Thu thập session Multiple (áp dụng chọn lọc 2 đầu + 2 cuối)...")
    if multi_sessions:
        selected_multi = select_history_sessions(multi_sessions)
        dest_res = os.path.join(report_dir, "results")
        dest_log = os.path.join(report_dir, "logs")
        log(f"-> Multiple: {len(multi_sessions)} sessions -> Chọn giữ {len(selected_multi)} sessions:")
        for s in selected_multi:
            copy_session(results_dir, logs_dir, dest_res, dest_log, s["timestamp"])

    log("\n[BƯỚC 3] Thu thập Single Modules vào Report/single/...")
    for mod_name, s_list in single_sessions.items():
        matched = match_module_folder(all_known_folders, mod_name)
        if matched:
            target_fol_name = matched
            target_base = all_known_folders[matched]["path"]
        else:
            next_id += 1
            suffix = "_multi" if mod_name in failed_in_multiple else ""
            target_fol_name = f"{next_id:02d}.{mod_name}{suffix}"
            target_base = os.path.join(single_dir, target_fol_name)
            all_known_folders[target_fol_name] = {"loc": "single", "path": target_base}

        dest_res = os.path.join(target_base, "results")
        dest_log = os.path.join(target_base, "logs")

        selected_s = select_history_sessions(s_list)
        log(f"-> Module '{mod_name}' -> Thư mục: {target_fol_name} ({len(s_list)} sessions -> Giữ {len(selected_s)}):")
        for s in selected_s:
            copy_session(results_dir, logs_dir, dest_res, dest_log, s["timestamp"])

    log("\n[BƯỚC 4] Thu thập các Testcase chạy lẻ đã Pass vào Report/single/...")
    for (mod_name, tc_name), s_list in tc_sessions.items():
        passes = [s for s in s_list if s["is_pass"]]
        if not passes:
            log(f"-> Testcase '{mod_name}#{tc_name}': Chưa có session Pass -> Bỏ qua.")
            continue

        best_s = passes[-1]
        matched = match_testcase_folder(all_known_folders, mod_name, tc_name)
        if matched:
            target_fol_name = matched
            target_base = all_known_folders[matched]["path"]
        else:
            next_id += 1
            target_fol_name = f"{next_id:02d}.{mod_name}_{sanitize_name(tc_name)}"
            target_base = os.path.join(single_dir, target_fol_name)
            all_known_folders[target_fol_name] = {"loc": "single", "path": target_base}

        dest_res = os.path.join(target_base, "results")
        dest_log = os.path.join(target_base, "logs")
        log(f"-> [PASS TESTCASE] '{mod_name}#{tc_name}' -> Thư mục: {target_fol_name} (Session: {best_s['timestamp']})")
        copy_session(results_dir, logs_dir, dest_res, dest_log, best_s["timestamp"])

    log("\n[BƯỚC 5] Tái cấu trúc chuẩn hóa: Đưa toàn bộ module đơn lẻ vào Report/single/...")

    m_folder = None
    if os.path.exists(report_dir):
        for f in os.listdir(report_dir):
            if "multiple" in f.lower() and os.path.isdir(os.path.join(report_dir, f)):
                m_folder = f
                break
    if m_folder:
        m_path = os.path.join(report_dir, m_folder)
        log(f"-> Dọn dẹp chuyển kết quả từ '{m_folder}' ra root Report/results và logs...")
        in_res = os.path.join(m_path, "results")
        out_res = os.path.join(report_dir, "results")
        os.makedirs(out_res, exist_ok=True)
        if os.path.exists(in_res):
            for item in os.listdir(in_res):
                s_p = os.path.join(in_res, item)
                d_p = os.path.join(out_res, item)
                if not os.path.exists(d_p):
                    shutil.move(s_p, d_p)

        in_log = os.path.join(m_path, "logs")
        out_log = os.path.join(report_dir, "logs")
        os.makedirs(out_log, exist_ok=True)
        if os.path.exists(in_log):
            for item in os.listdir(in_log):
                s_p = os.path.join(in_log, item)
                d_p = os.path.join(out_log, item)
                if not os.path.exists(d_p):
                    shutil.move(s_p, d_p)

        try:
            shutil.rmtree(m_path)
            log(f"-> Đã xóa thư mục '{m_folder}' sau khi chuyển.")
        except Exception:
            pass

    if os.path.exists(report_dir):
        for item in os.listdir(report_dir):
            if item in ["results", "logs", "single"]:
                continue
            item_path = os.path.join(report_dir, item)
            if os.path.isdir(item_path) and re.match(r"^\d+\.", item):
                dest_in_single = os.path.join(single_dir, item)
                log(f"-> Di chuyển '{item}' từ root vào Report/single/{item}")
                if os.path.exists(dest_in_single):
                    for sub in ["results", "logs"]:
                        s_sub = os.path.join(item_path, sub)
                        d_sub = os.path.join(dest_in_single, sub)
                        os.makedirs(d_sub, exist_ok=True)
                        if os.path.exists(s_sub):
                            for sub_item in os.listdir(s_sub):
                                s_file = os.path.join(s_sub, sub_item)
                                d_file = os.path.join(d_sub, sub_item)
                                if not os.path.exists(d_file):
                                    shutil.move(s_file, d_file)
                    shutil.rmtree(item_path, ignore_errors=True)
                else:
                    shutil.move(item_path, dest_in_single)

    log("\n🎉 HOÀN TẤT THU THẬP VÀ TỔ CHỨC BÁO CÁO REPORT THÀNH CÔNG! 🎉")
    return True

if __name__ == "__main__":
    t_root = sys.argv[1] if len(sys.argv) > 1 else ""
    execute_organize(t_root)
"""
