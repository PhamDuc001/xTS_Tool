"""
Generate Report Sub-Tab for xTS Pre-Setup & Report Tool.
Provides interactive UI for configuring, executing, and monitoring
the 9-step Google Certification report generation pipeline.
"""
import os
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional
import paramiko

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QMessageBox, QFileDialog, QProgressBar, QDateEdit, QDialog, QTextEdit
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from generate_report_engine import GenerateReportWorker, STEP_TITLES


class AptraConfirmDialog(QDialog):
    """Modal dialog prompting user to confirm APTRA analysis completion."""
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Xác Nhận Trạng Thái APTRA Analysis")
        self.setFixedSize(520, 240)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl_icon = QLabel("⏳ <b>ĐANG CHỜ PHÂN TÍCH TRÊN SERVER APTRA</b>")
        lbl_icon.setStyleSheet("font-size: 14px; color: #1976d2;")
        layout.addWidget(lbl_icon)

        txt_info = QTextEdit()
        txt_info.setReadOnly(True)
        txt_info.setText(message)
        txt_info.setStyleSheet("background-color: #f5f5f5; font-size: 12px; border: 1px solid #ddd;")
        layout.addWidget(txt_info)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("⏹ Hủy Bỏ")
        self.btn_cancel.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; padding: 6px 14px;")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("✅ ĐÃ CHẠY XONG - TIẾP TỤC")
        self.btn_ok.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px 20px;")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)


class GenerateReportTab(QWidget):
    log_signal = pyqtSignal(str, str)  # (message, level)

    def __init__(self, ssh_manager, config=None, parent=None):
        super().__init__(parent)
        self.ssh_mgr = ssh_manager
        self.config = config or {}
        self.worker: Optional[GenerateReportWorker] = None
        self._init_ui()
        self._load_config_defaults()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        # -------------------------------------------------------------
        # 1. Metadata Configuration Group
        # -------------------------------------------------------------
        meta_group = QGroupBox("Thông Tin Dự Án & Phiên Bản Báo Cáo Chứng Chỉ")
        meta_layout = QGridLayout(meta_group)
        meta_layout.setContentsMargins(8, 8, 8, 8)
        meta_layout.setHorizontalSpacing(10)
        meta_layout.setVerticalSpacing(6)

        # Row 0: Project Full & Model Code
        meta_layout.addWidget(QLabel("<b>Project (Model) Full:</b>"), 0, 0)
        self.txt_model_full = QLineEdit("Nissan_AIVI_Full_12.3_PZ1D_26MY")
        meta_layout.addWidget(self.txt_model_full, 0, 1, 1, 3)

        meta_layout.addWidget(QLabel("<b>Model Code:</b>"), 0, 4)
        self.txt_model_code = QLineEdit("PZ1D")
        self.txt_model_code.setFixedWidth(100)
        meta_layout.addWidget(self.txt_model_code, 0, 5)

        # Row 1: HW, SW, MICOM, Tester
        meta_layout.addWidget(QLabel("<b>HW Version:</b>"), 1, 0)
        self.txt_hw_ver = QLineEdit("C")
        self.txt_hw_ver.setFixedWidth(100)
        meta_layout.addWidget(self.txt_hw_ver, 1, 1)

        meta_layout.addWidget(QLabel("<b>SW Version:</b>"), 1, 2)
        self.txt_sw_ver = QLineEdit("YAK.31.03.30")
        meta_layout.addWidget(self.txt_sw_ver, 1, 3)

        meta_layout.addWidget(QLabel("<b>MICOM:</b>"), 1, 4)
        self.txt_micom_ver = QLineEdit("v3.27.37")
        self.txt_micom_ver.setFixedWidth(100)
        meta_layout.addWidget(self.txt_micom_ver, 1, 5)

        meta_layout.addWidget(QLabel("<b>Tester ID:</b>"), 1, 6)
        self.txt_tester = QLineEdit("duc4.pham")
        self.txt_tester.setFixedWidth(120)
        meta_layout.addWidget(self.txt_tester, 1, 7)

        # Row 2: Date Pickers
        meta_layout.addWidget(QLabel("<b>OEM Delivery:</b>"), 2, 0)
        self.date_oem = QDateEdit()
        self.date_oem.setCalendarPopup(True)
        self.date_oem.setDisplayFormat("MM/dd/yyyy")
        self.date_oem.setDate(QDate.currentDate())
        meta_layout.addWidget(self.date_oem, 2, 1)

        meta_layout.addWidget(QLabel("<b>Test Start:</b>"), 2, 2)
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("MM/dd/yyyy")
        self.date_start.setDate(QDate.currentDate().addDays(-3))
        meta_layout.addWidget(self.date_start, 2, 3)

        meta_layout.addWidget(QLabel("<b>Test End:</b>"), 2, 4)
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("MM/dd/yyyy")
        self.date_end.setDate(QDate.currentDate())
        meta_layout.addWidget(self.date_end, 2, 5)

        # Row 3: Raw Path on Connected Server
        meta_layout.addWidget(QLabel("<b>Raw Path (Server):</b>"), 3, 0)
        self.txt_raw_path = QLineEdit("/home/lge/GoogleQA/Report_tmp/01.Full/")
        meta_layout.addWidget(self.txt_raw_path, 3, 1, 1, 5)

        # Row 4: Previous Summary Template Path
        meta_layout.addWidget(QLabel("<b>Summary Mẫu Trước:</b>"), 4, 0)
        self.txt_prev_summary = QLineEdit()
        self.txt_prev_summary.setPlaceholderText("Đường dẫn file Summary phiên bản trước (trên GOOGLEQA hoặc máy Local)")
        meta_layout.addWidget(self.txt_prev_summary, 4, 1, 1, 5)

        self.btn_detect_prev = QPushButton("🔍 Dò Bản Gần Nhất")
        self.btn_detect_prev.setToolTip("Tự động quét trên GOOGLEQA để lấy file Summary của version trước gần nhất")
        self.btn_detect_prev.clicked.connect(self._auto_detect_prev_summary)
        meta_layout.addWidget(self.btn_detect_prev, 4, 6)

        self.btn_browse_prev = QPushButton("📂 Browse Local...")
        self.btn_browse_prev.clicked.connect(self._browse_prev_summary)
        meta_layout.addWidget(self.btn_browse_prev, 4, 7)

        # Row 5: APTRA Path (Server)
        meta_layout.addWidget(QLabel("<b>APTRA Path:</b>"), 5, 0)
        self.txt_aptra_path = QLineEdit("/home/aptra/APTRA/Nissan_AIVI_Full_12.3_PZ1D_26MY/YAK.31.03.30")
        self.txt_aptra_path.setPlaceholderText("Thư mục trên APTRA (sync data & lấy *Result.xlsx)")
        meta_layout.addWidget(self.txt_aptra_path, 5, 1, 1, 7)

        # Row 6: GOOGLEQA Upload Path (Server)
        meta_layout.addWidget(QLabel("<b>GOOGLEQA Upload:</b>"), 6, 0)
        self.txt_googleqa_dest = QLineEdit("/home/googleqa/GOOGLEQA/Official_Test_results/Nissan_AIVI_Full_12.3_PZ1D_26MY/YAK.31.03.30")
        self.txt_googleqa_dest.setPlaceholderText("Thư mục phát hành trên GOOGLEQA (upload file 00 - 03 & Summary)")
        meta_layout.addWidget(self.txt_googleqa_dest, 6, 1, 1, 7)

        # Dynamic sync when Model or SW changes
        self.txt_model_full.textChanged.connect(self._sync_server_paths)
        self.txt_sw_ver.textChanged.connect(self._sync_server_paths)

        main_layout.addWidget(meta_group)

        # -------------------------------------------------------------
        # 2. Action Controls & Progress
        # -------------------------------------------------------------
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(10)

        self.btn_run_all = QPushButton("🚀 Generate Report")
        self.btn_run_all.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; font-size: 13px; padding: 8px 18px;")
        self.btn_run_all.clicked.connect(self._run_all)
        ctrl_layout.addWidget(self.btn_run_all)

        self.btn_stop = QPushButton("⏹ DỪNG LẠI (Stop)")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #c62828; color: white; font-weight: bold; font-size: 13px; padding: 8px 16px;")
        self.btn_stop.clicked.connect(self._stop_execution)
        ctrl_layout.addWidget(self.btn_stop)

        self.btn_open_folder = QPushButton("📂 Mở Thư Mục Báo Cáo (Local)")
        self.btn_open_folder.setStyleSheet("font-weight: bold; padding: 8px 14px;")
        self.btn_open_folder.clicked.connect(self._open_report_folder)
        ctrl_layout.addWidget(self.btn_open_folder)

        ctrl_layout.addStretch()

        self.lbl_status = QLabel("Trạng thái: Sẵn sàng")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #1976d2;")
        ctrl_layout.addWidget(self.lbl_status)

        main_layout.addLayout(ctrl_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setRange(0, len(STEP_TITLES))
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.progress_bar)

        # -------------------------------------------------------------
        # 3. Steps Table
        # -------------------------------------------------------------
        self.table_steps = QTableWidget()
        self.table_steps.setColumnCount(5)
        self.table_steps.setHorizontalHeaderLabels([
            "Bước", "Tên Bước Quy Trình", "Mô Tả Chi Tiết", "Trạng Thái", "Hành Động"
        ])
        self.table_steps.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_steps.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_steps.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_steps.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_steps.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_steps.verticalHeader().setVisible(False)
        self.table_steps.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        step_descriptions = [
            "Chạy ReportGenerator.py -p <raw_path> để sinh 00.Internal và các file zip",
            "Đồng bộ song song 100%: Upload file zip sang GOOGLEQA (4 luồng) & folder *Results sang APTRA (4 luồng)",
            "Hiện Pop-up nhắc kỹ sư kích hoạt APTRA Analysis & chờ xác nhận",
            "Tải *Result.xlsx từ APTRA, Summary mẫu từ GOOGLEQA, và CTS_Verifier XML về Local Windows",
            "Đổi tên file 03.*, điền Header metadata, unmerge B17:F17, xóa rows 15-40 bằng openpyxl",
            "Chèn khối version mới vào sheet Summary, tính =SUM, cập nhật Fail Module & TestCase List",
            "Upload trực tiếp toàn bộ file 03.*.xlsx và file Summary hoàn chỉnh lên server GOOGLEQA",
            "Lưu trữ một bản sao các file hoàn thiện tại ResultFinal/"
        ]

        self.table_steps.setRowCount(len(STEP_TITLES))
        for idx, (title, desc) in enumerate(zip(STEP_TITLES, step_descriptions)):
            item_num = QTableWidgetItem(f"Bước {idx+1}")
            item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_steps.setItem(idx, 0, item_num)

            item_title = QTableWidgetItem(title)
            font = item_title.font()
            font.setBold(True)
            item_title.setFont(font)
            self.table_steps.setItem(idx, 1, item_title)

            item_desc = QTableWidgetItem(desc)
            self.table_steps.setItem(idx, 2, item_desc)

            item_status = QTableWidgetItem("⚪ Chờ chạy")
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_status.setForeground(QColor("#757575"))
            self.table_steps.setItem(idx, 3, item_status)

            btn_run_step = QPushButton("▶ Chạy Bước Này")
            btn_run_step.setStyleSheet("padding: 2px 8px;")
            btn_run_step.clicked.connect(lambda _, s=idx: self._run_single_step(s))
            self.table_steps.setCellWidget(idx, 4, btn_run_step)

        main_layout.addWidget(self.table_steps, 1)

    def _sync_server_paths(self):
        """Automatically updates APTRA and GOOGLEQA destination paths when Model or SW changes."""
        model = self.txt_model_full.text().strip()
        sw = self.txt_sw_ver.text().strip()
        if model and sw:
            self.txt_aptra_path.setText(f"/home/aptra/APTRA/{model}/{sw}")
            self.txt_googleqa_dest.setText(f"/home/googleqa/GOOGLEQA/Official_Test_results/{model}/{sw}")

    def _load_config_defaults(self):
        gr_cfg = self.config.get("generate_report", {})
        if gr_cfg.get("model_full"):
            self.txt_model_full.setText(gr_cfg["model_full"])
        if gr_cfg.get("model_code"):
            self.txt_model_code.setText(gr_cfg["model_code"])
        if gr_cfg.get("hw_version"):
            self.txt_hw_ver.setText(gr_cfg["hw_version"])
        if gr_cfg.get("sw_version"):
            self.txt_sw_ver.setText(gr_cfg["sw_version"])
        if gr_cfg.get("micom_version"):
            self.txt_micom_ver.setText(gr_cfg["micom_version"])
        if gr_cfg.get("tester_name"):
            self.txt_tester.setText(gr_cfg["tester_name"])
        if gr_cfg.get("raw_path"):
            self.txt_raw_path.setText(gr_cfg["raw_path"])
        if gr_cfg.get("prev_summary_path"):
            self.txt_prev_summary.setText(gr_cfg["prev_summary_path"])
        if gr_cfg.get("aptra_path"):
            self.txt_aptra_path.setText(gr_cfg["aptra_path"])
        if gr_cfg.get("googleqa_dest_path"):
            self.txt_googleqa_dest.setText(gr_cfg["googleqa_dest_path"])

    def _get_execution_params(self) -> Dict[str, Any]:
        return {
            "model_full": self.txt_model_full.text().strip(),
            "model_code": self.txt_model_code.text().strip(),
            "hw_version": self.txt_hw_ver.text().strip(),
            "sw_version": self.txt_sw_ver.text().strip(),
            "micom_version": self.txt_micom_ver.text().strip(),
            "tester_name": self.txt_tester.text().strip(),
            "oem_delivery_date": self.date_oem.date().toString("MM/dd/yyyy"),
            "test_start_date": self.date_start.date().toString("MM/dd/yyyy"),
            "test_end_date": self.date_end.date().toString("MM/dd/yyyy"),
            "raw_path": self.txt_raw_path.text().strip(),
            "prev_summary_path": self.txt_prev_summary.text().strip(),
            "aptra_path": self.txt_aptra_path.text().strip(),
            "googleqa_dest_path": self.txt_googleqa_dest.text().strip(),
            "report_generator_script": self.config.get("generate_report", {}).get(
                "report_generator_script",
                "/home/lge/Environment/tools/GenerReport_Update_0623/ReportGenerator.py"
            ),
            "aptra_server": self.config.get("generate_report", {}).get("aptra_server", {
                "host": "loghub.lge.com", "port": 22, "username": "aptra", "password": "aptra"
            }),
            "googleqa_server": self.config.get("generate_report", {}).get("googleqa_server", {
                "host": "loghub.lge.com", "port": 22, "username": "googleqa", "password": "googleqa"
            }),
        }

    def _auto_detect_prev_summary(self):
        """Connects via SFTP to GOOGLEQA and finds latest version's summary file."""
        model_full = self.txt_model_full.text().strip()
        current_sw = self.txt_sw_ver.text().strip()
        gq_dest = self.txt_googleqa_dest.text().strip()

        self.log_signal.emit("Đang kết nối tới GOOGLEQA để tìm file Summary mẫu của version trước...", "INFO")
        gq_cfg = self.config.get("generate_report", {}).get("googleqa_server", {
            "host": "loghub.lge.com", "port": 22, "username": "googleqa", "password": "googleqa"
        })

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                gq_cfg.get("host", "loghub.lge.com"),
                port=gq_cfg.get("port", 22),
                username=gq_cfg.get("username", "googleqa"),
                password=gq_cfg.get("password", "googleqa"),
                timeout=10
            )
            sftp = client.open_sftp()
            base_dir = os.path.dirname(gq_dest.rstrip("/")).replace("\\", "/") if gq_dest else f"/home/googleqa/GOOGLEQA/Official_Test_results/{model_full}"
            entries = sftp.listdir_attr(base_dir)

            version_candidates = []
            for entry in entries:
                if entry.filename.startswith(".") or entry.filename == current_sw:
                    continue
                version_candidates.append((entry.st_mtime, entry.filename))

            version_candidates.sort(key=lambda x: x[0], reverse=True)

            found_summary = None
            for _, vname in version_candidates:
                vpath = f"{base_dir}/{vname}"
                try:
                    for f in sftp.listdir(vpath):
                        if "Summary" in f and f.endswith(".xlsx"):
                            found_summary = f"{vpath}/{f}"
                            break
                except Exception:
                    continue
                if found_summary:
                    break

            # Fallback: if not found in earlier versions, check current_sw folder itself
            if not found_summary:
                try:
                    vpath = f"{base_dir}/{current_sw}"
                    for f in sftp.listdir(vpath):
                        if "Summary" in f and f.endswith(".xlsx"):
                            found_summary = f"{vpath}/{f}"
                            break
                except Exception:
                    pass

            sftp.close()
            client.close()

            if found_summary:
                self.txt_prev_summary.setText(found_summary)
                self.log_signal.emit(f"[TỰ ĐỘNG DÒ TÌM] Đã tìm thấy file Summary: {found_summary}", "SUCCESS")
                QMessageBox.information(self, "Tìm thấy Summary mẫu", f"Đã tìm thấy file Summary mẫu:\n{found_summary}")
            else:
                self.log_signal.emit("[TỰ ĐỘNG DÒ TÌM] Không tìm thấy file Summary nào trên GOOGLEQA.", "WARN")
                QMessageBox.warning(self, "Không tìm thấy", "Không tìm thấy file Summary nào của version trước trên GOOGLEQA.")
        except Exception as e:
            self.log_signal.emit(f"[LỖI] Không thể kết nối tới GOOGLEQA: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Lỗi kết nối", f"Lỗi khi dò tìm Summary trên GOOGLEQA:\n{str(e)}")

    def _browse_prev_summary(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn File Summary Mẫu Phiên Bản Trước", "", "Excel Files (*.xlsx)"
        )
        if path:
            self.txt_prev_summary.setText(path)

    def _open_report_folder(self):
        sw_ver = self.txt_sw_ver.text().strip() or "output"
        tool_root = os.path.dirname(os.path.abspath(__file__))
        folder = os.path.abspath(os.path.join(tool_root, "temp_report", sw_ver))
        os.makedirs(folder, exist_ok=True)
        try:
            os.startfile(folder)
        except Exception as e:
            QMessageBox.information(self, "Thư mục Báo cáo", f"Đường dẫn thư mục:\n{folder}")

    # -------------------------------------------------------------
    # Worker Execution Handlers
    # -------------------------------------------------------------
    def _run_all(self):
        self._start_worker(single_step=None)

    def _run_single_step(self, step_idx: int):
        self._start_worker(single_step=step_idx)

    def _start_worker(self, single_step: Optional[int]):
        if not self.ssh_mgr.is_connected():
            QMessageBox.warning(self, "Chưa kết nối SSH", "Vui lòng kết nối SSH trước khi chạy báo cáo!")
            return

        params = self._get_execution_params()
        if not params["model_full"] or not params["sw_version"]:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đầy đủ Model Full và SW Version!")
            return

        # Reset UI table status
        if single_step is None:
            for r in range(self.table_steps.rowCount()):
                item = self.table_steps.item(r, 3)
                if item:
                    item.setText("⚪ Chờ chạy")
                    item.setForeground(QColor("#757575"))
            self.progress_bar.setValue(0)
        else:
            item = self.table_steps.item(single_step, 3)
            if item:
                item.setText("⚪ Chờ chạy")
                item.setForeground(QColor("#757575"))

        self.btn_run_all.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_status.setText("Trạng thái: Đang thực thi...")

        self.worker = GenerateReportWorker(
            ssh_mgr=self.ssh_mgr,
            params=params,
            single_step_idx=single_step
        )
        self.worker.log_signal.connect(self.log_signal.emit)
        self.worker.step_started_signal.connect(self._on_step_started)
        self.worker.step_finished_signal.connect(self._on_step_finished)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.request_aptra_confirm_signal.connect(self._on_request_aptra_confirm)
        self.worker.workflow_finished_signal.connect(self._on_workflow_finished)

        self.worker.start()

    def _stop_execution(self):
        if self.worker and self.worker.isRunning():
            self.worker.request_abort()
            self.lbl_status.setText("Trạng thái: Đang hủy...")

    def _on_step_started(self, step_idx: int, title: str):
        item = self.table_steps.item(step_idx, 3)
        if item:
            item.setText("🔵 Đang chạy...")
            item.setForeground(QColor("#1976d2"))
        self.lbl_status.setText(f"Đang chạy: {title}")

    def _on_step_finished(self, step_idx: int, title: str, success: bool):
        item = self.table_steps.item(step_idx, 3)
        if item:
            if success:
                item.setText("🟢 Hoàn thành")
                item.setForeground(QColor("#2e7d32"))
            else:
                item.setText("🔴 Thất bại")
                item.setForeground(QColor("#d32f2f"))

    def _on_progress(self, curr: int, total: int):
        self.progress_bar.setValue(curr)

    def _on_request_aptra_confirm(self, prompt_msg: str):
        """Shows modal dialog for user to confirm APTRA analysis completion."""
        dialog = AptraConfirmDialog(prompt_msg, parent=self)
        res = dialog.exec()
        if res == QDialog.DialogCode.Accepted:
            if self.worker:
                self.worker.provide_aptra_confirmation(True)
        else:
            if self.worker:
                self.worker.provide_aptra_confirmation(False)

    def _on_workflow_finished(self, success: bool, msg: str):
        self.btn_run_all.setEnabled(True)
        self.btn_stop.setEnabled(False)

        if success:
            self.lbl_status.setText("Trạng thái: ✅ Đã hoàn thành toàn bộ")
            self.progress_bar.setValue(self.progress_bar.maximum())
            QMessageBox.information(
                self, "Báo Cáo Thành Công",
                "🎉 Quá trình tạo và xuất bản báo cáo chứng chỉ Google đã hoàn tất thành công!\n\n"
                "Báo cáo đã được upload lên GOOGLEQA và lưu trữ tại ResultFinal."
            )
        else:
            self.lbl_status.setText("Trạng thái: ⚠️ Kết thúc có lỗi")
            QMessageBox.warning(
                self, "Quá Trình Kết Thúc",
                f"Quá trình báo cáo đã dừng lại:\n{msg}"
            )
