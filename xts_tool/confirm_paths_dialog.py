"""
Dialogs for Confirming Paths, Manual Authentication, and Error Handling.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QGroupBox, QFormLayout, QTextEdit, QMessageBox,
    QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class ConfirmPathsDialog(QDialog):
    """
    Displays detected and configured paths before running Pre-Setup.
    Allows user to review, edit, or re-detect paths directly from server.
    """
    def __init__(self, parent, paths: dict, ssh_mgr=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Firmware & Script Paths on Server")
        self.resize(750, 560)
        self.paths = paths.copy()
        self.ssh = ssh_mgr

        layout = QVBoxLayout(self)

        # Header Info
        header = QLabel(
            "<b>Please verify paths before executing Pre-Setup:</b><br>"
            "<small style='color: #888;'>User / Userdebug paths are automatically detected from the root Binary directory on server. "
            "You can modify them directly if needed.</small>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        form_box = QGroupBox("Linux Server Paths Configuration")
        form_layout = QFormLayout(form_box)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Inputs
        self.txt_userdebug = QLineEdit(self.paths.get("userdebug_path", ""))
        self.txt_user = QLineEdit(self.paths.get("user_path", ""))
        
        self.txt_gkey_path = QLineEdit(self.paths.get("google_key_path", ""))
        self.txt_gkey_script = QLineEdit(self.paths.get("google_key_script", "./addGoogle_key_Nissan_P33A.sh"))
        
        self.txt_mtc_path = QLineEdit(self.paths.get("mtc_path", ""))
        mtc_scripts_str = ", ".join(self.paths.get("mtc_scripts", ["./MTC_PZ1D_26MY.sh", "./ChangeLanguage.sh"]))
        self.txt_mtc_scripts = QLineEdit(mtc_scripts_str)
        
        self.txt_calib_path = QLineEdit(self.paths.get("calibration_path", ""))
        self.txt_calib_script = QLineEdit(self.paths.get("calibration_script", "./do_calibration.sh"))
        
        self.txt_gsi_path = QLineEdit(self.paths.get("gsi_image_path", ""))

        form_layout.addRow("Userdebug Release Path:", self.txt_userdebug)
        form_layout.addRow("User Release Path:", self.txt_user)
        form_layout.addRow("Google Key Folder:", self.txt_gkey_path)
        form_layout.addRow("Google Key Script:", self.txt_gkey_script)
        form_layout.addRow("MTC Folder:", self.txt_mtc_path)
        form_layout.addRow("MTC Scripts (comma):", self.txt_mtc_scripts)
        form_layout.addRow("Calibration Folder:", self.txt_calib_path)
        form_layout.addRow("Calibration Script:", self.txt_calib_script)
        form_layout.addRow("GSI Image Folder:", self.txt_gsi_path)

        layout.addWidget(form_box)

        # Action Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_redetect = QPushButton("🔍 Auto Detect from Server")
        self.btn_redetect.clicked.connect(self._re_detect)
        btn_layout.addWidget(self.btn_redetect)

        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_confirm = QPushButton("✔ Confirm Paths & Proceed")
        self.btn_confirm.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px 15px;")
        self.btn_confirm.clicked.connect(self._confirm)
        btn_layout.addWidget(self.btn_confirm)

        layout.addLayout(btn_layout)

    def _re_detect(self):
        if not self.ssh or not self.ssh.is_connected():
            QMessageBox.warning(self, "Chưa kết nối", "SSH chưa được kết nối để quét thư mục trên server.")
            return

        self.btn_redetect.setEnabled(False)
        self.btn_redetect.setText("Đang quét server...")
        try:
            root_dir = self.paths.get("binary_root", "/home/lge/Environment/Storage/Binary/")
            detected = self.ssh.detect_binary_paths(root_dir)
            if detected.get("userdebug_path"):
                self.txt_userdebug.setText(detected["userdebug_path"])
            if detected.get("user_path"):
                self.txt_user.setText(detected["user_path"])
            QMessageBox.information(self, "Quét hoàn tất", 
                f"Đã phát hiện:\n- Userdebug: {detected.get('userdebug_path', 'Chưa thấy')}\n- User: {detected.get('user_path', 'Chưa thấy')}")
        finally:
            self.btn_redetect.setEnabled(True)
            self.btn_redetect.setText("🔍 Quét lại tự động từ Server")

    def _confirm(self):
        ud = self.txt_userdebug.text().strip()
        u = self.txt_user.text().strip()
        if ud and u and ud == u:
            reply = QMessageBox.question(
                self, "Cảnh báo trùng đường dẫn",
                "Đường dẫn Userdebug và User đang giống nhau!\nBạn có chắc chắn muốn xác nhận không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.paths["userdebug_path"] = ud
        self.paths["user_path"] = u
        self.paths["google_key_path"] = self.txt_gkey_path.text().strip()
        self.paths["google_key_script"] = self.txt_gkey_script.text().strip()
        self.paths["mtc_path"] = self.txt_mtc_path.text().strip()
        self.paths["mtc_scripts"] = [s.strip() for s in self.txt_mtc_scripts.text().split(",") if s.strip()]
        self.paths["calibration_path"] = self.txt_calib_path.text().strip()
        self.paths["calibration_script"] = self.txt_calib_script.text().strip()
        self.paths["gsi_image_path"] = self.txt_gsi_path.text().strip()
        self.accept()

    def get_paths(self):
        return self.paths


class ManualAuthDialog(QDialog):
    """
    Non-modal alert requesting the engineer to perform manual authentication on device.
    Supports server, suite, and serial identification.
    """
    auth_responded = pyqtSignal(bool)  # True: Confirm / Continue, False: Abort

    def __init__(self, parent=None, prompt_msg: str = "", server_host: str = "", 
                 suite_name: str = "", device_serial: str = "", step_title: str = ""):
        super().__init__(parent)
        self.setModal(False)
        self._responded = False

        title_tag = f"[{suite_name or 'xTS'}] {server_host}" if server_host else "DUT"
        self.setWindowTitle(f"⚠️ Manual Authentication - {title_tag}")
        self.resize(560, 320)

        layout = QVBoxLayout(self)

        # Header Badge nhận diện máy & server
        badge_frame = QFrame()
        badge_frame.setStyleSheet("background-color: #2b2b2b; border: 1px solid #ff9800; border-radius: 6px; padding: 6px;")
        badge_layout = QGridLayout(badge_frame)
        badge_layout.addWidget(QLabel(f"🖥️ <b>Server:</b> <span style='color: #4fc3f7; font-size: 13px;'>{server_host or 'N/A'}</span>"), 0, 0)
        badge_layout.addWidget(QLabel(f"📦 <b>Suite:</b> <span style='color: #81c784; font-size: 13px;'>{suite_name or 'N/A'}</span>"), 0, 1)
        badge_layout.addWidget(QLabel(f"📱 <b>DUT Serial:</b> <span style='color: #ffb74d; font-family: Consolas;'>{device_serial or 'Unknown'}</span>"), 1, 0)
        badge_layout.addWidget(QLabel(f"📌 <b>Step:</b> <span style='color: #e0e0e0;'>{step_title or 'Manual Authentication'}</span>"), 1, 1)
        layout.addWidget(badge_frame)

        # Hướng dẫn xác thực
        msg_box = QTextEdit()
        msg_box.setReadOnly(True)
        msg_box.setPlainText(prompt_msg)
        msg_box.setStyleSheet("background-color: #1e1e1e; color: #fff; font-size: 13px; padding: 8px; border-radius: 4px;")
        layout.addWidget(msg_box)

        # Nút bấm hành động
        btn_layout = QHBoxLayout()
        btn_abort = QPushButton("✖ Abort")
        btn_abort.setStyleSheet("background-color: #c62828; color: white; padding: 7px 16px; font-weight: bold;")
        btn_abort.clicked.connect(self._on_abort)

        btn_confirm = QPushButton("✔ Complete Authentication (Continue)")
        btn_confirm.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 7px 20px; font-size: 13px;")
        btn_confirm.clicked.connect(self._on_confirm)

        btn_layout.addWidget(btn_abort)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_confirm)
        layout.addLayout(btn_layout)

    def _on_confirm(self):
        if not self._responded:
            self._responded = True
            self.auth_responded.emit(True)
        self.accept()

    def _on_abort(self):
        if not self._responded:
            self._responded = True
            self.auth_responded.emit(False)
        self.reject()

    def closeEvent(self, event):
        if not self._responded:
            self._responded = True
            self.auth_responded.emit(False)
        super().closeEvent(event)


class ErrorDecisionDialog(QDialog):
    """
    Prompt user when a command/step fails: Retry, Skip, or Abort.
    """
    def __init__(self, parent, step_title: str, error_details: str, server_host: str = "", suite_name: str = ""):
        super().__init__(parent)
        title_tag = f"[{suite_name}] {server_host} - " if (server_host or suite_name) else ""
        self.setWindowTitle(f"{title_tag}Step Execution Error")
        self.resize(560, 290)
        self.setModal(True)
        self.decision = "ABORT"

        layout = QVBoxLayout(self)

        if server_host or suite_name:
            lbl_srv = QLabel(f"🖥️ <b>Server:</b> <span style='color: #4fc3f7;'>{server_host or 'N/A'}</span> &nbsp;&nbsp;|&nbsp;&nbsp; 📦 <b>Suite:</b> <span style='color: #81c784;'>{suite_name or 'N/A'}</span>")
            lbl_srv.setStyleSheet("background-color: #2b2b2b; padding: 5px 8px; border-radius: 4px;")
            layout.addWidget(lbl_srv)

        lbl = QLabel(f"<b>Failed Step:</b> <span style='color: #f44336;'>{step_title}</span>")
        lbl.setStyleSheet("font-size: 14px;")
        layout.addWidget(lbl)

        txt_err = QTextEdit()
        txt_err.setReadOnly(True)
        txt_err.setPlainText(error_details)
        txt_err.setStyleSheet("background-color: #262626; color: #ff8a80; font-family: Consolas; font-size: 12px;")
        layout.addWidget(txt_err)

        lbl_ask = QLabel("Please choose an action:")
        layout.addWidget(lbl_ask)

        btn_layout = QHBoxLayout()
        btn_retry = QPushButton("🔄 Retry Step")
        btn_retry.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold; padding: 6px 12px;")
        btn_retry.clicked.connect(self._retry)

        btn_skip = QPushButton("⏩ Skip Step")
        btn_skip.setStyleSheet("background-color: #f57c00; color: white; padding: 6px 12px;")
        btn_skip.clicked.connect(self._skip)

        btn_abort = QPushButton("⏹ Abort Execution")
        btn_abort.setStyleSheet("background-color: #c62828; color: white; font-weight: bold; padding: 6px 12px;")
        btn_abort.clicked.connect(self._abort)

        btn_layout.addWidget(btn_retry)
        btn_layout.addWidget(btn_skip)
        btn_layout.addWidget(btn_abort)

        layout.addLayout(btn_layout)

    def _retry(self):
        self.decision = "RETRY"
        self.accept()

    def _skip(self):
        self.decision = "SKIP"
        self.accept()

    def _abort(self):
        self.decision = "ABORT"
        self.reject()
