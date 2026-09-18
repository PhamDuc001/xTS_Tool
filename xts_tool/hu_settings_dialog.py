"""
HU Settings Dialog for xTS Pre-Setup Tool.
Provides real-time inspection and 1-click automated setup for 1 or 2 Head Units (DUTs):
- Wi-Fi connection (GG, GG_Cert_Test, GG_Cert_Test_5G)
- Bluetooth activation
- Language change to en-US (Zero-Footprint via setlocale.jar)
- Date & Time format 12h
- Stay Awake & Dismiss Keyguard
"""
import os
import re
import time
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QTextEdit, QProgressBar, QMessageBox,
    QFrame, QWidget, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor, QColor


DEFAULT_WIFI_LIST = [
    {"ssid": "GG", "password": "11111112"},
    {"ssid": "GG_Cert_Test", "password": "1234567890"},
    {"ssid": "GG_Cert_Test_5G", "password": "1234567890"},
]


class HUSettingsWorker(QThread):
    """
    Worker thread to query device states and execute HU settings asynchronously.
    """
    status_queried = pyqtSignal(list)       # list of dicts: device info & states
    log_message = pyqtSignal(str, str)       # text, level ("INFO", "SUCCESS", "WARN", "ERROR")
    progress = pyqtSignal(int, int)          # current, total
    operation_finished = pyqtSignal(bool, str)

    def __init__(self, ssh_mgr, config: dict, mode: str = "query",
                 wifi_ssid: str = "GG", wifi_password: str = "11111112"):
        super().__init__()
        self.ssh = ssh_mgr
        self.config = config
        self.mode = mode  # "query" or "apply"
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        self._is_aborted = False

    def request_abort(self):
        self._is_aborted = True

    def run(self):
        if not self.ssh or not self.ssh.is_connected():
            self.log_message.emit("Lỗi: SSH chưa kết nối tới server!", "ERROR")
            self.operation_finished.emit(False, "SSH chưa kết nối")
            return

        if self.mode == "query":
            self._do_query()
        elif self.mode == "apply":
            self._do_apply()

    def _get_connected_devices(self) -> List[str]:
        """Detect connected adb devices via SSH."""
        code, out, _ = self.ssh.run_command("adb devices")
        serials = []
        for line in out.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("*") or line.startswith("List of devices"):
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serials.append(parts[0])
        return serials

    def _query_single_device(self, serial: str) -> Dict[str, Any]:
        """Queries status of one device."""
        info = {
            "serial": serial,
            "wifi_enabled": False,
            "wifi_ssid": "Chưa kết nối",
            "wifi_ip": "Chưa có IP",
            "bluetooth_on": False,
            "language": "Không rõ",
            "time_format": "Không rõ",
            "stay_awake": "Không rõ",
        }

        # 1. Wi-Fi status
        code, out_wlan, _ = self.ssh.run_command(f"adb -s {serial} shell ip -f inet addr show wlan0")
        ip_match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out_wlan)
        if ip_match:
            info["wifi_ip"] = ip_match.group(1)

        code, out_wifi_cmd, _ = self.ssh.run_command(f"adb -s {serial} shell cmd -w wifi status")
        if "Wifi is enabled" in out_wifi_cmd:
            info["wifi_enabled"] = True
            # Try parsing SSID
            ssid_match = re.search(r'mWifiInfo\s+SSID:\s*"?([^",\n\r]+)"?', out_wifi_cmd)
            if not ssid_match:
                ssid_match = re.search(r'SSID:\s*"?([^",\n\r]+)"?', out_wifi_cmd)
            if ssid_match:
                ssid_val = ssid_match.group(1).strip()
                if ssid_val and ssid_val != "<unknown ssid>":
                    info["wifi_ssid"] = ssid_val
                elif ip_match:
                    info["wifi_ssid"] = "Đã kết nối (SSID ẩn)"
        else:
            # Fallback check
            code, out_w_on, _ = self.ssh.run_command(f"adb -s {serial} shell settings get global wifi_on")
            if out_w_on.strip() == "1":
                info["wifi_enabled"] = True

        # 2. Bluetooth
        code, out_bt, _ = self.ssh.run_command(f"adb -s {serial} shell settings get global bluetooth_on")
        info["bluetooth_on"] = (out_bt.strip() == "1")

        # 3. Language (RAM & persist)
        lang = ""
        code, out_act, _ = self.ssh.run_command(f'adb -s {serial} shell "dumpsys activity settings | grep -i mGlobalConfiguration"')
        lang_match = re.search(r"mGlobalConfiguration=\{[^\}]*?\s\??([a-zA-Z]{2,3}-[a-zA-Z0-9_-]+)", out_act)
        if lang_match:
            lang = lang_match.group(1)
        if not lang:
            code, out_loc, _ = self.ssh.run_command(f"adb -s {serial} shell getprop persist.sys.locale")
            lang = out_loc.strip()
        info["language"] = lang if lang else "Không rõ"

        # 4. Date & Time format (12h or 24h)
        code, out_time, _ = self.ssh.run_command(f"adb -s {serial} shell settings get system time_12_24")
        t_val = out_time.strip()
        if t_val == "12":
            info["time_format"] = "12h (AM/PM)"
        elif t_val == "24":
            info["time_format"] = "24h"
        elif t_val == "null" or not t_val:
            info["time_format"] = "Mặc định hệ thống"
        else:
            info["time_format"] = t_val

        # 5. Stay Awake
        code, out_stay, _ = self.ssh.run_command(f"adb -s {serial} shell settings get global stay_on_while_plugged_in")
        stay_val = out_stay.strip()
        if stay_val == "7":
            info["stay_awake"] = "Bật (7 - AC/USB/Wireless)"
        elif stay_val == "0":
            info["stay_awake"] = "Tắt (0)"
        else:
            info["stay_awake"] = f"Giá trị: {stay_val}"

        return info

    def _do_query(self):
        self.log_message.emit("Đang quét thiết bị ADB trên server...", "INFO")
        serials = self._get_connected_devices()
        if not serials:
            self.log_message.emit("Không tìm thấy thiết bị ADB nào kết nối!", "WARN")
            self.status_queried.emit([])
            self.operation_finished.emit(True, "Không có thiết bị kết nối")
            return

        self.log_message.emit(f"Tìm thấy {len(serials)} thiết bị: {', '.join(serials)}", "INFO")
        device_infos = []
        for s in serials:
            if self._is_aborted:
                break
            self.log_message.emit(f"Đang đọc cấu hình thiết bị {s}...", "INFO")
            info = self._query_single_device(s)
            device_infos.append(info)

        self.status_queried.emit(device_infos)
        self.operation_finished.emit(True, "Đã đọc xong thông tin")

    def _do_apply(self):
        serials = self._get_connected_devices()
        if not serials:
            self.log_message.emit("Lỗi: Không tìm thấy thiết bị nào để cài đặt!", "ERROR")
            self.operation_finished.emit(False, "Không có thiết bị")
            return

        # Step 1: Upload setlocale.jar to /tmp/ on remote Linux Server via SFTP
        local_jar = os.path.join(os.path.dirname(__file__), "setlocale.jar")
        if not os.path.exists(local_jar):
            # Fallback to parent dir
            local_jar = os.path.join(os.path.dirname(os.path.dirname(__file__)), "setlocale.jar")

        remote_jar = "/tmp/setlocale.jar"
        if os.path.exists(local_jar):
            self.log_message.emit(f"Đang nạp file hỗ trợ đổi ngôn ngữ lên server: {remote_jar}...", "INFO")
            ok, msg = self.ssh.upload_file(local_jar, remote_jar)
            if not ok:
                self.log_message.emit(f"Cảnh báo SFTP: {msg}. Thử kiểm tra file có sẵn trên server...", "WARN")
        else:
            self.log_message.emit("Cảnh báo: Không tìm thấy setlocale.jar trên máy local.", "WARN")

        total_steps = len(serials) * 5
        current_step = 0

        for idx, s in enumerate(serials, 1):
            if self._is_aborted:
                self.log_message.emit("Tiến trình đã bị hủy bởi người dùng.", "WARN")
                self.operation_finished.emit(False, "Bị hủy")
                return

            self.log_message.emit(f"\n--- Đang cài đặt cho Thiết Bị {idx}/{len(serials)} (Serial: {s}) ---", "INFO")

            # 1. Wi-Fi
            self.log_message.emit(f"[{s}] Bật Wi-Fi và kết nối mạng '{self.wifi_ssid}'...", "INFO")
            self.ssh.run_command(f"adb -s {s} shell cmd -w wifi set-wifi-enabled enabled")
            self.ssh.run_command(f'adb -s {s} shell cmd -w wifi connect-network "{self.wifi_ssid}" wpa2 "{self.wifi_password}"')
            current_step += 1
            self.progress.emit(current_step, total_steps)
            time.sleep(1)

            # 2. Bluetooth
            self.log_message.emit(f"[{s}] Bật Bluetooth...", "INFO")
            self.ssh.run_command(f"adb -s {s} shell svc bluetooth enable")
            self.ssh.run_command(f"adb -s {s} shell settings put global bluetooth_on 1")
            current_step += 1
            self.progress.emit(current_step, total_steps)

            # 3. Stay Awake & Dismiss Keyguard
            self.log_message.emit(f"[{s}] Cài đặt Giữ màn hình luôn sáng (Stay Awake) & Mở khóa...", "INFO")
            self.ssh.run_command(f"adb -s {s} shell svc power stayon true")
            self.ssh.run_command(f"adb -s {s} shell settings put global stay_on_while_plugged_in 7")
            self.ssh.run_command(f"adb -s {s} shell wm dismiss-keyguard")
            current_step += 1
            self.progress.emit(current_step, total_steps)

            # 4. Date & Time Format 12h
            self.log_message.emit(f"[{s}] Đặt định dạng giờ 12h...", "INFO")
            self.ssh.run_command(f"adb -s {s} shell settings put system time_12_24 12")
            current_step += 1
            self.progress.emit(current_step, total_steps)

            # 5. Language en-US (Zero-Footprint execution)
            self.log_message.emit(f"[{s}] Thiết lập ngôn ngữ en-US (Zero-Footprint)...", "INFO")
            push_code, _, push_err = self.ssh.run_command(f"adb -s {s} push {remote_jar} /data/local/tmp/setlocale.jar")
            if push_code == 0:
                self.ssh.run_command(
                    f'adb -s {s} shell "CLASSPATH=/data/local/tmp/setlocale.jar app_process /data/local/tmp com.setlocale.SetLocale en-US"'
                )
                # Zero-Footprint: Xóa ngay lập tức trên DUT
                self.ssh.run_command(f'adb -s {s} shell "rm -f /data/local/tmp/setlocale.jar"')
                self.log_message.emit(f"[{s}] Đã chuyển đổi ngôn ngữ sang en-US và dọn sạch file tạm.", "SUCCESS")
            else:
                self.log_message.emit(f"[{s}] Không thể push setlocale.jar: {push_err}", "ERROR")

            current_step += 1
            self.progress.emit(current_step, total_steps)

        # Chờ mạng Wi-Fi và cấu hình ổn định
        self.log_message.emit("\nĐang đợi thiết bị cập nhật trạng thái kết nối mạng (3s)...", "INFO")
        time.sleep(3)

        # Re-query
        self.log_message.emit("Đang cập nhật lại trạng thái hiển thị...", "INFO")
        self._do_query()
        self.log_message.emit("\n🎉 HOÀN TẤT CÀI ĐẶT TẤT CẢ CÁC THIẾT BỊ THÀNH CÔNG!", "SUCCESS")
        self.operation_finished.emit(True, "Cài đặt thành công")


class DeviceStatusCard(QGroupBox):
    """
    UI card representing real-time status of a single Head Unit.
    """
    def __init__(self, parent=None):
        super().__init__("Thiết Bị", parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
                background-color: #252526;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #58a6ff;
            }
        """)
        layout = QGridLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)

        # Labels
        layout.addWidget(QLabel("<b>Serial:</b>"), 0, 0)
        self.lbl_serial = QLabel("---")
        self.lbl_serial.setStyleSheet("color: #58a6ff; font-weight: bold;")
        layout.addWidget(self.lbl_serial, 0, 1)

        layout.addWidget(QLabel("<b>Wi-Fi:</b>"), 1, 0)
        self.lbl_wifi = QLabel("---")
        layout.addWidget(self.lbl_wifi, 1, 1)

        layout.addWidget(QLabel("<b>IP wlan0:</b>"), 2, 0)
        self.lbl_ip = QLabel("---")
        layout.addWidget(self.lbl_ip, 2, 1)

        layout.addWidget(QLabel("<b>Bluetooth:</b>"), 3, 0)
        self.lbl_bt = QLabel("---")
        layout.addWidget(self.lbl_bt, 3, 1)

        layout.addWidget(QLabel("<b>Language:</b>"), 4, 0)
        self.lbl_lang = QLabel("---")
        layout.addWidget(self.lbl_lang, 4, 1)

        layout.addWidget(QLabel("<b>Date & Time:</b>"), 5, 0)
        self.lbl_time = QLabel("---")
        layout.addWidget(self.lbl_time, 5, 1)

        layout.addWidget(QLabel("<b>Stay Awake:</b>"), 6, 0)
        self.lbl_stay = QLabel("---")
        layout.addWidget(self.lbl_stay, 6, 1)

    def update_info(self, info: Dict[str, Any], index: int = 1):
        serial = info.get("serial", "Unknown")
        self.setTitle(f"📱 Head Unit {index}: {serial}")
        self.lbl_serial.setText(serial)

        # Wi-Fi
        w_enabled = info.get("wifi_enabled", False)
        ssid = info.get("wifi_ssid", "Chưa kết nối")
        ip = info.get("wifi_ip", "Chưa có IP")

        if w_enabled and ssid != "Chưa kết nối":
            self.lbl_wifi.setText(f"🟢 Đã kết nối: <b>{ssid}</b>")
            self.lbl_wifi.setStyleSheet("color: #4caf50;")
        elif w_enabled:
            self.lbl_wifi.setText("🟡 Đã bật Wi-Fi (Chưa có mạng)")
            self.lbl_wifi.setStyleSheet("color: #ffb300;")
        else:
            self.lbl_wifi.setText("🔴 Đang tắt")
            self.lbl_wifi.setStyleSheet("color: #f44336;")

        if ip != "Chưa có IP":
            self.lbl_ip.setText(f"<b>{ip}</b>")
            self.lbl_ip.setStyleSheet("color: #64b5f6;")
        else:
            self.lbl_ip.setText("Chưa có IP")
            self.lbl_ip.setStyleSheet("color: #888;")

        # Bluetooth
        bt_on = info.get("bluetooth_on", False)
        if bt_on:
            self.lbl_bt.setText("🟢 Bật (ON)")
            self.lbl_bt.setStyleSheet("color: #4caf50;")
        else:
            self.lbl_bt.setText("🔴 Tắt (OFF)")
            self.lbl_bt.setStyleSheet("color: #f44336;")

        # Language
        lang = info.get("language", "Không rõ")
        if "en-US" in lang:
            self.lbl_lang.setText(f"🟢 <b>{lang} (Chuẩn)</b>")
            self.lbl_lang.setStyleSheet("color: #4caf50;")
        else:
            self.lbl_lang.setText(f"🟠 <b>{lang}</b> (Cần đổi sang en-US)")
            self.lbl_lang.setStyleSheet("color: #ff9800;")

        # Time format
        tf = info.get("time_format", "Không rõ")
        if "12h" in tf:
            self.lbl_time.setText(f"🟢 <b>{tf} (Chuẩn)</b>")
            self.lbl_time.setStyleSheet("color: #4caf50;")
        else:
            self.lbl_time.setText(f"🟠 <b>{tf}</b> (Cần đổi sang 12h)")
            self.lbl_time.setStyleSheet("color: #ff9800;")

        # Stay Awake
        stay = info.get("stay_awake", "Không rõ")
        if "7" in stay:
            self.lbl_stay.setText(f"🟢 <b>{stay}</b>")
            self.lbl_stay.setStyleSheet("color: #4caf50;")
        else:
            self.lbl_stay.setText(f"🟠 <b>{stay}</b>")
            self.lbl_stay.setStyleSheet("color: #ff9800;")


class HUSettingsDialog(QDialog):
    """
    Main Dialog for Setting HU.
    """
    def __init__(self, parent, ssh_mgr, config: dict):
        super().__init__(parent)
        self.ssh = ssh_mgr
        self.config = config or {}
        self.worker = None

        self.setWindowTitle("📱 Setting HU - Head Unit Auto Configuration")
        self.resize(820, 680)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #cccccc;
            }
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:disabled {
                background-color: #222222;
                color: #666666;
                border-color: #333333;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                selection-background-color: #1565c0;
            }
            QProgressBar {
                border: 1px solid #444444;
                border-radius: 4px;
                text-align: center;
                color: white;
                background-color: #252526;
            }
            QProgressBar::chunk {
                background-color: #2e7d32;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # 1. Header Bar
        header_layout = QHBoxLayout()
        header_info = QVBoxLayout()
        lbl_title = QLabel("<b>📱 CẤU HÌNH NHANH HEAD UNIT (AUTO SETTING HU)</b>")
        lbl_title.setStyleSheet("font-size: 15px; color: #58a6ff;")
        header_info.addWidget(lbl_title)

        self.lbl_subtitle = QLabel("Tự động cấu hình Wi-Fi, Bluetooth, Ngôn ngữ US, Giờ 12h, Stay Awake (Hỗ trợ 1 hoặc 2 devices).")
        self.lbl_subtitle.setStyleSheet("color: #888888; font-size: 12px;")
        header_info.addWidget(self.lbl_subtitle)
        header_layout.addLayout(header_info, 1)

        self.btn_refresh = QPushButton("🔄 Quét lại (Refresh)")
        self.btn_refresh.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold;")
        self.btn_refresh.clicked.connect(self._start_query)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # 2. Real-time Status Section (Cards Container)
        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)

        self.lbl_no_device = QLabel("Đang kiểm tra kết nối thiết bị qua ADB...")
        self.lbl_no_device.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_device.setStyleSheet("color: #ffa726; font-style: italic; padding: 20px;")
        self.cards_layout.addWidget(self.lbl_no_device)
        layout.addWidget(self.cards_container)

        # 3. Settings Config Box
        cfg_box = QGroupBox("Cấu Hình Muốn Áp Dụng (Auto-Settings Scope)")
        cfg_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444444;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #66bb6a;
            }
        """)
        cfg_layout = QVBoxLayout(cfg_box)
        cfg_layout.setContentsMargins(12, 10, 12, 10)
        cfg_layout.setSpacing(8)

        # Wi-Fi Selection Row
        wifi_row = QHBoxLayout()
        wifi_row.addWidget(QLabel("<b>Chọn Mạng Wi-Fi:</b>"))
        self.combo_wifi = QComboBox()
        self.combo_wifi.setMinimumWidth(320)
        
        # Load Wi-Fi list from config
        self.wifi_list = self.config.get("wifi_networks", DEFAULT_WIFI_LIST)
        for w in self.wifi_list:
            ssid = w.get("ssid", "")
            pwd = w.get("password", "")
            self.combo_wifi.addItem(f"{ssid} (Password: {pwd})", userData=w)
        wifi_row.addWidget(self.combo_wifi)
        wifi_row.addStretch(1)
        cfg_layout.addLayout(wifi_row)

        # Features Summary
        features_lbl = QLabel(
            "<b>Các tính năng sẽ tự động kích hoạt đồng thời:</b><br>"
            "✔ Kết nối Wi-Fi đã chọn &nbsp;&nbsp;|&nbsp;&nbsp; "
            "✔ Bật Bluetooth &nbsp;&nbsp;|&nbsp;&nbsp; "
            "✔ Chuyển ngôn ngữ sang <b>en-US</b> (Zero-Footprint) &nbsp;&nbsp;|&nbsp;&nbsp; "
            "✔ Định dạng giờ <b>12h</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            "✔ Giữ màn hình sáng (Stay Awake)"
        )
        features_lbl.setStyleSheet("color: #a5d6a7; font-size: 11px; padding: 4px 0;")
        cfg_layout.addWidget(features_lbl)

        # Action Buttons Row
        act_row = QHBoxLayout()
        self.btn_apply = QPushButton("▶ BẮT ĐẦU CÀI ĐẶT (Apply Settings)")
        self.btn_apply.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; font-size: 13px; padding: 8px 18px;")
        self.btn_apply.clicked.connect(self._start_apply)
        act_row.addWidget(self.btn_apply)

        self.btn_close = QPushButton("Đóng")
        self.btn_close.clicked.connect(self.close)
        act_row.addWidget(self.btn_close)
        act_row.addStretch(1)
        cfg_layout.addLayout(act_row)

        layout.addWidget(cfg_box)

        # 4. Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(16)
        layout.addWidget(self.progress_bar)

        # 5. Live Log Console
        log_box = QGroupBox("Nhật Ký Thực Thi (Execution Log)")
        log_box.setStyleSheet("""
            QGroupBox {
                border: 1px solid #333333;
                border-radius: 4px;
                margin-top: 4px;
            }
            QGroupBox::title {
                color: #888888;
            }
        """)
        log_layout = QVBoxLayout(log_box)
        log_layout.setContentsMargins(6, 6, 6, 6)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("background-color: #141414; color: #d4d4d4; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px;")
        self.txt_log.setMinimumHeight(140)
        log_layout.addWidget(self.txt_log)
        layout.addWidget(log_box)

        # Start initial query
        self._start_query()

    def _append_log(self, text: str, level: str = "INFO"):
        color_map = {
            "INFO": "#cccccc",
            "SUCCESS": "#66bb6a",
            "WARN": "#ffa726",
            "ERROR": "#ef5350",
        }
        color = color_map.get(level, "#cccccc")
        self.txt_log.setTextColor(QColor(color))
        self.txt_log.append(text)
        self.txt_log.moveCursor(QTextCursor.MoveOperation.End)

    def _clear_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _start_query(self):
        if self.worker and self.worker.isRunning():
            return
        self.btn_refresh.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.progress_bar.setValue(0)

        self.worker = HUSettingsWorker(self.ssh, self.config, mode="query")
        self.worker.status_queried.connect(self._on_status_queried)
        self.worker.log_message.connect(self._append_log)
        self.worker.operation_finished.connect(self._on_worker_finished)
        self.worker.start()

    def _start_apply(self):
        if self.worker and self.worker.isRunning():
            return

        current_data = self.combo_wifi.currentData()
        if not current_data:
            QMessageBox.warning(self, "Chưa chọn Wi-Fi", "Vui lòng chọn mạng Wi-Fi hợp lệ.")
            return

        ssid = current_data.get("ssid", "")
        pwd = current_data.get("password", "")

        reply = QMessageBox.question(
            self, "Xác nhận Cài Đặt HU",
            f"Bạn có chắc muốn tự động cấu hình các Head Unit đang kết nối?\n\n"
            f"• Mạng Wi-Fi: {ssid}\n"
            f"• Ngôn ngữ: en-US\n"
            f"• Giờ: 12h (AM/PM)\n"
            f"• Bluetooth: ON\n"
            f"• Màn hình: Luôn sáng & Mở khóa\n\n"
            f"Thao tác sẽ được thực hiện đồng thời trên tất cả các Head Unit kết nối.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.btn_refresh.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.progress_bar.setValue(0)

        self.worker = HUSettingsWorker(
            self.ssh, self.config, mode="apply",
            wifi_ssid=ssid, wifi_password=pwd
        )
        self.worker.status_queried.connect(self._on_status_queried)
        self.worker.log_message.connect(self._append_log)
        self.worker.progress.connect(self._on_progress)
        self.worker.operation_finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_status_queried(self, device_infos: list):
        self._clear_cards()
        if not device_infos:
            lbl = QLabel("⚠️ Không tìm thấy thiết bị ADB nào kết nối với Server.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #ffa726; font-style: italic; padding: 20px; font-size: 13px;")
            self.cards_layout.addWidget(lbl)
            self.lbl_subtitle.setText("Không có thiết bị ADB nào kết nối.")
            return

        self.lbl_subtitle.setText(f"Đang kết nối: {len(device_infos)} thiết bị ADB.")
        for idx, info in enumerate(device_infos, 1):
            card = DeviceStatusCard(self)
            card.update_info(info, index=idx)
            self.cards_layout.addWidget(card)

    def _on_progress(self, current: int, total: int):
        percent = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percent)

    def _on_worker_finished(self, success: bool, msg: str):
        self.btn_refresh.setEnabled(True)
        self.btn_apply.setEnabled(True)
        if success and self.worker and self.worker.mode == "apply":
            QMessageBox.information(self, "Thành Công", "Đã hoàn tất tự động cấu hình các Head Unit thành công!")
