"""
Dialog chọn HU để chạy Pre-Setup (chế độ multi-HU tuần tự).

Mỗi lần bấm Run khi có cấu hình "hus", dialog này hiện lên để user tick chọn
những HU cần chạy đợt này (VD: 2/3 máy đã setup xong thì bỏ tick 2 máy đó).
"""
from typing import List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QPushButton, QGroupBox, QMessageBox,
)
from PyQt6.QtCore import Qt


class HUSelectDialog(QDialog):
    """Checklist chọn HU cho 1 lần chạy Pre-Setup."""

    def __init__(self, parent, hus: List[Dict[str, Any]]):
        super().__init__(parent)
        self.setWindowTitle("Chọn HU để chạy Pre-Setup")
        self.resize(420, 300)
        self._hus = list(hus)

        layout = QVBoxLayout(self)

        header = QLabel(
            "<b>Chọn các HU sẽ chạy trong đợt này</b> (tuần tự từng máy):<br>"
            "<small style='color: #888;'>Máy nào đã setup xong thì bỏ tick để khỏi flash lại.</small>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        box = QGroupBox(f"Danh sách HU ({len(self._hus)} máy)")
        box_layout = QVBoxLayout(box)
        self._checkboxes: List[QCheckBox] = []
        for hu in self._hus:
            serial = hu.get("serial", "?")
            kb = hu.get("kb_signal", "?")
            rl = hu.get("rl_signal", "?")
            cb = QCheckBox(f"{serial}   (keyboard {kb} / relay {rl})")
            cb.setChecked(True)
            self._checkboxes.append(cb)
            box_layout.addWidget(cb)
        layout.addWidget(box)

        # Nút chọn nhanh
        quick_row = QHBoxLayout()
        btn_all = QPushButton("Chọn tất cả")
        btn_none = QPushButton("Bỏ chọn tất cả")
        btn_all.clicked.connect(lambda: [cb.setChecked(True) for cb in self._checkboxes])
        btn_none.clicked.connect(lambda: [cb.setChecked(False) for cb in self._checkboxes])
        quick_row.addWidget(btn_all)
        quick_row.addWidget(btn_none)
        quick_row.addStretch(1)
        layout.addLayout(quick_row)

        # OK / Cancel
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_ok = QPushButton("Bắt đầu chạy")
        btn_cancel = QPushButton("Hủy")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._on_accept)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _on_accept(self):
        if not any(cb.isChecked() for cb in self._checkboxes):
            QMessageBox.warning(self, "Chưa chọn HU", "Bạn chưa tick chọn HU nào để chạy.")
            return
        self.accept()

    def selected_hus(self) -> List[Dict[str, Any]]:
        """Trả về danh sách HU được tick (giữ nguyên thứ tự config)."""
        return [hu for hu, cb in zip(self._hus, self._checkboxes) if cb.isChecked()]
