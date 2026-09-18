"""
Server Tab Widget for xTS Pre-Setup & Report Organizer Tool.
Represents one remote Ubuntu server connection with its own SSH session,
device checker, path resolver, step table, controls, report organizer, and real-time log viewer.
"""
import os
import re
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QProgressBar, QGroupBox, QMessageBox, QFileDialog, QSplitter,
    QTabWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor, QTextCharFormat, QFont

from ssh_client import SSHManager
from workflow_runner import WorkflowWorker, build_workflow_steps, StepDecision
from confirm_paths_dialog import ConfirmPathsDialog, ManualAuthDialog, ErrorDecisionDialog
from hu_settings_dialog import HUSettingsDialog
from report_collector import ReportOrganizeWorker
from generate_report_tab import GenerateReportTab

ANSI_REGEX = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')



class ServerTab(QWidget):
    tab_title_changed = pyqtSignal(str)

    def __init__(self, parent=None, config=None, default_server_info=None):
        super().__init__(parent)
        self.config = config or {}
        self.ssh = SSHManager()
        self.worker = None
        self.report_worker = None
        self._log_need_newline = False

        # Loaded paths
        default_paths_cfg = self.config.get("default_paths", {})
        self.paths = {
            "binary_root": default_paths_cfg.get("binary_root", "/home/lge/Environment/Storage/Binary/"),
            "userdebug_path": "",
            "user_path": "",
            "google_key_path": default_paths_cfg.get("google_key", {}).get("path", "/home/lge/Environment/PreSetup/NissanEU/"),
            "google_key_script": default_paths_cfg.get("google_key", {}).get("script", "./addGoogle_key_Nissan_P33A.sh"),
            "google_key_retry_script": default_paths_cfg.get("google_key", {}).get("retry_script", './AddGoogle_key_Nissan.sh "AttestationChainTee"'),
            "mtc_path": default_paths_cfg.get("mtc_script", {}).get("path", "/home/lge/Environment/scripts/PZ1D_26MY/"),
            "mtc_scripts": default_paths_cfg.get("mtc_script", {}).get("scripts", ["./MTC_PZ1D_26MY.sh", "./ChangeLanguage.sh"]),
            "calibration_path": default_paths_cfg.get("calibration", {}).get("path", "/home/lge/Environment/scripts/PZ1D_26MY/Calibrations_aio_2026May/Calibrations/"),
            "calibration_script": default_paths_cfg.get("calibration", {}).get("script", "./do_calibration.sh"),
            "gsi_image_path": default_paths_cfg.get("gsi_image", {}).get("path", "/home/lge/Environment/GSI_IMAGE/"),
        }

        self.current_steps = []
        self._init_ui(default_server_info)

    def _init_ui(self, default_server_info):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # -------------------------------------------------------------
        # 1. Top Panel: SSH & Device Info
        # -------------------------------------------------------------
        top_group = QGroupBox("Kết nối SSH & Trạng thái Thiết bị (1 Device Only)")
        top_layout = QGridLayout(top_group)
        top_layout.setContentsMargins(8, 8, 8, 8)
        top_layout.setHorizontalSpacing(10)
        top_layout.setVerticalSpacing(6)

        default_host = default_server_info.get("host", "192.168.1.100") if default_server_info else "192.168.1.100"
        default_port = str(default_server_info.get("port", 22)) if default_server_info else "22"
        default_user = default_server_info.get("username", "lge") if default_server_info else "lge"
        default_pass = default_server_info.get("password", "") if default_server_info else ""

        # SSH Fields
        top_layout.addWidget(QLabel("Host/IP:"), 0, 0)
        self.txt_host = QLineEdit(default_host)
        self.txt_host.setPlaceholderText("IP Ubuntu Server")
        top_layout.addWidget(self.txt_host, 0, 1)

        top_layout.addWidget(QLabel("Port:"), 0, 2)
        self.txt_port = QLineEdit(default_port)
        self.txt_port.setFixedWidth(55)
        top_layout.addWidget(self.txt_port, 0, 3)

        top_layout.addWidget(QLabel("User:"), 0, 4)
        self.txt_user = QLineEdit(default_user)
        self.txt_user.setFixedWidth(80)
        top_layout.addWidget(self.txt_user, 0, 5)

        top_layout.addWidget(QLabel("Password:"), 0, 6)
        self.txt_pass = QLineEdit(default_pass)
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("Pass")
        self.txt_pass.setFixedWidth(100)
        top_layout.addWidget(self.txt_pass, 0, 7)

        self.btn_connect = QPushButton("🔌 Kết nối SSH")
        self.btn_connect.setStyleSheet("font-weight: bold; background-color: #1976d2; color: white;")
        self.btn_connect.clicked.connect(self._toggle_ssh)
        top_layout.addWidget(self.btn_connect, 0, 8)

        # Status indicator
        self.lbl_ssh_status = QLabel("⚪ Chưa kết nối")
        self.lbl_ssh_status.setStyleSheet("font-weight: bold; color: #9e9e9e;")
        top_layout.addWidget(self.lbl_ssh_status, 0, 9)

        # Device check row
        self.btn_check_device = QPushButton("📱 Kiểm tra Device (Pre-Setup)")
        self.btn_check_device.setEnabled(False)
        self.btn_check_device.clicked.connect(self._check_device_clicked)
        top_layout.addWidget(self.btn_check_device, 1, 0, 1, 2)

        self.lbl_device_status = QLabel("⚪ Thiết bị (Chỉ cần khi Pre-Setup): Chưa kiểm tra")
        self.lbl_device_status.setStyleSheet("font-weight: bold; color: #9e9e9e;")
        top_layout.addWidget(self.lbl_device_status, 1, 2, 1, 8)

        main_layout.addWidget(top_group)

        # -------------------------------------------------------------
        # 2. Main Work Area: Sub-Tabs (Pre-Setup & Report Organizer)
        # -------------------------------------------------------------
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.work_tabs = QTabWidget()
        self.work_tabs.setStyleSheet("""
            QTabBar::tab {
                font-weight: bold;
                padding: 6px 20px;
                font-size: 12px;
            }
        """)

        # -------------------------------------------------------------
        # Sub-Tab 1: Pre-Setup Workflow
        # -------------------------------------------------------------
        presetup_widget = QWidget()
        presetup_layout = QVBoxLayout(presetup_widget)
        presetup_layout.setContentsMargins(4, 6, 4, 4)
        presetup_layout.setSpacing(6)

        # Config & Suite Selection
        cfg_group = QGroupBox("Cấu hình Bài Test & Đường Dẫn Firmware")
        cfg_layout = QHBoxLayout(cfg_group)
        cfg_layout.setContentsMargins(8, 8, 8, 8)

        cfg_layout.addWidget(QLabel("<b>Chọn bài test:</b>"))
        self.combo_suite = QComboBox()
        self.combo_suite.addItems(["CTS", "CTS on GSI", "ATS", "STS", "VTS"])
        self.combo_suite.currentTextChanged.connect(self._on_suite_changed)
        self.combo_suite.setFixedWidth(130)
        cfg_layout.addWidget(self.combo_suite)

        self.btn_confirm_paths = QPushButton("📂 Xác nhận Đường Dẫn Firmware & Scripts...")
        self.btn_confirm_paths.clicked.connect(self._open_confirm_paths_dialog)
        cfg_layout.addWidget(self.btn_confirm_paths)

        self.btn_setting_hu = QPushButton("📱 Setting HU")
        self.btn_setting_hu.setStyleSheet("background-color: #1565c0; color: white; font-weight: bold; padding: 5px 12px;")
        self.btn_setting_hu.clicked.connect(self._open_setting_hu_dialog)
        cfg_layout.addWidget(self.btn_setting_hu)

        self.lbl_paths_summary = QLabel("Paths: Chưa quét thư mục")
        self.lbl_paths_summary.setStyleSheet("color: #ffa726; font-style: italic;")
        cfg_layout.addWidget(self.lbl_paths_summary, 1)

        presetup_layout.addWidget(cfg_group)

        # Controls & Progress
        ctrl_layout = QHBoxLayout()
        self.btn_run_all = QPushButton("▶ BẮT ĐẦU CHẠY TOÀN BỘ (Run All)")
        self.btn_run_all.setEnabled(False)
        self.btn_run_all.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; font-size: 13px; padding: 6px 14px;")
        self.btn_run_all.clicked.connect(self._run_all_steps)
        ctrl_layout.addWidget(self.btn_run_all)

        self.btn_abort = QPushButton("⏹ DỪNG LẠI (Stop)")
        self.btn_abort.setEnabled(False)
        self.btn_abort.setStyleSheet("background-color: #c62828; color: white; font-weight: bold; font-size: 13px; padding: 6px 14px;")
        self.btn_abort.clicked.connect(self._abort_execution)
        ctrl_layout.addWidget(self.btn_abort)

        ctrl_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setTextVisible(True)
        ctrl_layout.addWidget(self.progress_bar)

        presetup_layout.addLayout(ctrl_layout)

        # Steps Table
        self.table_steps = QTableWidget()
        self.table_steps.setColumnCount(4)
        self.table_steps.setHorizontalHeaderLabels(["Bước", "Mô tả / Lệnh", "Trạng thái", "Thao tác"])
        self.table_steps.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_steps.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_steps.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_steps.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_steps.verticalHeader().setVisible(False)
        self.table_steps.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        presetup_layout.addWidget(self.table_steps)

        self.work_tabs.addTab(presetup_widget, "⚙️ Quy Trình Pre-Setup (xTS Flash & Setup)")

        # -------------------------------------------------------------
        # Sub-Tab 2: Collect & Organize Report
        # -------------------------------------------------------------
        report_widget = QWidget()
        report_layout = QVBoxLayout(report_widget)
        report_layout.setContentsMargins(4, 6, 4, 4)
        report_layout.setSpacing(6)

        # Test Root Path selector
        troot_group = QGroupBox("Đường Dẫn Test Root & Thao Tác Collect Report")
        troot_layout = QVBoxLayout(troot_group)
        troot_layout.setContentsMargins(8, 8, 8, 8)
        troot_layout.setSpacing(6)

        lbl_note = QLabel("ℹ️ <i>Tính năng Collect Report hoạt động hoàn toàn qua SSH trên máy chủ, <b>không yêu cầu cắm thiết bị (Device)</b>.</i>")
        lbl_note.setStyleSheet("color: #64b5f6; font-size: 11px;")
        troot_layout.addWidget(lbl_note)

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("<b>Test Root Path:</b>"))
        self.txt_test_root = QLineEdit("/home/lge/GoogleQA/TestFolder/GSI_cf8886c9,d930bf76/android-cts")
        self.txt_test_root.setPlaceholderText("VD: /home/lge/GoogleQA/TestFolder/GSI_.../android-cts")
        path_row.addWidget(self.txt_test_root, 1)

        self.btn_detect_test_root = QPushButton("🔍 Dò Tìm TestFolder")
        self.btn_detect_test_root.setEnabled(False)
        self.btn_detect_test_root.clicked.connect(self._detect_test_roots_clicked)
        path_row.addWidget(self.btn_detect_test_root)

        troot_layout.addLayout(path_row)

        # Action Buttons
        btn_action_row = QHBoxLayout()
        self.btn_scan_preview = QPushButton("🔎 Quét & Phân Tích Kết Quả (Scan Preview)")
        self.btn_scan_preview.setEnabled(False)
        self.btn_scan_preview.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_scan_preview.clicked.connect(self._scan_report_preview_clicked)
        btn_action_row.addWidget(self.btn_scan_preview)

        self.btn_organize_report = QPushButton("📁 Collect Report")
        self.btn_organize_report.setEnabled(False)
        self.btn_organize_report.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; font-size: 13px; padding: 6px 16px;")
        self.btn_organize_report.clicked.connect(self._organize_report_clicked)
        btn_action_row.addWidget(self.btn_organize_report)

        btn_action_row.addStretch()

        self.lbl_report_stats = QLabel("Trạng thái: Chưa quét dữ liệu")
        self.lbl_report_stats.setStyleSheet("font-weight: bold; color: #ffa726;")
        btn_action_row.addWidget(self.lbl_report_stats)

        troot_layout.addLayout(btn_action_row)
        report_layout.addWidget(troot_group)

        # Preview Table
        self.table_report_preview = QTableWidget()
        self.table_report_preview.setColumnCount(7)
        self.table_report_preview.setHorizontalHeaderLabels([
            "Session Timestamp", "Loại", "Tên Module", "Pass / Fail", 
            "Đánh Giá", "Folder Đích trong Report", "Trạng Thái Copy"
        ])
        self.table_report_preview.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_report_preview.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_report_preview.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_report_preview.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_report_preview.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_report_preview.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table_report_preview.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table_report_preview.verticalHeader().setVisible(False)
        self.table_report_preview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        report_layout.addWidget(self.table_report_preview)

        self.work_tabs.addTab(report_widget, "📊 Collect Report")

        # -------------------------------------------------------------
        # Sub-Tab 3: Generate Google Certification Report
        # -------------------------------------------------------------
        self.generate_report_tab = GenerateReportTab(ssh_manager=self.ssh, config=self.config, parent=self)
        self.generate_report_tab.log_signal.connect(self._append_log)
        self.work_tabs.addTab(self.generate_report_tab, "📑 Generate Report")

        splitter.addWidget(self.work_tabs)

        # -------------------------------------------------------------
        # 3. Bottom Shared Area: Real-Time Log Viewer
        # -------------------------------------------------------------
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(4)

        log_bar = QHBoxLayout()
        log_bar.addWidget(QLabel("<b>Log Đầu Ra Thực Thi (Thời Gian Thực):</b>"))
        log_bar.addStretch()

        self.btn_clear_log = QPushButton("Xóa Log")
        self.btn_clear_log.clicked.connect(self._clear_log)
        log_bar.addWidget(self.btn_clear_log)

        self.btn_save_log = QPushButton("💾 Lưu File Log...")
        self.btn_save_log.clicked.connect(self._save_log)
        log_bar.addWidget(self.btn_save_log)

        log_layout.addLayout(log_bar)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet(
            "background-color: #1a1a1a; color: #e0e0e0; font-family: 'Consolas', monospace; font-size: 11px; padding: 4px;"
        )
        log_layout.addWidget(self.txt_log)

        splitter.addWidget(log_widget)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)

        main_layout.addWidget(splitter, 1)

        # Initial steps setup
        self._on_suite_changed(self.combo_suite.currentText())

    # -------------------------------------------------------------
    # SSH Connection
    # -------------------------------------------------------------
    def _toggle_ssh(self):
        if self.ssh.is_connected():
            self._disconnect_ssh()
        else:
            self._connect_ssh()

    def _connect_ssh(self):
        host = self.txt_host.text().strip()
        port_str = self.txt_port.text().strip()
        user = self.txt_user.text().strip()
        pwd = self.txt_pass.text()

        if not host:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập IP Host!")
            return
        try:
            port = int(port_str)
        except ValueError:
            port = 22

        self._append_log(f"Đang kết nối SSH tới {user}@{host}:{port}...", "INFO")
        self.btn_connect.setEnabled(False)
        self.btn_connect.setText("Đang kết nối...")

        ok, msg = self.ssh.connect(host, port, user, password=pwd)
        self.btn_connect.setEnabled(True)

        if ok:
            self._append_log(msg, "SUCCESS")
            self.lbl_ssh_status.setText("🟢 Đã kết nối")
            self.lbl_ssh_status.setStyleSheet("font-weight: bold; color: #4caf50;")
            self.btn_connect.setText("Ngắt kết nối SSH")
            self.btn_connect.setStyleSheet("background-color: #d32f2f; color: white;")
            self.btn_check_device.setEnabled(True)
            self.btn_run_all.setEnabled(True)
            self.btn_detect_test_root.setEnabled(True)
            self.btn_scan_preview.setEnabled(True)

            self.tab_title_changed.emit(f"Server {host}")

            # Auto check device and auto-detect paths in background
            self._check_device_status()
            self._auto_detect_binary_paths()
            self._auto_detect_test_root()
        else:
            self._append_log(msg, "ERROR")
            self.lbl_ssh_status.setText("🔴 Kết nối thất bại")
            self.lbl_ssh_status.setStyleSheet("font-weight: bold; color: #f44336;")
            self.btn_connect.setText("🔌 Kết nối SSH")
            self.btn_connect.setStyleSheet("font-weight: bold; background-color: #1976d2; color: white;")
            QMessageBox.critical(self, "Lỗi kết nối", msg)

    def _disconnect_ssh(self):
        if self.worker and self.worker.isRunning():
            self.worker.request_abort()
            self.worker.wait(2000)
        if self.report_worker and self.report_worker.isRunning():
            self.report_worker.request_abort()
            self.report_worker.wait(2000)
        if hasattr(self, 'generate_report_tab') and self.generate_report_tab.worker and self.generate_report_tab.worker.isRunning():
            self.generate_report_tab.worker.request_abort()
            self.generate_report_tab.worker.wait(2000)

        self.ssh.disconnect()
        self._append_log("Đã ngắt kết nối SSH.", "WARN")
        self.lbl_ssh_status.setText("⚪ Chưa kết nối")
        self.lbl_ssh_status.setStyleSheet("font-weight: bold; color: #9e9e9e;")
        self.lbl_device_status.setText("⚪ Thiết bị: Chưa kiểm tra")
        self.lbl_device_status.setStyleSheet("font-weight: bold; color: #9e9e9e;")
        self.btn_connect.setText("🔌 Kết nối SSH")
        self.btn_connect.setStyleSheet("font-weight: bold; background-color: #1976d2; color: white;")
        self.btn_check_device.setEnabled(False)
        self.btn_run_all.setEnabled(False)
        self.btn_detect_test_root.setEnabled(False)
        self.btn_scan_preview.setEnabled(False)
        self.btn_organize_report.setEnabled(False)
        self.tab_title_changed.emit("New Server")

    # -------------------------------------------------------------
    # Device Checking
    # -------------------------------------------------------------
    def _check_device_clicked(self):
        self._check_device_status(show_dialog=True)

    def _check_device_status(self, show_dialog=False) -> bool:
        if not self.ssh.is_connected():
            return False

        valid, msg, devs = self.ssh.check_devices()
        if valid:
            self.lbl_device_status.setText(f"🟢 {msg}")
            self.lbl_device_status.setStyleSheet("font-weight: bold; color: #4caf50;")
            self._append_log(f"[DEVICE CHECK] {msg}", "SUCCESS")
            if show_dialog:
                QMessageBox.information(self, "Kiểm tra thiết bị", msg)
            return True
        else:
            self.lbl_device_status.setText(f"🔴 {msg} (Chỉ cần khi Pre-Setup)")
            self.lbl_device_status.setStyleSheet("font-weight: bold; color: #ffa726;")
            self._append_log(f"[DEVICE CHECK] {msg} (Lưu ý: Chỉ bắt buộc khi chạy Pre-Setup; Collect Report không yêu cầu device)", "WARN")
            if show_dialog:
                QMessageBox.warning(
                    self, "Thông tin thiết bị",
                    f"{msg}\n\n"
                    "LƯU Ý:\n"
                    "- Yêu cầu kết nối duy nhất 1 device chỉ bắt buộc khi chạy flash/setup trong tab 'Quy Trình Pre-Setup'.\n"
                    "- Nếu bạn sử dụng tab 'Collect Report' hoặc 'Generate Report', bạn có thể tiếp tục bình thường mà không cần kết nối bất kỳ device nào."
                )
            return False

    # -------------------------------------------------------------
    # Path Detection & Configuration
    # -------------------------------------------------------------
    def _auto_detect_binary_paths(self):
        if not self.ssh.is_connected():
            return

        self._append_log("Đang quét thư mục Binary trên server để nhận diện userdebug/user build...", "INFO")
        detected = self.ssh.detect_binary_paths(self.paths["binary_root"])
        if detected.get("userdebug_path"):
            self.paths["userdebug_path"] = detected["userdebug_path"]
        if detected.get("user_path"):
            self.paths["user_path"] = detected["user_path"]

        self._update_paths_summary()
        self._rebuild_steps_table()

    def _auto_detect_test_root(self):
        if not self.ssh.is_connected():
            return
        roots = self.ssh.detect_test_roots()
        if roots:
            self.txt_test_root.setText(roots[0])
            self._append_log(f"[AUTO-DETECT] Tìm thấy TestRoot: {roots[0]}", "INFO")

    def _detect_test_roots_clicked(self):
        if not self.ssh.is_connected():
            return
        roots = self.ssh.detect_test_roots()
        if not roots:
            QMessageBox.information(self, "Dò tìm TestFolder", "Không tìm thấy thư mục android-cts/ats/vts nào trong /home/lge/GoogleQA/TestFolder/.")
            return
        if len(roots) == 1:
            self.txt_test_root.setText(roots[0])
            QMessageBox.information(self, "Đã tìm thấy TestFolder", f"Đã tự động chọn thư mục:\n{roots[0]}")
        else:
            # Pick from list
            from PyQt6.QtWidgets import QInputDialog
            chosen, ok = QInputDialog.getItem(
                self, "Chọn Thư Mục Test", "Tìm thấy nhiều thư mục TestRoot trên Server:\nVui lòng chọn một thư mục:", roots, 0, False
            )
            if ok and chosen:
                self.txt_test_root.setText(chosen)

    def _update_paths_summary(self):
        ud = os.path.basename(self.paths.get("userdebug_path", "")) or "Chưa rõ"
        u = os.path.basename(self.paths.get("user_path", "")) or "Chưa rõ"
        self.lbl_paths_summary.setText(f"Userdebug: {ud} | User: {u}")
        self.lbl_paths_summary.setStyleSheet("color: #66bb6a; font-weight: bold;" if (ud != "Chưa rõ" and u != "Chưa rõ") else "color: #ffa726;")

    def _open_confirm_paths_dialog(self):
        dlg = ConfirmPathsDialog(self, self.paths, self.ssh)
        if dlg.exec():
            self.paths = dlg.get_paths()
            self._update_paths_summary()
            self._rebuild_steps_table()
            self._append_log("Đã cập nhật cấu hình đường dẫn thành công.", "SUCCESS")

    def _open_setting_hu_dialog(self):
        if not self.ssh.is_connected():
            QMessageBox.warning(self, "Chưa kết nối SSH", "Vui lòng kết nối SSH tới server trước khi Setting HU.")
            return
        dlg = HUSettingsDialog(self, self.ssh, self.config)
        dlg.exec()

    # -------------------------------------------------------------
    # Pre-Setup Steps Table & Suite Selection
    # -------------------------------------------------------------
    def _on_suite_changed(self, suite_name: str):
        self.current_steps = build_workflow_steps(suite_name, self.paths)
        self._rebuild_steps_table()

    def _rebuild_steps_table(self):
        suite = self.combo_suite.currentText()
        self.current_steps = build_workflow_steps(suite, self.paths)

        self.table_steps.setRowCount(len(self.current_steps))
        for row, step in enumerate(self.current_steps):
            item_title = QTableWidgetItem(step["title"])
            item_title.setFlags(item_title.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_steps.setItem(row, 0, item_title)

            desc_text = step.get("desc", "")
            item_desc = QTableWidgetItem(desc_text)
            item_desc.setFlags(item_desc.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_steps.setItem(row, 1, item_desc)

            item_status = QTableWidgetItem("⚪ Sẵn sàng")
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_status.setFlags(item_status.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_steps.setItem(row, 2, item_status)

            btn_run_step = QPushButton("▶ Chạy bước này")
            btn_run_step.setStyleSheet("padding: 2px 8px;")
            btn_run_step.clicked.connect(lambda checked, r=row: self._run_single_step(r))
            self.table_steps.setCellWidget(row, 3, btn_run_step)

    # -------------------------------------------------------------
    # Pre-Setup Execution
    # -------------------------------------------------------------
    def _run_all_steps(self):
        self._start_workflow(single_step_idx=None)

    def _run_single_step(self, step_idx: int):
        self._start_workflow(single_step_idx=step_idx)

    def _start_workflow(self, single_step_idx=None):
        if not self.ssh.is_connected():
            QMessageBox.warning(self, "Chưa kết nối", "Vui lòng kết nối SSH trước!")
            return

        # 1. Device check
        valid = self._check_device_status(show_dialog=False)
        if not valid:
            QMessageBox.critical(self, "Lỗi Thiết Bị", 
                "Không thể chạy Pre-Setup: Yêu cầu kết nối DUY NHẤT 1 thiết bị.\n"
                f"{self.lbl_device_status.text()}")
            return

        # 2. Confirm paths if userdebug or user is empty
        suite = self.combo_suite.currentText()
        need_user = "STS" not in suite
        if not self.paths.get("userdebug_path") or (need_user and not self.paths.get("user_path")):
            ret = QMessageBox.question(
                self, "Chưa xác nhận đường dẫn",
                "Chưa phát hiện đầy đủ đường dẫn thư mục User / Userdebug.\n"
                "Bạn có muốn mở hộp thoại cấu hình đường dẫn ngay bây giờ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ret == QMessageBox.StandardButton.Yes:
                self._open_confirm_paths_dialog()
                if not self.paths.get("userdebug_path") or (need_user and not self.paths.get("user_path")):
                    return
            else:
                return

        # Re-build steps with latest paths
        self.current_steps = build_workflow_steps(suite, self.paths)

        # Reset step statuses
        if single_step_idx is None:
            for r in range(self.table_steps.rowCount()):
                self._set_step_status(r, "⚪ Đang chờ", "#9e9e9e")
            self.progress_bar.setValue(0)
        else:
            self._set_step_status(single_step_idx, "⏳ Đang chạy...", "#ffb300")

        # UI state
        self.btn_run_all.setEnabled(False)
        self.btn_abort.setEnabled(True)

        # Start worker thread
        self.worker = WorkflowWorker(
            ssh_mgr=self.ssh,
            steps=self.current_steps,
            single_step_idx=single_step_idx,
            timeouts=self.config.get("timeouts", {})
        )

        self.worker.log_signal.connect(self._append_log)
        self.worker.step_started_signal.connect(self._on_worker_step_started)
        self.worker.step_finished_signal.connect(self._on_worker_step_finished)
        self.worker.progress_signal.connect(self._on_worker_progress)
        self.worker.manual_auth_signal.connect(self._on_worker_manual_auth)
        self.worker.step_error_signal.connect(self._on_worker_step_error)
        self.worker.workflow_finished_signal.connect(self._on_worker_finished)

        self.worker.start()

    def _abort_execution(self):
        if self.worker and self.worker.isRunning():
            self._append_log("Đang yêu cầu dừng tiến trình...", "WARN")
            self.worker.request_abort()
            self.btn_abort.setEnabled(False)
        if self.report_worker and self.report_worker.isRunning():
            self._append_log("Đang yêu cầu dừng thu thập báo cáo...", "WARN")
            self.report_worker.request_abort()

    def _on_worker_step_started(self, step_idx: int, step_title: str):
        self._set_step_status(step_idx, "⏳ Đang chạy...", "#ffb300")

    def _on_worker_step_finished(self, step_idx: int, step_title: str, success: bool):
        if success:
            self._set_step_status(step_idx, "🟢 Thành công", "#4caf50")
        else:
            self._set_step_status(step_idx, "🔴 Thất bại", "#f44336")

    def _on_worker_progress(self, current: int, total: int):
        percent = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percent)

    def _on_worker_manual_auth(self, step_idx: int, prompt_msg: str):
        dlg = ManualAuthDialog(self, prompt_msg)
        res = dlg.exec()
        if res == ManualAuthDialog.DialogCode.Accepted:
            self.worker.provide_auth_response(True)
        else:
            self.worker.provide_auth_response(False)

    def _on_worker_step_error(self, step_idx: int, step_title: str, error_msg: str):
        dlg = ErrorDecisionDialog(self, step_title, error_msg)
        dlg.exec()
        self.worker.provide_error_decision(dlg.decision)

    def _on_worker_finished(self, success: bool, msg: str):
        self.btn_run_all.setEnabled(True)
        self.btn_abort.setEnabled(False)
        if success:
            QMessageBox.information(self, "Hoàn tất Pre-Setup", f"Chúc mừng! {msg}")
        else:
            QMessageBox.warning(self, "Pre-Setup Chưa Hoàn Tất", msg)

    def _set_step_status(self, row: int, text: str, color_hex: str):
        if 0 <= row < self.table_steps.rowCount():
            item = self.table_steps.item(row, 2)
            if item:
                item.setText(text)
                item.setForeground(QColor(color_hex))

    # -------------------------------------------------------------
    # Report Collector Functions
    # -------------------------------------------------------------
    def _scan_report_preview_clicked(self):
        if not self.ssh.is_connected():
            QMessageBox.warning(self, "Chưa kết nối", "Vui lòng kết nối SSH trước!")
            return

        test_root = self.txt_test_root.text().strip()
        if not test_root:
            QMessageBox.warning(self, "Thiếu đường dẫn", "Vui lòng nhập đường dẫn Test Root!")
            return

        self._append_log(f"Đang quét & phân tích các session kết quả tại: {test_root}...", "INFO")
        self.btn_scan_preview.setEnabled(False)
        self.btn_scan_preview.setText("Đang quét...")

        res = self.ssh.scan_report_preview(test_root)
        self.btn_scan_preview.setEnabled(True)
        self.btn_scan_preview.setText("🔎 Quét & Phân Tích Kết Quả (Scan Preview)")

        if "error" in res:
            self._append_log(f"[ERROR] {res['error']}", "ERROR")
            QMessageBox.critical(self, "Lỗi Quét", res["error"])
            return

        # Update stats
        total = res.get("total_sessions", 0)
        passed = res.get("passed_sessions_count", 0)
        latest_cnt = res.get("latest_pass_count", 0)
        self.lbl_report_stats.setText(f"Tổng: {total} | Pass: {passed} | Latest Pass Modules: {latest_cnt}")
        self.lbl_report_stats.setStyleSheet("font-weight: bold; color: #4caf50;" if passed > 0 else "color: #ffa726;")

        # Populate table
        sessions = res.get("sessions", [])
        self.table_report_preview.setRowCount(len(sessions))

        for row, s in enumerate(sessions):
            # 0: Timestamp
            it_ts = QTableWidgetItem(s["timestamp"])
            it_ts.setFlags(it_ts.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_report_preview.setItem(row, 0, it_ts)

            # 1: Type
            it_type = QTableWidgetItem(s["type"].upper())
            it_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_type.setFlags(it_type.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_report_preview.setItem(row, 1, it_type)

            # 2: Module Name
            it_mod = QTableWidgetItem(s["module_name"])
            it_mod.setFlags(it_mod.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_report_preview.setItem(row, 2, it_mod)

            # 3: Pass / Fail
            pf_text = f"{s['pass']} / {s['fail']}"
            it_pf = QTableWidgetItem(pf_text)
            it_pf.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_pf.setFlags(it_pf.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_report_preview.setItem(row, 3, it_pf)

            # 4: Rating / Status
            tag = s.get("status_tag", "")
            if tag == "LATEST_PASS":
                it_eval = QTableWidgetItem("🟢 Latest Pass")
                it_eval.setForeground(QColor("#4caf50"))
            elif tag == "OUTDATED_PASS":
                it_eval = QTableWidgetItem("🟡 Outdated Pass")
                it_eval.setForeground(QColor("#ffb300"))
            else:
                it_eval = QTableWidgetItem("🔴 Fail")
                it_eval.setForeground(QColor("#f44336"))
            it_eval.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_eval.setFlags(it_eval.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_report_preview.setItem(row, 4, it_eval)

            # 5: Target folder
            target = s.get("target_folder", "")
            it_target = QTableWidgetItem(target)
            if "[Chưa có" in target:
                it_target.setForeground(QColor("#ef5350"))
            it_target.setFlags(it_target.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_report_preview.setItem(row, 5, it_target)

            # 6: Copy status (Checks both Result and Log)
            c_status = s.get("copy_status", "NOT_COPIED")
            if c_status == "COPIED_FULL":
                it_copied = QTableWidgetItem("🟢 Đủ Result & Log")
                it_copied.setForeground(QColor("#4caf50"))
            elif c_status == "MISSING_LOG":
                it_copied = QTableWidgetItem("🟡 Thiếu Log (Sẽ bổ sung)")
                it_copied.setForeground(QColor("#ffa726"))
            elif c_status == "MISSING_RES":
                it_copied = QTableWidgetItem("🟡 Thiếu Result (Sẽ bổ sung)")
                it_copied.setForeground(QColor("#ffa726"))
            else:
                it_copied = QTableWidgetItem("⚪ Chưa copy")
                it_copied.setForeground(QColor("#9e9e9e"))

            it_copied.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_copied.setFlags(it_copied.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_report_preview.setItem(row, 6, it_copied)

        self.btn_organize_report.setEnabled(latest_cnt > 0)
        self._append_log(f"Quét hoàn tất: {total} sessions, {passed} pass, {latest_cnt} latest modules.", "SUCCESS")

    def _organize_report_clicked(self):
        if not self.ssh.is_connected():
            return

        test_root = self.txt_test_root.text().strip()
        if not test_root:
            return

        ret = QMessageBox.question(
            self, "Xác nhận thực hiện",
            f"Bạn có chắc muốn thực hiện sao chép log & result và tái cấu trúc thư mục Report tại:\n{test_root}?\n\n"
            "- Các module Single đã Pass sẽ được move vào Report/single/\n"
            "- Multiple nếu đã Pass sẽ move results & logs ra ngoài Report/ và xóa 00. Multiple\n"
            "- Các module chưa Pass sẽ được giữ nguyên ngang cấp với single/",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        self.btn_organize_report.setEnabled(False)
        self.btn_scan_preview.setEnabled(False)

        self.report_worker = ReportOrganizeWorker(self.ssh, test_root)
        self.report_worker.log_signal.connect(self._append_log)
        self.report_worker.finished_signal.connect(self._on_report_organize_finished)
        self.report_worker.start()

    def _on_report_organize_finished(self, success: bool, msg: str):
        self.btn_organize_report.setEnabled(True)
        self.btn_scan_preview.setEnabled(True)

        if success:
            QMessageBox.information(self, "Tổ Chức Report Thành Công", msg)
            # Re-scan to update table statuses
            self._scan_report_preview_clicked()
        else:
            QMessageBox.warning(self, "Lỗi Tổ Chức Report", msg)

    # -------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------
    def _append_log(self, text: str, level: str = "INFO"):
        if not text:
            return

        # Strip ANSI escape sequences from remote console/terminal
        clean_text = ANSI_REGEX.sub('', text)

        color_map = {
            "INFO": QColor("#64b5f6"),       # Light blue
            "WARN": QColor("#ffa726"),       # Orange / Amber
            "ERROR": QColor("#ef5350"),      # Red
            "SUCCESS": QColor("#66bb6a"),    # Green
            "STREAM": QColor("#cfd8dc"),     # Silver / Light gray
        }
        color = color_map.get(level, QColor("#e0e0e0"))

        cursor = self.txt_log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(color)

        if level == "STREAM":
            # Normalize carriage returns and newlines from PTY
            stream_text = clean_text.replace("\r\n", "\n").replace("\r", "\n")
            if stream_text:
                cursor.insertText(stream_text, fmt)
                self._log_need_newline = not stream_text.endswith("\n")
        else:
            prefix = "\n" if self._log_need_newline else ""
            timestamp = datetime.now().strftime("%H:%M:%S")
            msg = clean_text.rstrip("\r\n")
            if "\n" in msg:
                lines = msg.split("\n")
                first = f"{prefix}[{timestamp}] [{level}] {lines[0]}\n"
                rest = "\n".join(f"[{timestamp}] [{level}] {l}" for l in lines[1:]) + "\n"
                cursor.insertText(first + rest, fmt)
            else:
                cursor.insertText(f"{prefix}[{timestamp}] [{level}] {msg}\n", fmt)
            self._log_need_newline = False

        self.txt_log.setTextCursor(cursor)
        self.txt_log.ensureCursorVisible()

    def _clear_log(self):
        self.txt_log.clear()
        self._log_need_newline = False

    def _save_log(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Lưu File Log", f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "Text Files (*.txt)"
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.txt_log.toPlainText())
                QMessageBox.information(self, "Thành công", f"Đã lưu file log tại:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu file log: {str(e)}")

    def close_tab(self):
        """Clean up when tab is closed."""
        self._disconnect_ssh()
