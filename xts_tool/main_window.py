"""
Main Window for xTS Pre-Setup UI Tool.
Manages multi-server tabs, configuration loading, theme styling, and global actions.
"""
import os
import json
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QToolBar, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction

from server_tab import ServerTab


DARK_THEME_QSS = """
QMainWindow {
    background-color: #121212;
}
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    margin-top: 10px;
    font-weight: bold;
    color: #90caf9;
    padding-top: 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QLineEdit, QComboBox {
    background-color: #2b2b2b;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 5px;
    color: #ffffff;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #2196f3;
}
QPushButton {
    background-color: #333333;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 6px 12px;
    color: #ffffff;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #424242;
    border-color: #777;
}
QPushButton:pressed {
    background-color: #1f1f1f;
}
QPushButton:disabled {
    background-color: #262626;
    color: #666666;
    border-color: #333;
}
QTabWidget::pane {
    border: 1px solid #333;
    background-color: #1e1e1e;
}
QTabBar::tab {
    background: #252525;
    color: #aaa;
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1e1e1e;
    color: #64b5f6;
    font-weight: bold;
    border-bottom: 2px solid #2196f3;
}
QTabBar::tab:hover:!selected {
    background: #2e2e2e;
    color: #ddd;
}
QTableWidget {
    background-color: #222222;
    gridline-color: #333333;
    border: 1px solid #333333;
    border-radius: 4px;
}
QHeaderView::section {
    background-color: #2c2c2c;
    color: #90caf9;
    padding: 6px;
    font-weight: bold;
    border: 1px solid #333333;
}
QProgressBar {
    border: 1px solid #444;
    border-radius: 4px;
    text-align: center;
    background-color: #222;
    color: #fff;
}
QProgressBar::chunk {
    background-color: #2e7d32;
    border-radius: 3px;
}
QScrollBar:vertical {
    border: none;
    background: #1e1e1e;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #424242;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #616161;
}
"""


class MainWindow(QMainWindow):
    def __init__(self, config_path="config.json"):
        super().__init__()
        self.setWindowTitle("xTS Pre-Setup Manager (ATS / CTS / GSI / STS / VTS)")
        self.resize(1180, 780)
        self.config_path = config_path
        self.config = self._load_config()

        self._init_ui()
        self.setStyleSheet(DARK_THEME_QSS)

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config.json: {e}")
        return {}

    def _save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Lưu cấu hình", "Đã lưu cấu hình thành công vào config.json!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu config: {e}")

    def _init_ui(self):
        # Toolbar
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        btn_add_tab = QPushButton("➕ Thêm Cửa Sổ Server Mới")
        btn_add_tab.setStyleSheet("background-color: #1565c0; color: white; font-weight: bold;")
        btn_add_tab.clicked.connect(lambda: self.add_server_tab())
        toolbar.addWidget(btn_add_tab)

        toolbar.addSeparator()

        btn_save_cfg = QPushButton("💾 Lưu Cấu Hình")
        btn_save_cfg.clicked.connect(self._save_config)
        toolbar.addWidget(btn_save_cfg)

        toolbar.addSeparator()

        lbl_info = QLabel("  |  Mỗi tab là 1 Linux Server - Đảm bảo kết nối DUY NHẤT 1 device per Server")
        lbl_info.setStyleSheet("color: #81c784; font-weight: bold;")
        toolbar.addWidget(lbl_info)

        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close_requested)
        self.setCentralWidget(self.tab_widget)

        # Populate initial server tabs from config
        saved = self.config.get("saved_servers", [])
        if saved:
            for s in saved:
                self.add_server_tab(server_info=s)
        else:
            self.add_server_tab()

    def add_server_tab(self, server_info=None):
        tab = ServerTab(self, config=self.config, default_server_info=server_info)
        
        tab_name = server_info.get("name", "New Server") if server_info else f"Server {self.tab_widget.count() + 1}"
        index = self.tab_widget.addTab(tab, tab_name)
        self.tab_widget.setCurrentIndex(index)

        tab.tab_title_changed.connect(lambda title, w=tab: self._update_tab_title(w, title))

    def _update_tab_title(self, widget, new_title):
        idx = self.tab_widget.indexOf(widget)
        if idx != -1:
            self.tab_widget.setTabText(idx, new_title)

    def _on_tab_close_requested(self, index):
        if self.tab_widget.count() <= 1:
            QMessageBox.information(self, "Thông báo", "Phải giữ lại ít nhất một cửa sổ Server!")
            return

        ret = QMessageBox.question(
            self, "Xác nhận đóng tab",
            f"Bạn có chắc muốn đóng {self.tab_widget.tabText(index)}?\nKết nối SSH và tiến trình đang chạy (nếu có) sẽ bị ngắt.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ret == QMessageBox.StandardButton.Yes:
            widget = self.tab_widget.widget(index)
            if hasattr(widget, "close_tab"):
                widget.close_tab()
            self.tab_widget.removeTab(index)

    def closeEvent(self, event):
        # Clean up all tabs on exit
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if hasattr(widget, "close_tab"):
                widget.close_tab()
        event.accept()
