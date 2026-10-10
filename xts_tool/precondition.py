"""
Precondition (HU basic setup) — ported from AutoFlashing Precondition.sh.

Original script (bash) did, in order:
  1. Install wifi.apk + change-language apks
  2. Connect WiFi via adbjoinwifi app, retry up to 10x, verified with `ping -c1 www.google.com`
  3. BACK x2, HOME keyevents to dismiss foreground apps
  4. Disable lockscreen persistently (`lock_screen_lock_none=true`), 3x retry with read-back verify
  5. Stay awake (`stay_on_while_plugged_in=7`), 3x retry with verify
  6. Time format 12h, 3x retry with verify
  7. Change language to en-US via instrumented test, verified with `persist.sys.locale`
  8. Uninstall helper apks (zero footprint)

This Python port keeps the same order and the retry-with-verify pattern (the key
reason the original was more reliable in real runs), with two adaptations:
  - WiFi uses `cmd -w wifi connect-network` (no helper apk needed on server)
    but keeps the ping-verification retry loop from the original.
  - Language uses the repo's zero-footprint setlocale.jar approach, with
    `persist.sys.locale` verification added.

  NOTE: the original script had a typo: `stay_on_while_pulgged_in`. The typo is
  intentionally NOT ported — the correct key `stay_on_while_plugged_in` is used.

Best-effort semantics (same as the original script): individual items log WARN on
failure but the function only returns False when aborted by the user.
"""

import time
from typing import Callable, Optional


def _set_with_verify(ssh, serial: str, namespace: str, key: str, value: str,
                     log: Callable[[str, str], None],
                     is_aborted: Callable[[], bool],
                     retries: int = 3) -> bool:
    """settings put + read-back verify, ported from Precondition.sh retry loops."""
    for attempt in range(1, retries + 1):
        if is_aborted():
            return False
        ssh.run_command(
            f"adb -s {serial} shell settings put {namespace} {key} {value}",
            timeout=15,
        )
        time.sleep(1)
        _, out, _ = ssh.run_command(
            f"adb -s {serial} shell settings get {namespace} {key}",
            timeout=15,
        )
        if out.strip() == value:
            log(f"[Precondition] {namespace}/{key} = {value} (OK, lần {attempt}).", "SUCCESS")
            return True
        log(f"[Precondition] {namespace}/{key} chưa nhận giá trị (lần {attempt}/{retries}), thử lại...", "WARN")
    log(f"[Precondition] CẢNH BÁO: Không set được {namespace}/{key}={value} sau {retries} lần.", "WARN")
    return False


def run_precondition(ssh, serial: str, wifi_ssid: str, wifi_password: str,
                     log: Callable[[str, str], None],
                     is_aborted: Optional[Callable[[], bool]] = None,
                     server_jar_path: str = "/tmp/setlocale.jar",
                     progress_cb: Optional[Callable[[str], None]] = None) -> bool:
    """
    Runs the full precondition sequence on one device.

    ssh: SSHManager-like object exposing run_command(cmd, timeout) -> (code, out, err).
    serial: adb serial of the target device.
    log: callable(text, level).
    is_aborted: optional callable() -> bool.
    server_jar_path: setlocale.jar location ON THE SERVER (uploaded beforehand).
    progress_cb: optional callable(desc) invoked at each sub-step (for dialogs).
    """
    def aborted() -> bool:
        return bool(is_aborted and is_aborted())

    def step(desc: str):
        log(f"[Precondition] {desc}", "INFO")
        if progress_cb:
            progress_cb(desc)

    def adb_shell(cmd: str, timeout: int = 30):
        code, out, _ = ssh.run_command(f"adb -s {serial} shell {cmd}", timeout=timeout)
        return code, out.strip()

    # ---------------------------------------------------------------- 1. WiFi
    step(f"Bật WiFi và kết nối mạng '{wifi_ssid}'...")
    ssh.run_command(f"adb -s {serial} shell cmd -w wifi set-wifi-enabled enabled", timeout=15)
    if wifi_ssid:
        ssh.run_command(
            f'adb -s {serial} shell cmd -w wifi connect-network "{wifi_ssid}" wpa2 "{wifi_password}"',
            timeout=30,
        )

    # Verify loop ported from Precondition.sh (ping www.google.com, up to 10 tries)
    wifi_ok = False
    for attempt in range(1, 11):
        if aborted():
            return False
        code, out = adb_shell("ping -c1 www.google.com", timeout=20)
        if code == 0 and ("1 received" in out or "bytes from" in out):
            wifi_ok = True
            log(f"[Precondition] WiFi đã có mạng (ping OK, lần {attempt}).", "SUCCESS")
            break
        log(f"[Precondition] Chưa có mạng (lần {attempt}/10), thử kết nối lại WiFi...", "WARN")
        if wifi_ssid:
            ssh.run_command(
                f'adb -s {serial} shell cmd -w wifi connect-network "{wifi_ssid}" wpa2 "{wifi_password}"',
                timeout=30,
            )
        time.sleep(5)
    if not wifi_ok:
        log("[Precondition] CẢNH BÁO: Không xác minh được mạng WiFi sau 10 lần thử. "
            "Tiếp tục các bước còn lại.", "WARN")

    # ------------------------------------------------- 2. Dismiss foreground app
    step("Thoát app nền (BACK x2, HOME)...")
    adb_shell("input keyevent 4")
    adb_shell("input keyevent 4")
    adb_shell("input keyevent 3")

    # ------------------------------------------------- 3. Lockscreen: none (persistent)
    # Bản gốc: settings put secure lock_screen_lock_none true (verify 3 lần).
    # Khác với `wm dismiss-keyguard` (chỉ tắt tạm thời, reboot là hiện lại).
    step("Tắt lockscreen vĩnh viễn (lock_screen_lock_none)...")
    _set_with_verify(ssh, serial, "secure", "lock_screen_lock_none", "true", log, aborted)

    # ------------------------------------------------- 4. Stay awake
    step("Bật Stay Awake (màn hình luôn sáng khi cắm nguồn)...")
    adb_shell("svc power stayon true")
    _set_with_verify(ssh, serial, "global", "stay_on_while_plugged_in", "7", log, aborted)

    # ------------------------------------------------- 5. Time format 12h
    step("Đặt định dạng giờ 12h...")
    _set_with_verify(ssh, serial, "system", "time_12_24", "12", log, aborted)

    # ------------------------------------------------- 6. Language en-US (zero-footprint)
    step("Đổi ngôn ngữ sang en-US (setlocale.jar, zero-footprint)...")
    lang_ok = False
    for attempt in range(1, 3):
        if aborted():
            return False
        code, _, _ = ssh.run_command(
            f"adb -s {serial} push {server_jar_path} /data/local/tmp/setlocale.jar",
            timeout=30,
        )
        if code != 0:
            log(f"[Precondition] Không push được setlocale.jar lên thiết bị (lần {attempt}).", "WARN")
            time.sleep(3)
            continue
        ssh.run_command(
            'adb -s {} shell "CLASSPATH=/data/local/tmp/setlocale.jar '
            'app_process /data/local/tmp com.setlocale.SetLocale en-US"'.format(serial),
            timeout=30,
        )
        ssh.run_command(f"adb -s {serial} shell rm -f /data/local/tmp/setlocale.jar", timeout=15)
        _, locale, _ = ssh.run_command(
            f"adb -s {serial} shell getprop persist.sys.locale", timeout=15)
        if locale.strip() == "en-US":
            lang_ok = True
            log("[Precondition] Ngôn ngữ đã là en-US (đã dọn file tạm trên thiết bị).", "SUCCESS")
            break
        log(f"[Precondition] Ngôn ngữ chưa phải en-US (lần {attempt}/2), thử lại...", "WARN")
        time.sleep(3)
    if not lang_ok:
        log("[Precondition] CẢNH BÁO: Không đổi được ngôn ngữ sang en-US.", "WARN")

    # ------------------------------------------------- 7. Dismiss keyguard (transient, best effort)
    adb_shell("wm dismiss-keyguard")

    log("[Precondition] Hoàn tất precondition cho thiết bị " + serial, "SUCCESS")
    return True
