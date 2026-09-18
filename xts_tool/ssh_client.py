"""
SSH Client wrapper using Paramiko.
Provides real-time command streaming, device check, and binary path detection.
"""
import os
import re
import socket
import select
import time
import paramiko
from typing import Callable, Optional, Tuple, List, Dict, Any
from device_checker import evaluate_device_connection, DeviceInfo


class SSHManager:
    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None
        self.host: str = ""
        self.port: int = 22
        self.username: str = ""
        self.password: Optional[str] = None
        self.key_path: Optional[str] = None

    def connect(self, host: str, port: int = 22, username: str = "lge", 
                password: Optional[str] = None, key_path: Optional[str] = None, 
                timeout: int = 10) -> Tuple[bool, str]:
        """Establish SSH connection."""
        self.disconnect()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path

        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": timeout,
                "banner_timeout": 30,
            }
            if key_path and os.path.exists(key_path):
                connect_kwargs["key_filename"] = key_path
            elif password:
                connect_kwargs["password"] = password

            self.client.connect(**connect_kwargs)
            return True, f"Kết nối thành công tới {username}@{host}:{port}"
        except Exception as e:
            self.client = None
            return False, f"Lỗi kết nối SSH: {str(e)}"

    def disconnect(self):
        """Disconnect active SSH connection."""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None

    def is_connected(self) -> bool:
        """Check if connection is alive."""
        if not self.client:
            return False
        transport = self.client.get_transport()
        return transport is not None and transport.is_active()

    ENV_PREFIX = (
        'export PATH="$HOME/Environment/AndroidSDK/platform-tools:'
        '/home/lge/Environment/AndroidSDK/platform-tools:'
        '/usr/lib/android-sdk/platform-tools:'
        '$HOME/Environment/AndroidSDK/cmdline-tools/tools/bin:'
        '$HOME/bin:$HOME/.local/bin:'
        '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"; '
    )

    def _wrap_command(self, cmd: str) -> str:
        """Prepends essential environment PATH to commands for non-interactive SSH shells."""
        clean = cmd.strip()
        if clean.startswith("export PATH=") or clean.startswith("bash -l"):
            return cmd
        return f"{self.ENV_PREFIX}{cmd}"

    def run_command(self, cmd: str, timeout: int = 60) -> Tuple[int, str, str]:
        """Runs a synchronous command on remote server."""
        if not self.is_connected():
            return -1, "", "SSH chưa được kết nối."
        try:
            wrapped = self._wrap_command(cmd)
            stdin, stdout, stderr = self.client.exec_command(wrapped, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            exit_code = stdout.channel.recv_exit_status()
            return exit_code, out, err
        except Exception as e:
            return -1, "", str(e)

    def upload_file(self, local_path: str, remote_path: str) -> Tuple[bool, str]:
        """Uploads a local file to remote server via SFTP."""
        if not self.is_connected():
            return False, "SSH chưa được kết nối."
        if not os.path.exists(local_path):
            return False, f"File nguồn không tồn tại: {local_path}"
        try:
            sftp = self.client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            return True, f"Upload thành công: {remote_path}"
        except Exception as e:
            return False, f"Lỗi upload SFTP: {str(e)}"

    def run_command_stream(self, cmd: str, output_callback: Optional[Callable[[str], None]] = None,
                           check_abort: Optional[Callable[[], bool]] = None,
                           auto_press_any_key: bool = True,
                           auto_confirm_yn: bool = False) -> Tuple[int, str]:
        """
        Runs command and streams stdout/stderr chunk by chunk in real-time.
        Can be aborted via check_abort callback.
        If auto_press_any_key is True, automatically sends Enter whenever prompts
        like 'Press any key to continue' appear in the output stream.
        If auto_confirm_yn is True, automatically sends 'Y' whenever prompts
        like '(Y/N)' or 'rename + zip folders' appear in the output stream.
        """
        if not self.is_connected():
            if output_callback:
                output_callback("[ERROR] SSH chưa được kết nối.\n")
            return -1, "SSH chưa kết nối"

        try:
            transport = self.client.get_transport()
            channel = transport.open_session()
            channel.get_pty(term="xterm", width=120, height=40)
            wrapped = self._wrap_command(cmd)
            channel.exec_command(wrapped)

            full_output = []
            prompt_buffer = ""
            prompt_patterns = [
                re.compile(r"press any (key|button)", re.IGNORECASE),
                re.compile(r"nhấn phím bất kỳ", re.IGNORECASE)
            ]
            yn_patterns = [
                re.compile(r"\(Y/N\)", re.IGNORECASE),
                re.compile(r"\[Y/N\]", re.IGNORECASE),
                re.compile(r"\(y/n\)", re.IGNORECASE),
                re.compile(r"\[y/n\]", re.IGNORECASE),
                re.compile(r"rename \+ zip folders", re.IGNORECASE),
            ]

            while True:
                if check_abort and check_abort():
                    channel.close()
                    if output_callback:
                        output_callback("\n[ABORTED] Tiến trình đã bị dừng bởi người dùng.\n")
                    return -999, "".join(full_output)

                r, _, _ = select.select([channel], [], [], 0.2)
                if r:
                    if channel.recv_ready():
                        data = channel.recv(4096).decode("utf-8", errors="replace")
                        if data:
                            full_output.append(data)
                            if output_callback:
                                output_callback(data)
                            if auto_press_any_key or auto_confirm_yn:
                                prompt_buffer += data
                    
                    if channel.recv_stderr_ready():
                        err_data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                        if err_data:
                            full_output.append(err_data)
                            if output_callback:
                                output_callback(err_data)
                            if auto_press_any_key or auto_confirm_yn:
                                prompt_buffer += err_data

                    if (auto_press_any_key or auto_confirm_yn) and prompt_buffer:
                        if len(prompt_buffer) > 2000:
                            prompt_buffer = prompt_buffer[-1000:]

                        # Check Y/N prompts first
                        if auto_confirm_yn:
                            matched_yn = False
                            for pat in yn_patterns:
                                if pat.search(prompt_buffer):
                                    prompt_buffer = ""
                                    if output_callback:
                                        output_callback("\n[Auto-confirm] Phát hiện yêu cầu xác nhận '(Y/N)', tự động gửi 'Y' để tiếp tục...\n")
                                    time.sleep(0.3)
                                    channel.send("Y\n")
                                    matched_yn = True
                                    break
                            if matched_yn:
                                continue

                        if auto_press_any_key:
                            for pat in prompt_patterns:
                                if pat.search(prompt_buffer):
                                    prompt_buffer = ""
                                    if output_callback:
                                        output_callback("\n[Auto-confirm] Phát hiện yêu cầu xác nhận ('Press any key'), tự động gửi phím Enter để tiếp tục...\n")
                                    time.sleep(0.5)
                                    channel.send("\n")
                                    break

                if channel.exit_status_ready():
                    # Read any remaining output
                    while channel.recv_ready():
                        data = channel.recv(4096).decode("utf-8", errors="replace")
                        if data:
                            full_output.append(data)
                            if output_callback:
                                output_callback(data)
                    while channel.recv_stderr_ready():
                        err_data = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                        if err_data:
                            full_output.append(err_data)
                            if output_callback:
                                output_callback(err_data)
                    break

            exit_status = channel.recv_exit_status()
            return exit_status, "".join(full_output)
        except Exception as e:
            err_msg = f"\n[ERROR] Lỗi khi thực thi lệnh: {str(e)}\n"
            if output_callback:
                output_callback(err_msg)
            return -1, err_msg

    def check_devices(self) -> Tuple[bool, str, List[DeviceInfo]]:
        """
        Executes 'adb devices' and 'fastboot devices' on remote server.
        Returns evaluation of single-device requirement.
        """
        if not self.is_connected():
            return False, "SSH chưa kết nối.", []

        _, adb_out, _ = self.run_command("adb devices", timeout=10)
        _, fb_out, _ = self.run_command("fastboot devices", timeout=10)

        return evaluate_device_connection(adb_out, fb_out)

    def detect_binary_paths(self, root_dir: str = "/home/lge/Environment/Storage/Binary/") -> Dict[str, str]:
        """
        Scans remote server Binary directory using python/bash to find user and userdebug release paths.
        - userdebug: folder containing flash scripts with 'userdebug' or '_BDV' (non-PROD) in path
        - user: folder containing flash scripts with 'user' (not userdebug) or '_PROD' in path
        """
        results = {
            "userdebug_path": "",
            "user_path": "",
            "details": []
        }

        if not self.is_connected():
            results["details"].append("Lỗi: SSH chưa kết nối.")
            return results

        # 1. Advanced search using python on remote host
        find_script = f"""python3 -c '
import os, glob, json

root = "{root_dir}"
data = {{"userdebug": "", "user": ""}}

userdebug_candidates = []
user_candidates = []

if os.path.exists(root):
    for dirpath, dirnames, filenames in os.walk(root):
        has_blank = "fastboot_n_fullnavi_blank_flash.sh" in filenames
        has_reflash = "fastboot_n_fullnavi_reflash.sh" in filenames
        
        if not (has_blank or has_reflash):
            continue
            
        p_lower = dirpath.lower()
        if "trash" in p_lower:
            continue
            
        try:
            mtime = os.path.getmtime(dirpath)
        except Exception:
            mtime = 0
            
        is_userdebug = ("userdebug" in p_lower) or ("_bdv" in p_lower and "_prod" not in p_lower)
        is_user = (("user" in p_lower and "userdebug" not in p_lower) or "_prod" in p_lower)
        
        if is_userdebug:
            score = mtime + (1000 if has_blank else 0)
            userdebug_candidates.append((score, dirpath))
            
        if is_user:
            score = mtime + (1000 if has_reflash else 0)
            user_candidates.append((score, dirpath))

    if userdebug_candidates:
        userdebug_candidates.sort(key=lambda x: x[0], reverse=True)
        data["userdebug"] = userdebug_candidates[0][1]

    if user_candidates:
        user_candidates.sort(key=lambda x: x[0], reverse=True)
        data["user"] = user_candidates[0][1]

    # Fallback if scripts not directly found: search by top-level folder names
    if not data["userdebug"] or not data["user"]:
        for item in sorted(os.listdir(root), reverse=True):
            full = os.path.join(root, item)
            if not os.path.isdir(full):
                continue
            item_lower = item.lower()
            if not data["userdebug"] and "userdebug" in item_lower:
                subs = sorted(glob.glob(os.path.join(full, "RELEASE_*")), reverse=True)
                data["userdebug"] = subs[0] if subs else full
            if not data["user"] and "user" in item_lower and "userdebug" not in item_lower:
                subs = sorted(glob.glob(os.path.join(full, "RELEASE_*")), reverse=True)
                data["user"] = subs[0] if subs else full

print(json.dumps(data))
'
"""
        code, out, err = self.run_command(find_script, timeout=20)
        import json
        if code == 0 and out.strip():
            try:
                # Find JSON block in output
                json_start = out.find("{")
                json_end = out.rfind("}") + 1
                if json_start != -1 and json_end != -1:
                    parsed = json.loads(out[json_start:json_end])
                    results["userdebug_path"] = parsed.get("userdebug", "").replace("\\", "/")
                    results["user_path"] = parsed.get("user", "").replace("\\", "/")
            except Exception as e:
                results["details"].append(f"Không phân tích được kết quả JSON: {e}")

        # Fallback to bash find if python script failed or did not find
        if not results["userdebug_path"]:
            c1, o1, _ = self.run_command(
                f'find {root_dir} -type f -name "fastboot_n_fullnavi_blank_flash.sh" 2>/dev/null | grep -i "userdebug" | head -n 1'
            )
            if c1 == 0 and o1.strip():
                results["userdebug_path"] = os.path.dirname(o1.strip()).replace("\\", "/")
            else:
                c1_b, o1_b, _ = self.run_command(
                    f'find {root_dir} -maxdepth 3 -type d 2>/dev/null | grep -i "userdebug" | head -n 1'
                )
                if c1_b == 0 and o1_b.strip():
                    results["userdebug_path"] = o1_b.strip().replace("\\", "/")

        if not results["user_path"]:
            c2, o2, _ = self.run_command(
                f'find {root_dir} -type f -name "fastboot_n_fullnavi_reflash.sh" 2>/dev/null | grep -i "user" | grep -v -i "userdebug" | head -n 1'
            )
            if c2 == 0 and o2.strip():
                results["user_path"] = os.path.dirname(o2.strip()).replace("\\", "/")
            else:
                c2_b, o2_b, _ = self.run_command(
                    f'find {root_dir} -maxdepth 3 -type d 2>/dev/null | grep -i "user" | grep -v -i "userdebug" | head -n 1'
                )
                if c2_b == 0 and o2_b.strip():
                    results["user_path"] = o2_b.strip().replace("\\", "/")

        # Final sanity check: userdebug and user must NOT be identical
        if results["userdebug_path"] and results["user_path"] and results["userdebug_path"] == results["user_path"]:
            p_lower = results["userdebug_path"].lower()
            if "userdebug" in p_lower:
                results["user_path"] = ""
            else:
                results["userdebug_path"] = ""

        return results

    def detect_test_roots(self, base_dir: str = "/home/lge/GoogleQA/TestFolder/") -> List[str]:
        """
        Discovers test roots under base_dir (folders containing android-cts, android-ats, android-vts, etc.)
        """
        if not self.is_connected():
            return []
        
        cmd = f'find {base_dir} -maxdepth 3 -type d \\( -name "android-cts" -o -name "android-ats" -o -name "android-vts" -o -name "android-sts" \\) 2>/dev/null'
        code, out, _ = self.run_command(cmd, timeout=10)
        if code == 0 and out.strip():
            lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
            return lines
        return []

    def scan_report_preview(self, test_root: str) -> Dict[str, Any]:
        """
        Runs remote scan script to return JSON analysis of sessions in results/ and Report/.
        """
        import json
        from report_collector import REMOTE_SCAN_SCRIPT

        if not self.is_connected():
            return {"error": "SSH chưa được kết nối."}

        try:
            sftp = self.client.open_sftp()
            with sftp.file("/tmp/xts_scan_report.py", "w") as f:
                f.write(REMOTE_SCAN_SCRIPT)
            sftp.close()

            code, out, err = self.run_command(f'python3 /tmp/xts_scan_report.py "{test_root}"', timeout=30)
            if code == 0 and out.strip():
                json_start = out.find("{")
                json_end = out.rfind("}") + 1
                if json_start != -1 and json_end != -1:
                    return json.loads(out[json_start:json_end])
            return {"error": f"Lỗi khi quét kết quả: {err or out}"}
        except Exception as e:
            return {"error": f"Lỗi ngoại lệ khi quét: {str(e)}"}

    def run_report_organize_stream(self, test_root: str,
                                   output_callback: Optional[Callable[[str], None]] = None,
                                   check_abort: Optional[Callable[[], bool]] = None) -> Tuple[int, str]:
        """
        Uploads and runs organize script on server, streaming logs chunk-by-chunk in real time.
        """
        from report_collector import REMOTE_ORGANIZE_SCRIPT

        if not self.is_connected():
            if output_callback:
                output_callback("[ERROR] SSH chưa kết nối.\n")
            return -1, "SSH chưa kết nối"

        try:
            sftp = self.client.open_sftp()
            with sftp.file("/tmp/xts_organize_report.py", "w") as f:
                f.write(REMOTE_ORGANIZE_SCRIPT)
            sftp.close()

            cmd = f'python3 /tmp/xts_organize_report.py "{test_root}"'
            return self.run_command_stream(cmd, output_callback=output_callback, check_abort=check_abort)
        except Exception as e:
            err_msg = f"[ERROR] Lỗi khi thực thi tổ chức Report: {str(e)}\n"
            if output_callback:
                output_callback(err_msg)
            return -1, err_msg

