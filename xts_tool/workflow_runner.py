"""
Workflow Runner for xTS Pre-Setup.
Manages step execution, waiting for devices (fastboot/adb), error handling, 
manual authentication prompts, and single/all step modes.
"""
import os
import time
import threading
from typing import Dict, List, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal
from ssh_client import SSHManager


class StepDecision:
    RETRY = "RETRY"
    SKIP = "SKIP"
    ABORT = "ABORT"


def build_workflow_steps(suite_name: str, paths: Dict[str, Any], arduino_enabled: bool = False,
                         precondition_cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Builds the list of steps for the selected test suite.
    Paths dict contains:
      - userdebug_path: str
      - user_path: str
      - google_key_path: str
      - google_key_script: str
      - google_key_retry_script: str
      - mtc_path: str
      - mtc_scripts: list of str
      - calibration_path: str
      - calibration_script: str
      - gsi_image_path: str
    precondition_cfg: {"enabled": bool, "wifi_ssid": str, "wifi_password": str}
        Neu enabled, them buoc Precondition (port tu Precondition.sh ban goc:
        WiFi verify ping, tat lockscreen, stay-awake, gio 12h, en-US) vao cuoi workflow.
    """
    suite = suite_name.upper()

    userdebug_dir = paths.get("userdebug_path", "")
    user_dir = paths.get("user_path", "")
    gkey_dir = paths.get("google_key_path", "")
    gkey_script = paths.get("google_key_script", "./AddGoogle_key_Nissan.sh")
    
    mtc_dir = paths.get("mtc_path", "")
    mtc_scripts = paths.get("mtc_scripts", ["./MTC_PZ1D_26MY.sh", "./ChangeLanguage.sh"])
    
    calib_dir = paths.get("calibration_path", "")
    calib_script = paths.get("calibration_script", "./do_calibration.sh")
    
    gsi_dir = paths.get("gsi_image_path", "")

    steps = []

    def _maybe_append_precondition():
        """Thêm bước Precondition vào cuối (port Precondition.sh bản gốc)."""
        if precondition_cfg and precondition_cfg.get("enabled", True):
            num = len(steps) + 1
            steps.append({
                "id": "precondition",
                "title": f"{num}. Precondition (WiFi/Lockscreen/StayAwake)",
                "type": "precondition",
                "wifi_ssid": precondition_cfg.get("wifi_ssid", ""),
                "wifi_password": precondition_cfg.get("wifi_password", ""),
                "desc": "Kết nối WiFi (verify ping), tắt lockscreen vĩnh viễn, stay-awake, giờ 12h, en-US"
            })

    # Step 1: Flash Userdebug (Common to all)
    steps.append({
        "id": "flash_userdebug",
        "title": "1. Flash Userdebug",
        "type": "flash_sw",
        "workdir": userdebug_dir,
        "script": "./fastboot_n_fullnavi_blank_flash.sh",
        "reboot_after": True,
        "desc": "Reboot bootloader -> fastboot_n_fullnavi_blank_flash.sh -> reboot & chờ adb"
    })

    # Step 2: Google Attestation Key (Common to all)
    steps.append({
        "id": "google_key",
        "title": "2. Google Attestation Key",
        "type": "run_commands",
        "workdir": gkey_dir,
        "commands": [gkey_script],
        "desc": f"Run {gkey_script}"
    })

    # Step 3: MTC Update (& Calibration for ATS)
    if "ATS" in suite:
        steps.append({
            "id": "mtc_and_calibration",
            "title": "3. MTC Update & Calibration",
            "type": "composite",
            "substeps": [
                {"workdir": mtc_dir, "commands": mtc_scripts, "title": "MTC Scripts"},
                {"workdir": calib_dir, "commands": [calib_script], "title": "Calibration"}
            ],
            "desc": "Chạy MTC Scripts, ChangeLanguage & do_calibration.sh"
        })
    else:
        steps.append({
            "id": "mtc_update",
            "title": "3. MTC Update",
            "type": "run_commands",
            "workdir": mtc_dir,
            "commands": mtc_scripts,
            "desc": "Chạy MTC Scripts & ChangeLanguage.sh"
        })

    # STS specific: Step 4 is direct lock bootloader, no user build
    if "STS" in suite:
        steps.append({
            "id": "lock_bootloader",
            "title": "4. Lock Bootloader",
            "type": "lock_bootloader",
            "wait_for_adb": True,
            "desc": "adb reboot bootloader -> fastboot flashing lock -> reboot & chờ adb"
        })
        _maybe_append_precondition()
        return steps

    # For ATS, CTS, GSI, VTS: Flash User Build
    steps.append({
        "id": "flash_user",
        "title": "4. Flash User Build",
        "type": "flash_sw",
        "workdir": user_dir,
        "script": "./fastboot_n_fullnavi_reflash.sh",
        "reboot_after": True,
        "wait_for_adb": False,
        "desc": "Reboot bootloader -> fastboot_n_fullnavi_reflash.sh -> reboot (không chờ adb)"
    })

    # Manual Authentication #1
    if arduino_enabled:
        steps.append({
            "id": "arduino_auth_1",
            "title": "5. Xác thực tự động (Arduino)",
            "type": "arduino_auth",
            "desc": "Tự động Bypass RSA & Setup Wizard bằng Arduino"
        })
    else:
        steps.append({
            "id": "manual_auth_1",
            "title": "5. Xác thực thủ công (Manual Authentication)",
            "type": "manual_auth",
            "prompt": "Đã hoàn thành flash User Build.\nVui lòng thực hiện thao tác xác thực trên màn hình thiết bị.\nBấm 'Tiếp tục' sau khi hoàn tất thành công.",
            "desc": "Yêu cầu người dùng xác thực thủ công trên màn hình xe/device"
        })

    if "ATS" in suite or "CTS" in suite and "GSI" not in suite:
        # ATS & CTS: Step 6 is Lock bootloader, Step 7 is second manual auth
        steps.append({
            "id": "lock_bootloader",
            "title": "6. Lock Bootloader",
            "type": "lock_bootloader",
            "wait_for_adb": False,
            "desc": "adb reboot bootloader -> fastboot flashing lock -> reboot (không chờ adb)"
        })
        if arduino_enabled:
            steps.append({
                "id": "arduino_auth_2",
                "title": "7. Xác thực lại tự động (Arduino)",
                "type": "arduino_auth",
                "desc": "Tự động Bypass RSA sau khi lock bootloader bằng Arduino"
            })
        else:
            steps.append({
                "id": "manual_auth_2",
                "title": "7. Xác thực lại thủ công (Post-lock Authentication)",
                "type": "manual_auth",
                "prompt": "Đã khóa Bootloader thành công.\nVui lòng thực hiện xác thực thủ công lại trên màn hình thiết bị lần cuối.\nBấm 'Tiếp tục' sau khi hoàn tất thành công.",
                "desc": "Xác thực lại sau khi bootloader locked"
            })

    elif "GSI" in suite or "VTS" in suite:
        # GSI / VTS setting:
        # Flash boot-debug.img
        steps.append({
            "id": "flash_boot_debug",
            "title": "6. Flash Boot-Debug Image",
            "type": "flash_boot_debug",
            "workdir": user_dir,
            "desc": "adb reboot bootloader -> fastboot flash boot_a/boot_b boot-debug.img -> reboot"
        })

        # Flash system.img in fastbootd
        steps.append({
            "id": "flash_gsi_system",
            "title": "7. Flash GSI System Image",
            "type": "flash_system_gsi",
            "workdir": gsi_dir,
            "desc": "adb reboot fastboot -> fastboot erase system_a -> fastboot flash -S 250M system_a system.img -> reboot"
        })

        # GSI only: Flash back boot.img
        if "GSI" in suite:
            steps.append({
                "id": "flash_boot_orig",
                "title": "8. Flash Lại Boot.img Gốc",
                "type": "flash_boot_orig",
                "workdir": user_dir,
                "desc": "adb reboot bootloader -> fastboot flash boot_a/boot_b boot.img -> reboot"
            })

    _maybe_append_precondition()
    return steps


class WorkflowWorker(QThread):
    # Signals
    log_signal = pyqtSignal(str, str)  # (text, level: 'INFO', 'WARN', 'ERROR', 'SUCCESS', 'STREAM')
    step_started_signal = pyqtSignal(int, str)  # (step_idx, step_title)
    step_finished_signal = pyqtSignal(int, str, bool)  # (step_idx, step_title, success)
    workflow_finished_signal = pyqtSignal(bool, str)  # (overall_success, summary)
    progress_signal = pyqtSignal(int, int)  # (current, total)
    
    # Interactive signals
    manual_auth_signal = pyqtSignal(dict)  # (auth_info: dict with step_idx, step_title, prompt, server_host, suite_name, device_serial)
    step_error_signal = pyqtSignal(int, str, str)  # (step_idx, step_title, error_message)

    def __init__(self, ssh_mgr: SSHManager, steps: List[Dict[str, Any]], 
                 single_step_idx: Optional[int] = None, timeouts: Optional[Dict[str, int]] = None,
                 server_host: str = "", suite_name: str = "", arduino_config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.ssh = ssh_mgr
        self.steps = steps
        self.single_step_idx = single_step_idx
        self.server_host = server_host or getattr(ssh_mgr, "host", "")
        self.suite_name = suite_name
        self._current_step_idx = single_step_idx or 0
        self._device_serial = ""
        self.timeouts = timeouts or {
            "bootloader_wait_sec": 30,
            "adb_reboot_wait_sec": 80,
            "fastbootd_wait_sec": 45,
            "poll_interval_sec": 3
        }

        # Arduino configuration — follow AutoFlashing devices.setup() logic
        self.arduino_config = arduino_config or {}
        self._arduino_enabled = self.arduino_config.get("enabled", False)
        kb = self.arduino_config.get("kb_signal", "K1") or "K1"
        last_char = kb[-1]  # safe even for single-char signals (avoids kb[1] IndexError)
        self._kb_signal = kb                      # e.g. "K1"   — single click (Enable USB Debug / RSA Allow)
        self._kb_double = kb + last_char          # e.g. "K11"  — double click (Allow Privacy)
        self._kb_triple = kb + last_char + last_char  # e.g. "K111" — triple click (Exit Recovery)
        self._rl_signal = self.arduino_config.get("rl_signal", "R1")  # Relay on
        self._controlpcb_path = self.arduino_config.get("controlpcb_path", "/home/lge/Environment/scripts/ControlPCB.py")

        self._abort_requested = False
        
        # Sync primitives for interactive dialogs
        self._auth_event = threading.Event()
        self._auth_result = False

        self._error_event = threading.Event()
        self._error_decision = StepDecision.ABORT

    def request_abort(self):
        self._abort_requested = True
        self._auth_event.set()
        self._error_event.set()

    def is_aborted(self) -> bool:
        return self._abort_requested

    def provide_auth_response(self, confirmed: bool):
        self._auth_result = confirmed
        self._auth_event.set()

    def provide_error_decision(self, decision: str):
        self._error_decision = decision
        self._error_event.set()

    def log(self, text: str, level: str = "INFO"):
        self.log_signal.emit(text, level)

    def run(self):
        """Worker thread entry point."""
        self.log("=== BẮT ĐẦU QUY TRÌNH PRE-SETUP ===", "INFO")

        if not self.ssh.is_connected():
            self.log("[ERROR] SSH chưa được kết nối!", "ERROR")
            self.workflow_finished_signal.emit(False, "SSH chưa kết nối.")
            return

        # 1. Device check verification
        self.log("Kiểm tra thiết bị kết nối trước khi thực thi...", "INFO")
        valid, msg, devs = self.ssh.check_devices()
        if not valid:
            self.log(f"[ERROR] {msg}", "ERROR")
            self.workflow_finished_signal.emit(False, f"Kiểm tra thiết bị thất bại: {msg}")
            return
        self.log(f"[OK] {msg}", "SUCCESS")

        if self._arduino_enabled:
            self.log("Kiểm tra kết nối mạch Arduino...", "INFO")
            code, out, _ = self.ssh.run_command("test -e /dev/arduino")
            if code != 0:
                self.log("[CẢNH BÁO] Không tìm thấy kết nối /dev/arduino trên server!", "WARN")
                self._auth_event.clear()
                self._auth_result = False
                self.manual_auth_signal.emit({
                    "step_idx": -1,
                    "step_title": "Cảnh Báo Arduino",
                    "prompt": "Tính năng tự động Bypass bằng Arduino đang BẬT nhưng không tìm thấy thiết bị kết nối (/dev/arduino) trên server.\n\nBạn có quên cắm dây cáp Arduino không?\nNhấn 'Tiếp tục' để bỏ qua và chuyển sang xác thực bằng tay, hoặc tắt bảng này để Hủy.",
                    "server_host": self.server_host,
                    "suite_name": self.suite_name,
                    "device_serial": self._get_device_serial()
                })
                self._auth_event.wait()
                if not self._auth_result or self._abort_requested:
                    self.log("Người dùng đã hủy quy trình do thiếu Arduino.", "ERROR")
                    self.workflow_finished_signal.emit(False, "Hủy quy trình do thiếu Arduino.")
                    return
                else:
                    self.log("Chuyển về chế độ xác thực thủ công.", "WARN")
                    self._arduino_enabled = False
            else:
                self.log("[OK] Arduino đã được kết nối sẵn sàng (/dev/arduino).", "SUCCESS")

        steps_to_run = []
        if self.single_step_idx is not None:
            if 0 <= self.single_step_idx < len(self.steps):
                steps_to_run = [(self.single_step_idx, self.steps[self.single_step_idx])]
        else:
            steps_to_run = list(enumerate(self.steps))

        total = len(steps_to_run)
        success_all = True

        for i, (orig_idx, step) in enumerate(steps_to_run):
            if self._abort_requested:
                self.log("Tiến trình đã bị hủy bởi người dùng.", "WARN")
                success_all = False
                break

            self._current_step_idx = orig_idx
            self.progress_signal.emit(i + 1, total)
            self.step_started_signal.emit(orig_idx, step["title"])
            self.log(f"\n--- [{i+1}/{total}] {step['title']} ---", "INFO")
            self.log(f"Mô tả: {step.get('desc', '')}", "INFO")

            step_ok = False
            while not step_ok:
                if self._abort_requested:
                    break

                try:
                    step_ok = self._execute_step(step)
                except Exception as e:
                    self.log(f"[EXCEPTION] Lỗi khi thực hiện bước: {str(e)}", "ERROR")
                    step_ok = False

                if step_ok:
                    self.log(f"[SUCCESS] Hoàn thành: {step['title']}\n", "SUCCESS")
                    self.step_finished_signal.emit(orig_idx, step["title"], True)
                    break
                else:
                    self.log(f"[FAILED] Bước thất bại: {step['title']}", "ERROR")
                    self.step_finished_signal.emit(orig_idx, step["title"], False)

                    if self._abort_requested:
                        break

                    # Prompt user for decision: RETRY / SKIP / ABORT
                    self._error_event.clear()
                    self._error_decision = StepDecision.ABORT
                    self.step_error_signal.emit(orig_idx, step["title"], "Lệnh thực thi trả về mã lỗi hoặc mất kết nối.")
                    
                    self._error_event.wait()

                    if self._error_decision == StepDecision.RETRY:
                        self.log(f"Đang thử lại bước: {step['title']}...", "WARN")
                        continue
                    elif self._error_decision == StepDecision.SKIP:
                        self.log(f"Người dùng đã chọn BỎ QUA bước: {step['title']}", "WARN")
                        step_ok = True
                        break
                    else:  # ABORT
                        self.log("Người dùng đã chọn DỪNG quy trình.", "ERROR")
                        self._abort_requested = True
                        success_all = False
                        break

            if not step_ok and self._abort_requested:
                success_all = False
                break

        if success_all and not self._abort_requested:
            self.log("\n🎉 TẤT CẢ CÁC BƯỚC PRE-SETUP ĐÃ HOÀN THÀNH THÀNH CÔNG! 🎉", "SUCCESS")
            self.workflow_finished_signal.emit(True, "Pre-setup hoàn tất thành công.")
        else:
            self.log("\n⚠️ Quy trình Pre-setup kết thúc không hoàn chỉnh.", "WARN")
            self.workflow_finished_signal.emit(False, "Quy trình bị dừng hoặc có lỗi.")

    # -------------------------------------------------------------
    # Step Execution Dispatcher
    # -------------------------------------------------------------
    def _execute_step(self, step: Dict[str, Any]) -> bool:
        stype = step.get("type")
        sid = step.get("id", "")

        # Kiểm tra và đảm bảo thiết bị đã ở trạng thái ADB ổn định trước khi chạy Google Key hoặc MTC Update
        if sid == "google_key":
            if not self._ensure_adb_ready("Trước khi chạy Google Attestation Key", post_sleep=10):
                return False
        elif sid in ["mtc_update", "mtc_and_calibration"]:
            if not self._ensure_adb_ready("Trước khi chạy MTC Update", post_sleep=10):
                return False
        
        if stype == "flash_sw":
            return self._step_flash_sw(step)
        elif stype == "run_commands":
            return self._step_run_commands(step.get("workdir", ""), step.get("commands", []))
        elif stype == "composite":
            return self._step_composite(step)
        elif stype == "lock_bootloader":
            return self._step_lock_bootloader(step)
        elif stype == "manual_auth":
            return self._step_manual_auth(step)
        elif stype == "arduino_auth":
            return self._step_arduino_auth(step)
        elif stype == "flash_boot_debug":
            return self._step_flash_boot_debug(step)
        elif stype == "flash_system_gsi":
            return self._step_flash_system_gsi(step)
        elif stype == "flash_boot_orig":
            return self._step_flash_boot_orig(step)
        elif stype == "precondition":
            return self._step_precondition(step)
        else:
            self.log(f"Không nhận diện được loại bước: {stype}", "ERROR")
            return False


    # -------------------------------------------------------------
    # Device Wait Helpers
    # -------------------------------------------------------------
    def _get_device_serial(self) -> str:
        code, out, _ = self.ssh.run_command("adb get-serialno", timeout=5)
        serial = out.strip()
        if code == 0 and serial and serial != "unknown":
            return serial
        return ""

    def _check_adb_status(self) -> str:
        """
        Kiểm tra trạng thái ADB chi tiết của thiết bị.
        Follow logic hàm check_adb_devices() trong AutoFlashing.py (dòng 84-95).
        Returns: "PASS" | "UNAUTHORIZED" | "RECOVERY" | "FAIL"
        """
        code, out, _ = self.ssh.run_command("adb devices", timeout=10)
        if code != 0:
            return "FAIL"
        for line in out.strip().splitlines():
            line = line.strip()
            if line.endswith("\tdevice") or line.endswith(" device"):
                return "PASS"
            elif "unauthorized" in line:
                return "UNAUTHORIZED"
            elif "recovery" in line:
                return "RECOVERY"
        return "FAIL"

    def _wait_for_adb_any_state(self, timeout_sec: int = 90) -> str:
        """
        Chờ thiết bị xuất hiện trong 'adb devices' ở BẤT KỲ trạng thái nào
        (device / unauthorized / recovery), khác với _wait_for_adb() chỉ
        chấp nhận trạng thái authorized ("\tdevice").

        Rất quan trọng cho _step_arduino_auth: dialog RSA (UNAUTHORIZED) chỉ
        hiện khi máy đã boot nhưng chưa authorized — nếu dùng _wait_for_adb()
        ở đây thì nhánh xử lý UNAUTHORIZED/RECOVERY phía dưới không bao giờ
        tới được (timeout 80s rồi reboot relay vô ích).

        Returns: "PASS" | "UNAUTHORIZED" | "RECOVERY" | "" (timeout/abort)
        """
        start = time.time()
        while time.time() - start < timeout_sec:
            if self._abort_requested:
                return ""
            status = self._check_adb_status()
            if status in ("PASS", "UNAUTHORIZED", "RECOVERY"):
                return status
            time.sleep(self.timeouts.get("poll_interval_sec", 3))
        return ""

    def _send_arduino(self, signal: str):
        """
        Gửi tín hiệu điều khiển xuống mạch Arduino qua SSH.
        Follow logic hàm ControlPCB() trong AutoFlashing.py (dòng 127-137).
        """
        cmd = f'python3 {self._controlpcb_path} "{signal}"'
        self.log(f"[Arduino] Gửi tín hiệu: {signal} → {cmd}", "INFO")
        code, out, err = self.ssh.run_command(cmd, timeout=10)
        if code != 0:
            self.log(f"[Arduino] Cảnh báo: Lệnh trả về mã {code}. Stderr: {err}", "WARN")

    def _ensure_adb_ready(self, reason: str = "", post_sleep: int = 10, timeout_sec: int = 90) -> bool:
        """
        Đảm bảo thiết bị đã ở trạng thái kết nối ADB ổn định trước khi thực hiện bước kế tiếp.
        Nếu thiết bị chưa ở trạng thái ADB (ví dụ đang reboot từ script trước đó), 
        sẽ tự động chờ đến khi thiết bị xuất hiện trong 'adb devices'.
        Sau đó tạm dừng post_sleep giây (~10s) để adbd và các dịch vụ nền Android ổn định hoàn toàn.
        """
        if self._abort_requested:
            return False

        header_msg = f"[{reason}] " if reason else ""
        self.log(f"{header_msg}Kiểm tra trạng thái kết nối ADB của thiết bị...", "INFO")

        # 1. Kiểm tra trạng thái ADB hiện tại
        code, out, _ = self.ssh.run_command("adb devices", timeout=10)
        online = False
        if code == 0:
            lines = [l for l in out.strip().splitlines() if "\tdevice" in l]
            if lines:
                online = True
                self.log(f"[OK] Thiết bị đang online trong ADB: {lines[0]}", "SUCCESS")

        # 2. Nếu chưa online, tiến hành chờ thiết bị khởi động về ADB
        if not online:
            self.log(f"{header_msg}Thiết bị chưa ở trạng thái ADB (có thể đang khởi động lại từ bước trước). Đang chờ kết nối (tối đa {timeout_sec}s)...", "WARN")
            start = time.time()
            retry_cnt = 0
            while time.time() - start < timeout_sec:
                if self._abort_requested:
                    return False
                retry_cnt += 1
                time.sleep(self.timeouts.get("poll_interval_sec", 3))
                code, out, _ = self.ssh.run_command("adb devices", timeout=10)
                if code == 0:
                    lines = [l for l in out.strip().splitlines() if "\tdevice" in l]
                    if lines:
                        online = True
                        self.log(f"[OK] Thiết bị đã khởi động và xuất hiện trong ADB: {lines[0]}", "SUCCESS")
                        break
                if retry_cnt % 5 == 0:
                    self.log(f"Vẫn đang chờ thiết bị vào trạng thái ADB (lần {retry_cnt})...", "INFO")

            if not online:
                self.log(f"[ERROR] {header_msg}Hết thời gian chờ (timeout {timeout_sec}s)! Thiết bị không kết nối được qua ADB.", "ERROR")
                return False

        # 3. Sau khi device đã online, sleep ~10s để adbd và các service hệ thống ổn định hoàn toàn
        if post_sleep > 0:
            self.log(f"{header_msg}Thiết bị đã ở trạng thái ADB. Tạm dừng {post_sleep}s để hệ thống ổn định hoàn toàn trước khi tiếp tục...", "INFO")
            for _ in range(post_sleep):
                if self._abort_requested:
                    return False
                time.sleep(1)

        # 4. Kiểm tra phản hồi thực tế từ adb shell
        test_code, test_out, _ = self.ssh.run_command("adb shell echo ok", timeout=10)
        if test_code == 0 and "ok" in test_out:
            self.log(f"[OK] {header_msg}Thiết bị đã sẵn sàng thực thi lệnh qua ADB.", "SUCCESS")
        else:
            time.sleep(3)

        return True

    def _wait_for_fastboot(self, timeout_sec: int = 35) -> bool:
        self.log(f"Đang chờ thiết bị chuyển sang chế độ Fastboot (tối đa {timeout_sec}s)...", "INFO")
        start = time.time()
        # Initial sleep ~5s as requested in guides
        time.sleep(5)
        while time.time() - start < timeout_sec:
            if self._abort_requested:
                return False
            code, out, _ = self.ssh.run_command("fastboot devices")
            if code == 0 and "fastboot" in out:
                self.log(f"[OK] Thiết bị đã ở Fastboot: {out.strip()}", "SUCCESS")
                return True
            time.sleep(self.timeouts.get("poll_interval_sec", 3))
        self.log("[ERROR] Hết thời gian chờ (timeout) thiết bị vào chế độ Fastboot!", "ERROR")
        return False

    def _wait_for_adb(self, initial_sleep: int = 20, timeout_sec: int = 80) -> bool:
        self.log(f"Đang chờ thiết bị khởi động lại và kết nối ADB (chờ khởi tạo {initial_sleep}s)...", "INFO")
        time.sleep(initial_sleep)
        start = time.time()
        retry_cnt = 0
        while time.time() - start < timeout_sec:
            if self._abort_requested:
                return False
            retry_cnt += 1
            code, out, _ = self.ssh.run_command("adb devices")
            if code == 0:
                lines = [l for l in out.strip().splitlines() if "\tdevice" in l]
                if lines:
                    self.log(f"[OK] Thiết bị đã kết nối ADB thành công: {lines[0]}", "SUCCESS")
                    return True
            self.log(f"Kiểm tra lại ADB (lần {retry_cnt})...", "INFO")
            time.sleep(self.timeouts.get("poll_interval_sec", 4))
        self.log("[ERROR] Hết thời gian chờ (timeout) thiết bị kết nối ADB!", "ERROR")
        return False

    # -------------------------------------------------------------
    # Step Implementations
    # -------------------------------------------------------------
    def _step_flash_sw(self, step: Dict[str, Any]) -> bool:
        workdir = step.get("workdir", "")
        script = step.get("script", "")
        if not workdir:
            self.log("[ERROR] Thư mục release không tồn tại hoặc chưa cấu hình!", "ERROR")
            return False

        # 1. Trước khi adb reboot bootloader: kiểm tra xem thiết bị đã ở fastboot chưa
        fb_code, fb_out, _ = self.ssh.run_command("fastboot devices", timeout=5)
        if fb_code == 0 and "fastboot" in fb_out:
            self.log("[OK] Thiết bị đã ở sẵn chế độ Fastboot, bỏ qua bước adb reboot bootloader.", "INFO")
        else:
            # Đảm bảo thiết bị ở trạng thái ADB ổn định trước khi reboot bootloader
            if not self._ensure_adb_ready(f"Trước khi adb reboot bootloader ({step.get('title', '')})", post_sleep=10):
                return False
            self.log("Chạy: adb reboot bootloader", "INFO")
            c1, out1, err1 = self.ssh.run_command("adb reboot bootloader")
            if c1 != 0 and "no devices" in (out1 + err1):
                self.log("Thiết bị có thể đã ở chế độ fastboot, đang kiểm tra...", "WARN")

        # 2. wait for fastboot
        if not self._wait_for_fastboot(self.timeouts.get("bootloader_wait_sec", 35)):
            return False

        # 3. run flash script
        cmd = f"cd {workdir} && chmod +x {script} && {script}"
        self.log(f"Chạy script flash: {cmd}", "INFO")
        c2, out2 = self.ssh.run_command_stream(
            cmd, 
            output_callback=lambda txt: self.log_signal.emit(txt, "STREAM"),
            check_abort=self.is_aborted
        )
        if c2 != 0:
            self.log(f"[ERROR] Script flash thất bại với mã lỗi {c2}", "ERROR")
            return False

        # 4. fastboot reboot & wait adb
        if step.get("reboot_after", True):
            self.log("Chạy: fastboot reboot", "INFO")
            self.ssh.run_command("fastboot reboot")

            # Nếu bước này cấu hình không chờ adb (vd: Flash User Build cần người dùng xác thực thủ công trên màn hình)
            if not step.get("wait_for_adb", True):
                self.log("[OK] Đã phát lệnh 'fastboot reboot' thành công. Thiết bị đang khởi động lại User Build.", "SUCCESS")
                self.log("ℹ️ Bước Flash User Build đã hoàn thành. Vui lòng chuyển sang bước tiếp theo để thực hiện xác thực thủ công trên màn hình thiết bị.", "INFO")
                time.sleep(3)
                return True

            if not self._wait_for_adb(initial_sleep=20, timeout_sec=self.timeouts.get("adb_reboot_wait_sec", 80)):
                return False
            # Sau khi vừa reboot về adb, sleep 10s để hệ thống ổn định
            self.log("Tạm dừng 10s sau khi khởi động về ADB để hệ thống ổn định hoàn toàn...", "INFO")
            for _ in range(10):
                if self._abort_requested:
                    return False
                time.sleep(1)

        return True

    def _step_run_commands(self, workdir: str, commands: List[str]) -> bool:
        if not workdir:
            self.log("[ERROR] Thư mục làm việc chưa được cấu hình!", "ERROR")
            return False

        serial = self._get_device_serial()
        if serial:
            self._device_serial = serial

        for idx, cmd_item in enumerate(commands):
            if self._abort_requested:
                return False

            actual_cmd = cmd_item

            # NẾU LÀ CHANGELANGUAGE.SH CHẠY SAU MTC (MTC hardReset làm khởi động lại Head Unit):
            if "ChangeLanguage.sh" in actual_cmd and idx > 0:
                self.log("Phát hiện ChangeLanguage sau script MTC. Đang chờ Head Unit khởi động lại từ lệnh hardReset...", "INFO")
                # Chờ 15s để thiết bị ngắt kết nối và reboot, timeout tối đa 90s để xuất hiện trong adb devices
                if not self._wait_for_adb(initial_sleep=15, timeout_sec=self.timeouts.get("adb_reboot_wait_sec", 90)):
                    return False
                # Đảm bảo ADB kết nối ổn định và phản hồi 'adb shell echo ok'
                if not self._ensure_adb_ready("Trước khi chạy ChangeLanguage", post_sleep=10):
                    return False
                # Cập nhật lại serial sau reboot nếu trước đó chưa lấy được
                serial = self._get_device_serial()
                if serial:
                    self._device_serial = serial

            if "{serial}" in actual_cmd:
                actual_cmd = actual_cmd.replace("{serial}", serial)
            elif "ChangeLanguage.sh" in actual_cmd and serial and len(actual_cmd.split()) == 1:
                actual_cmd = f"{actual_cmd} {serial}"

            # Đảm bảo quyền thực thi nếu là shell script
            script_token = actual_cmd.split()[0]
            if script_token.endswith(".sh"):
                cmd = f"cd {workdir} && chmod +x {script_token} && {actual_cmd}"
            else:
                cmd = f"cd {workdir} && {actual_cmd}"

            self.log(f"Thực thi: {cmd}", "INFO")
            code, out = self.ssh.run_command_stream(
                cmd,
                output_callback=lambda txt: self.log_signal.emit(txt, "STREAM"),
                check_abort=self.is_aborted
            )
            if code != 0:
                self.log(f"[ERROR] Lệnh '{actual_cmd}' thất bại với mã {code}", "ERROR")
                return False
                
            # Post-MTC Arduino Bypass (bản gốc: KeyBoard_Allow_Privacy x2 sau changeLanguage).
            # ChangeLanguage có thể khiến HU reboot — phải đảm bảo ADB đã về ổn định
            # trước khi gửi phím, nếu không phím sẽ "rơi vào khoảng không".
            if "ChangeLanguage.sh" in actual_cmd and self._arduino_enabled:
                if not self._ensure_adb_ready("Sau khi ChangeLanguage (thiết bị có thể đang reboot)", post_sleep=5):
                    return False
                self.log("[ARDUINO] Gửi double-click để bypass Privacy sau khi đổi ngôn ngữ...", "INFO")
                self._send_arduino(self._kb_double)
                time.sleep(5)
                self.log("[ARDUINO] Gửi double-click lần 2...", "INFO")
                self._send_arduino(self._kb_double)
                time.sleep(5)
                
        return True

    def _step_composite(self, step: Dict[str, Any]) -> bool:
        substeps = step.get("substeps", [])
        for idx, sub in enumerate(substeps):
            if self._abort_requested:
                return False
            title = sub.get('title', '')
            self.log(f"-> Chạy phân mục: {title}", "INFO")
            # Nếu là phân mục tiếp theo (như Calibration sau MTC), đảm bảo thiết bị đã về ADB ổn định
            if idx > 0:
                if not self._ensure_adb_ready(f"Trước khi chạy {title}", post_sleep=10):
                    return False
            ok = self._step_run_commands(sub.get("workdir", ""), sub.get("commands", []))
            if not ok:
                return False
        return True


    def _step_lock_bootloader(self, step: Optional[Dict[str, Any]] = None) -> bool:
        # Kiểm tra nếu thiết bị đã ở Fastboot thì không cần reboot bootloader
        fb_code, fb_out, _ = self.ssh.run_command("fastboot devices", timeout=5)
        if fb_code == 0 and "fastboot" in fb_out:
            self.log("[OK] Thiết bị đã ở sẵn chế độ Fastboot, bỏ qua bước adb reboot bootloader.", "INFO")
        else:
            if not self._ensure_adb_ready("Trước khi adb reboot bootloader (Lock Bootloader)", post_sleep=10):
                return False
            self.log("Chạy: adb reboot bootloader", "INFO")
            self.ssh.run_command("adb reboot bootloader")

        if not self._wait_for_fastboot(self.timeouts.get("bootloader_wait_sec", 35)):
            return False

        self.log("Chạy: fastboot flashing lock", "INFO")
        c, out = self.ssh.run_command_stream(
            "fastboot flashing lock",
            output_callback=lambda txt: self.log_signal.emit(txt, "STREAM"),
            check_abort=self.is_aborted
        )
        if c != 0:
            self.log("[ERROR] Lệnh 'fastboot flashing lock' thất bại!", "ERROR")
            return False

        self.log("Chạy: fastboot reboot", "INFO")
        self.ssh.run_command("fastboot reboot")

        # Nếu bước này cấu hình không chờ adb (vd: ATS/CTS có bước manual_auth_2 tiếp theo)
        if step and not step.get("wait_for_adb", True):
            self.log("[OK] Đã phát lệnh 'fastboot reboot' sau khi khóa bootloader thành công. Thiết bị đang khởi động lại.", "SUCCESS")
            self.log("ℹ️ Bước Khóa Bootloader đã hoàn thành. Vui lòng chuyển sang bước tiếp theo để thực hiện xác thực thủ công trên màn hình thiết bị.", "INFO")
            time.sleep(3)
            return True

        if not self._wait_for_adb(initial_sleep=20, timeout_sec=self.timeouts.get("adb_reboot_wait_sec", 80)):
            return False
        self.log("Tạm dừng 10s sau khi khóa bootloader và khởi động về ADB...", "INFO")
        for _ in range(10):
            if self._abort_requested:
                return False
            time.sleep(1)
        return True

    def _step_manual_auth(self, step: Dict[str, Any]) -> bool:
        prompt = step.get("prompt", "Vui lòng xác thực thủ công trên thiết bị.")
        self.log("\n" + "="*50, "WARN")
        self.log(f"[YÊU CẦU XÁC THỰC THỦ CÔNG]\n{prompt}", "WARN")
        self.log("="*50 + "\n", "WARN")

        self._auth_event.clear()
        self._auth_result = False

        if not self._device_serial:
            self._device_serial = self._get_device_serial()

        auth_data = {
            "step_idx": getattr(self, "_current_step_idx", self.single_step_idx or 0),
            "step_title": step.get("title", "Xác thực thủ công"),
            "prompt": prompt,
            "server_host": getattr(self, "server_host", "") or getattr(self.ssh, "host", ""),
            "suite_name": getattr(self, "suite_name", ""),
            "device_serial": self._device_serial
        }
        self.manual_auth_signal.emit(auth_data)

        # Wait for user click in Dialog
        self._auth_event.wait()
        if not self._auth_result or self._abort_requested:
            self.log("Người dùng đã hủy bỏ xác thực thủ công.", "WARN")
            return False
        self.log("Người dùng đã xác nhận hoàn tất thủ công thành công.", "SUCCESS")
        return True

    def _step_arduino_auth(self, step: Dict[str, Any]) -> bool:
        if not self._arduino_enabled:
            self.log("[ARDUINO] Tính năng Arduino đã bị tắt hoặc mất kết nối. Chuyển sang xác thực thủ công.", "WARN")
            step["prompt"] = "Vui lòng thực hiện thao tác xác thực trên màn hình thiết bị (Bypass thủ công)."
            return self._step_manual_auth(step)
            
        self.log(f"\n[ARDUINO] Bắt đầu xác thực tự động: {step.get('title', '')}", "INFO")
        
        max_reboot_loops = 10
        loop_count = 0
        auth_success = False

        while loop_count < max_reboot_loops and not auth_success and not self._abort_requested:
            loop_count += 1
            self.log(f"[ARDUINO] Vòng lặp kiểm tra ADB lần {loop_count}/{max_reboot_loops}", "INFO")

            # Chờ thiết bị xuất hiện ở BẤT KỲ trạng thái nào (kể cả UNAUTHORIZED —
            # chính là lúc dialog RSA đang hiện trên màn hình và cần bấm Allow).
            # LƯU Ý: không dùng _wait_for_adb() ở đây vì nó chỉ chấp nhận thiết bị
            # đã authorized, làm nhánh UNAUTHORIZED/RECOVERY bên dưới thành dead code.
            status = self._wait_for_adb_any_state(timeout_sec=80)
            if not status:
                self.log("[ARDUINO] Hết timeout chờ thiết bị xuất hiện trên ADB, sẽ thử khởi động lại qua Relay...", "WARN")
            else:
                k1_retries = 0
                while k1_retries < 5 and not self._abort_requested:
                    if status == "PASS":
                        self.log("[ARDUINO] Thiết bị đã xác thực ADB thành công (PASS).", "SUCCESS")
                        auth_success = True
                        break
                    elif status == "UNAUTHORIZED":
                        self.log(f"[ARDUINO] ADB đang báo UNAUTHORIZED (dialog RSA trên màn hình). Gửi tín hiệu {self._kb_signal} để bấm Allow (Lần {k1_retries+1}/5)...", "WARN")
                        self._send_arduino(self._kb_signal)
                        time.sleep(10)
                    elif status == "RECOVERY":
                        self.log("[ARDUINO] Thiết bị kẹt ở RECOVERY. Gửi tín hiệu triple-click để thoát...", "WARN")
                        self._send_arduino(self._kb_triple)
                        time.sleep(20)
                    else:
                        self.log("[ARDUINO] Trạng thái ADB không xác định hoặc mất kết nối, chờ 5s...", "WARN")
                        time.sleep(5)

                    k1_retries += 1
                    status = self._check_adb_status()

                if auth_success:
                    break
            
            # Nếu hết 5 lần thử K1 hoặc không thấy ADB, tiến hành reset relay
            if not auth_success and not self._abort_requested:
                if loop_count == 1:
                    self.log("[ARDUINO] Cảnh báo: Vòng lặp đầu tiên thất bại. Có thể do chưa cắm dây vào HU.", "WARN")
                    self._error_event.clear()
                    self._error_decision = StepDecision.ABORT
                    
                    orig_idx = getattr(self, "_current_step_idx", 0)
                    error_msg = ("Đã thử gửi tín hiệu K1 nhiều lần nhưng thiết bị không xác thực được.\n"
                                 "Bạn có quên cắm cáp nối từ Arduino vào cổng USB của xe không?\n\n"
                                 "- Chọn 'Thử lại' (Retry) nếu bạn đã cắm lại và muốn tiếp tục.\n"
                                 "- Chọn 'Bỏ qua' (Skip) để tự tay ấn xác thực trên màn hình xe (Xác thực thủ công).\n"
                                 "- Chọn 'Dừng' (Abort) để hủy quy trình.")
                    
                    self.step_error_signal.emit(orig_idx, "Nghi vấn quên cáp Arduino", error_msg)
                    self._error_event.wait()
                    
                    if self._abort_requested or self._error_decision == StepDecision.ABORT:
                        self.log("Người dùng đã chọn DỪNG quy trình.", "ERROR")
                        return False
                    elif self._error_decision == StepDecision.SKIP:
                        self.log("Chuyển sang chế độ xác thực thủ công.", "WARN")
                        self._arduino_enabled = False
                        step["prompt"] = "Vui lòng thực hiện thao tác xác thực trên màn hình thiết bị (Bypass thủ công)."
                        return self._step_manual_auth(step)
                    else:
                        self.log("Đã chọn Thử lại, tiến hành Reboot bằng Relay và kiểm tra lại...", "INFO")

                self.log(f"[ARDUINO] Không thể xác thực, tiến hành khởi động lại thiết bị bằng Relay ({self._rl_signal}off -> {self._rl_signal})...", "ERROR")
                self._send_arduino(self._rl_signal + "off")
                time.sleep(5)
                self._send_arduino(self._rl_signal)
                self.log(f"[ARDUINO] Đã bật lại nguồn, chờ khởi động...", "INFO")
                time.sleep(15)

        if not auth_success:
            self.log("[ERROR] [ARDUINO] Xác thực thất bại sau nhiều lần thử lại.", "ERROR")
            return False

        self.log("[ARDUINO] Đợi 30s để màn hình load hoàn chỉnh trước khi Bypass Privacy...", "INFO")
        for _ in range(30):
            if self._abort_requested:
                return False
            time.sleep(1)

        self.log("[ARDUINO] Gửi double-click lần 1 để bypass Privacy/Setup Wizard...", "INFO")
        self._send_arduino(self._kb_double)
        time.sleep(5)

        self.log("[ARDUINO] Gửi double-click lần 2...", "INFO")
        self._send_arduino(self._kb_double)
        time.sleep(5)

        # Verify: Setup Wizard đã hoàn tất chưa (user_setup_complete=1).
        # Bản gốc chỉ bấm "mù" không verify — thêm bước này để biết chắc chắn,
        # tránh chạy tiếp khi màn hình vẫn kẹt ở wizard.
        if self._verify_setup_complete(timeout_sec=60):
            self.log("[ARDUINO] Xác minh: Setup Wizard đã hoàn tất (user_setup_complete=1).", "SUCCESS")
        else:
            self.log("[ARDUINO] CẢNH BÁO: Không xác minh được Setup Wizard đã xong (timeout 60s). "
                     "Có thể wizard vẫn hiển thị — hãy kiểm tra tay trên màn hình xe.", "WARN")

        if self._ensure_adb_ready("Hoàn tất bypass Arduino", post_sleep=5):
            self.log("[ARDUINO] Gửi triple-click lần cuối đề phòng popup lạ...", "INFO")
            self._send_arduino(self._kb_triple)
            return True
        else:
            return False

    def _verify_setup_complete(self, timeout_sec: int = 60) -> bool:
        """Polls 'settings get secure user_setup_complete' until it becomes 1."""
        start = time.time()
        while time.time() - start < timeout_sec:
            if self._abort_requested:
                return False
            code, out, _ = self.ssh.run_command(
                "adb shell settings get secure user_setup_complete", timeout=10)
            if code == 0 and out.strip() == "1":
                return True
            time.sleep(5)
        return False

    def _step_precondition(self, step: Dict[str, Any]) -> bool:
        """
        Chạy Precondition cho thiết bị (port từ Precondition.sh bản gốc AutoFlashing):
        WiFi (verify ping) -> tắt lockscreen vĩnh viễn -> stay-awake -> giờ 12h -> en-US.
        Dùng chung module precondition.py với HU Settings Dialog.
        """
        from precondition import run_precondition

        if not self._ensure_adb_ready("Trước khi chạy Precondition", post_sleep=5):
            return False

        serial = self._get_device_serial()
        if not serial:
            serial = self._device_serial
        if not serial:
            self.log("[ERROR] Không xác định được serial thiết bị cho bước Precondition!", "ERROR")
            return False
        self._device_serial = serial

        # Đảm bảo setlocale.jar có trên server để push xuống thiết bị
        local_jar = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setlocale.jar")
        remote_jar = "/tmp/setlocale.jar"
        if os.path.exists(local_jar):
            ok, msg = self.ssh.upload_file(local_jar, remote_jar)
            if not ok:
                self.log(f"[Precondition] Cảnh báo upload setlocale.jar: {msg}", "WARN")
        else:
            self.log("[Precondition] Cảnh báo: không tìm thấy setlocale.jar local, bước đổi ngôn ngữ có thể bỏ qua.", "WARN")

        self.log(f"[Precondition] Bắt đầu precondition cho thiết bị {serial}...", "INFO")
        ok = run_precondition(
            self.ssh, serial,
            step.get("wifi_ssid", ""), step.get("wifi_password", ""),
            self.log, self.is_aborted,
            server_jar_path=remote_jar,
        )
        if not ok:
            self.log("[ERROR] Precondition bị hủy bởi người dùng.", "ERROR")
            return False
        return True

    def _step_flash_boot_debug(self, step: Dict[str, Any]) -> bool:
        workdir = step.get("workdir", "")
        fb_code, fb_out, _ = self.ssh.run_command("fastboot devices", timeout=5)
        if fb_code == 0 and "fastboot" in fb_out:
            self.log("[OK] Thiết bị đã ở sẵn chế độ Fastboot, bỏ qua bước adb reboot bootloader.", "INFO")
        else:
            if not self._ensure_adb_ready("Trước khi adb reboot bootloader (Flash Boot-Debug)", post_sleep=10):
                return False
            self.log("Chạy: adb reboot bootloader", "INFO")
            self.ssh.run_command("adb reboot bootloader")

        if not self._wait_for_fastboot(self.timeouts.get("bootloader_wait_sec", 35)):
            return False

        cmd = f"cd {workdir} && fastboot flash boot_a boot-debug.img && fastboot flash boot_b boot-debug.img && fastboot reboot"
        self.log(f"Chạy flash boot-debug: {cmd}", "INFO")
        c, out = self.ssh.run_command_stream(
            cmd,
            output_callback=lambda txt: self.log_signal.emit(txt, "STREAM"),
            check_abort=self.is_aborted
        )
        if c != 0:
            self.log("[ERROR] Flash boot-debug.img thất bại!", "ERROR")
            return False

        if not self._wait_for_adb(initial_sleep=20, timeout_sec=self.timeouts.get("adb_reboot_wait_sec", 80)):
            return False
        self.log("Tạm dừng 10s sau khi khởi động về ADB...", "INFO")
        for _ in range(10):
            if self._abort_requested:
                return False
            time.sleep(1)
        return True

    def _step_flash_system_gsi(self, step: Dict[str, Any]) -> bool:
        workdir = step.get("workdir", "")
        fb_code, fb_out, _ = self.ssh.run_command("fastboot devices", timeout=5)
        if fb_code == 0 and "fastboot" in fb_out:
            self.log("[OK] Thiết bị đã ở sẵn chế độ Fastboot/Fastbootd.", "INFO")
        else:
            if not self._ensure_adb_ready("Trước khi adb reboot fastboot (Flash GSI System)", post_sleep=10):
                return False
            self.log("Chạy: adb reboot fastboot (vào fastbootd)", "INFO")
            self.ssh.run_command("adb reboot fastboot")

        if not self._wait_for_fastboot(self.timeouts.get("fastbootd_wait_sec", 45)):
            return False

        cmd = f"cd {workdir} && fastboot erase system_a && fastboot flash -S 250M system_a system.img && fastboot reboot"
        self.log(f"Chạy flash system.img: {cmd}", "INFO")
        c, out = self.ssh.run_command_stream(
            cmd,
            output_callback=lambda txt: self.log_signal.emit(txt, "STREAM"),
            check_abort=self.is_aborted
        )
        if c != 0:
            self.log("[ERROR] Flash system.img thất bại!", "ERROR")
            return False

        if not self._wait_for_adb(initial_sleep=20, timeout_sec=self.timeouts.get("adb_reboot_wait_sec", 80)):
            return False
        self.log("Tạm dừng 10s sau khi khởi động về ADB...", "INFO")
        for _ in range(10):
            if self._abort_requested:
                return False
            time.sleep(1)
        return True

    def _step_flash_boot_orig(self, step: Dict[str, Any]) -> bool:
        workdir = step.get("workdir", "")
        fb_code, fb_out, _ = self.ssh.run_command("fastboot devices", timeout=5)
        if fb_code == 0 and "fastboot" in fb_out:
            self.log("[OK] Thiết bị đã ở sẵn chế độ Fastboot, bỏ qua bước adb reboot bootloader.", "INFO")
        else:
            if not self._ensure_adb_ready("Trước khi adb reboot bootloader (Flash Boot Orig)", post_sleep=10):
                return False
            self.log("Chạy: adb reboot bootloader", "INFO")
            self.ssh.run_command("adb reboot bootloader")

        if not self._wait_for_fastboot(self.timeouts.get("bootloader_wait_sec", 35)):
            return False

        cmd = f"cd {workdir} && fastboot flash boot_a boot.img && fastboot flash boot_b boot.img && fastboot reboot"
        self.log(f"Chạy flash lại boot.img gốc: {cmd}", "INFO")
        c, out = self.ssh.run_command_stream(
            cmd,
            output_callback=lambda txt: self.log_signal.emit(txt, "STREAM"),
            check_abort=self.is_aborted
        )
        if c != 0:
            self.log("[ERROR] Flash boot.img thất bại!", "ERROR")
            return False

        if not self._wait_for_adb(initial_sleep=20, timeout_sec=self.timeouts.get("adb_reboot_wait_sec", 80)):
            return False
        self.log("Tạm dừng 10s sau khi khởi động về ADB...", "INFO")
        for _ in range(10):
            if self._abort_requested:
                return False
            time.sleep(1)
        return True

