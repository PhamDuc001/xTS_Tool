"""
Workflow Runner for xTS Pre-Setup.
Manages step execution, waiting for devices (fastboot/adb), error handling, 
manual authentication prompts, and single/all step modes.
"""
import time
import threading
from typing import Dict, List, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal
from ssh_client import SSHManager


class StepDecision:
    RETRY = "RETRY"
    SKIP = "SKIP"
    ABORT = "ABORT"


def build_workflow_steps(suite_name: str, paths: Dict[str, Any]) -> List[Dict[str, Any]]:
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
    """
    suite = suite_name.upper()

    userdebug_dir = paths.get("userdebug_path", "")
    user_dir = paths.get("user_path", "")
    gkey_dir = paths.get("google_key_path", "")
    gkey_script = paths.get("google_key_script", "./addGoogle_key_Nissan_P33A.sh")
    
    mtc_dir = paths.get("mtc_path", "")
    mtc_scripts = paths.get("mtc_scripts", ["./MTC_PZ1D_26MY.sh", "./ChangeLanguage.sh"])
    
    calib_dir = paths.get("calibration_path", "")
    calib_script = paths.get("calibration_script", "./do_calibration.sh")
    
    gsi_dir = paths.get("gsi_image_path", "")

    steps = []

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
            "desc": "adb reboot bootloader -> fastboot flashing lock -> reboot"
        })
        return steps

    # For ATS, CTS, GSI, VTS: Flash User Build
    steps.append({
        "id": "flash_user",
        "title": "4. Flash User Build",
        "type": "flash_sw",
        "workdir": user_dir,
        "script": "./fastboot_n_fullnavi_reflash.sh",
        "reboot_after": True,
        "desc": "Reboot bootloader -> fastboot_n_fullnavi_reflash.sh -> reboot & chờ adb"
    })

    # Manual Authentication #1
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
            "desc": "adb reboot bootloader -> fastboot flashing lock -> reboot"
        })
        steps.append({
            "id": "manual_auth_2",
            "title": "7. Xác thực lại thủ công (Post-lock Authentication)",
            "type": "manual_auth",
            "prompt": "Đã khóa Bootloader thành công.\nVui lòng thực hiện xác thực thủ công lại trên màn hình thiết bị lần cuối.",
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

    return steps


class WorkflowWorker(QThread):
    # Signals
    log_signal = pyqtSignal(str, str)  # (text, level: 'INFO', 'WARN', 'ERROR', 'SUCCESS', 'STREAM')
    step_started_signal = pyqtSignal(int, str)  # (step_idx, step_title)
    step_finished_signal = pyqtSignal(int, str, bool)  # (step_idx, step_title, success)
    workflow_finished_signal = pyqtSignal(bool, str)  # (overall_success, summary)
    progress_signal = pyqtSignal(int, int)  # (current, total)
    
    # Interactive signals
    manual_auth_signal = pyqtSignal(int, str)  # (step_idx, message)
    step_error_signal = pyqtSignal(int, str, str)  # (step_idx, step_title, error_message)

    def __init__(self, ssh_mgr: SSHManager, steps: List[Dict[str, Any]], 
                 single_step_idx: Optional[int] = None, timeouts: Optional[Dict[str, int]] = None):
        super().__init__()
        self.ssh = ssh_mgr
        self.steps = steps
        self.single_step_idx = single_step_idx
        self.timeouts = timeouts or {
            "bootloader_wait_sec": 30,
            "adb_reboot_wait_sec": 80,
            "fastbootd_wait_sec": 45,
            "poll_interval_sec": 3
        }

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
        
        if stype == "flash_sw":
            return self._step_flash_sw(step)
        elif stype == "run_commands":
            return self._step_run_commands(step.get("workdir", ""), step.get("commands", []))
        elif stype == "composite":
            return self._step_composite(step)
        elif stype == "lock_bootloader":
            return self._step_lock_bootloader()
        elif stype == "manual_auth":
            return self._step_manual_auth(step)
        elif stype == "flash_boot_debug":
            return self._step_flash_boot_debug(step)
        elif stype == "flash_system_gsi":
            return self._step_flash_system_gsi(step)
        elif stype == "flash_boot_orig":
            return self._step_flash_boot_orig(step)
        else:
            self.log(f"Không nhận diện được loại bước: {stype}", "ERROR")
            return False

    # -------------------------------------------------------------
    # Device Wait Helpers
    # -------------------------------------------------------------
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

        # 1. adb reboot bootloader
        self.log("Chạy: adb reboot bootloader", "INFO")
        c1, out1, err1 = self.ssh.run_command("adb reboot bootloader")
        if c1 != 0 and "no devices" in (out1 + err1):
            # Maybe device is already in fastboot?
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
            if not self._wait_for_adb(initial_sleep=20, timeout_sec=self.timeouts.get("adb_reboot_wait_sec", 80)):
                return False

        return True

    def _step_run_commands(self, workdir: str, commands: List[str]) -> bool:
        if not workdir:
            self.log("[ERROR] Thư mục làm việc chưa được cấu hình!", "ERROR")
            return False

        for cmd_item in commands:
            if self._abort_requested:
                return False
            cmd = f"cd {workdir} && {cmd_item}"
            self.log(f"Thực thi: {cmd}", "INFO")
            code, out = self.ssh.run_command_stream(
                cmd,
                output_callback=lambda txt: self.log_signal.emit(txt, "STREAM"),
                check_abort=self.is_aborted
            )
            if code != 0:
                self.log(f"[ERROR] Lệnh '{cmd_item}' thất bại với mã {code}", "ERROR")
                return False
        return True

    def _step_composite(self, step: Dict[str, Any]) -> bool:
        substeps = step.get("substeps", [])
        for sub in substeps:
            if self._abort_requested:
                return False
            self.log(f"-> Chạy phân mục: {sub.get('title', '')}", "INFO")
            ok = self._step_run_commands(sub.get("workdir", ""), sub.get("commands", []))
            if not ok:
                return False
        return True

    def _step_lock_bootloader(self) -> bool:
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
        return self._wait_for_adb(initial_sleep=20, timeout_sec=self.timeouts.get("adb_reboot_wait_sec", 80))

    def _step_manual_auth(self, step: Dict[str, Any]) -> bool:
        prompt = step.get("prompt", "Vui lòng xác thực thủ công trên thiết bị.")
        self.log("\n" + "="*50, "WARN")
        self.log(f"[YÊU CẦU XÁC THỰC THỦ CÔNG]\n{prompt}", "WARN")
        self.log("="*50 + "\n", "WARN")

        self._auth_event.clear()
        self._auth_result = False
        self.manual_auth_signal.emit(self.single_step_idx or 0, prompt)

        # Wait for user click in Dialog
        self._auth_event.wait()
        if not self._auth_result or self._abort_requested:
            self.log("Người dùng đã hủy bỏ xác thực thủ công.", "WARN")
            return False
        self.log("Người dùng đã xác nhận hoàn tất thủ công thành công.", "SUCCESS")
        return True

    def _step_flash_boot_debug(self, step: Dict[str, Any]) -> bool:
        workdir = step.get("workdir", "")
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

        return self._wait_for_adb(initial_sleep=20, timeout_sec=self.timeouts.get("adb_reboot_wait_sec", 80))

    def _step_flash_system_gsi(self, step: Dict[str, Any]) -> bool:
        workdir = step.get("workdir", "")
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

        return self._wait_for_adb(initial_sleep=20, timeout_sec=self.timeouts.get("adb_reboot_wait_sec", 80))

    def _step_flash_boot_orig(self, step: Dict[str, Any]) -> bool:
        workdir = step.get("workdir", "")
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

        return self._wait_for_adb(initial_sleep=20, timeout_sec=self.timeouts.get("adb_reboot_wait_sec", 80))
