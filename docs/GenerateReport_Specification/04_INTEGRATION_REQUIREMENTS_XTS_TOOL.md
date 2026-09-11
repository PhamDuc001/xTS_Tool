# Yêu Cầu Kỹ Thuật Tích Hợp Vào `xTS_Tool` (Integration Requirements)

---

## 1. Thiết kế Giao Diện (UI Form)
Tích hợp thành **Sub-tab thứ 3** trong `ServerTab`: **"📑 Tạo Báo Cáo Chứng Chỉ (Generate Report)"**.

### Giao diện gồm 3 vùng chức năng:
1. **Khu vực Cấu hình & Thông tin Metadata (Form Inputs):**
   - Project (Model) Full: `Nissan_AIVI_Full_12.3_PZ1D_26MY`
   - Model Short Code: `PZ1D`
   - SW Version: `YAK.31.03.30`
   - HW (PCB) Version: `C`
   - MICOM Version: `v3.27.37`
   - Date pickers: OEM Delivery, Test Start, Test End
   - Tester ID: `duc4.pham`
   - Previous Summary Path + Nút **"🔍 Tự Động Tìm Bản Gần Nhất"** + Nút **"Browse..."**
2. **Khu vực Điều khiển (Control Actions):**
   - Nút lớn: **"🚀 Chạy Toàn Bộ Quy Trình (Run All)"**
   - Bảng danh sách từng bước kèm nút **"Chạy Bước Này"** để hỗ trợ debug từng phần (Step-by-Step).
   - Nút **"📂 Mở Thư Mục Báo Cáo (Local)"**: Mở ngay folder `temp_report/` trên máy tính để kỹ sư xem trước file Excel.
3. **Khu vực Tiến độ & Console Nhật ký:**
   - Progress bar hiển thị % tiến trình tổng.
   - Cửa sổ Text Console hiển thị log màu (INFO, SUCCESS, WARNING, ERROR).

---

## 2. Thiết kế Module Phần Mềm (Software Modules)

```
xts_tool/
├── generate_report_tab.py         # Giao diện Sub-tab 3 (PyQt6)
├── report_pipeline_engine.py      # Bộ điều phối quy trình 9 bước
└── excel_report_formatter.py     # Module openpyxl xử lý file Excel trên Local
```

### Chi tiết các bước thực thi trong `report_pipeline_engine.py`:
1. `step1_run_report_generator()`: Gọi lệnh trên Server 66 qua SSH.
2. `step2_sync_to_googleqa()`: Chạy `curl` SFTP Server-to-Server đẩy `01.*` và `00.OEM*` sang GOOGLEQA.
3. `step3_sync_to_aptra()`: Chạy `curl` SFTP Server-to-Server đẩy `00.Internal/*Results` sang APTRA.
4. `step4_wait_aptra_confirmation()`: Hiển thị Pop-up chờ kỹ sư confirm APTRA chạy xong. Kiểm tra sự xuất hiện của file CSV.
5. `step5_download_excel_to_local()`: Tải trực tiếp các file `*Result.xlsx` từ APTRA và file Summary mẫu từ GOOGLEQA về Windows `temp_report/`.
6. `step6_format_suite_reports()`: Gọi `excel_report_formatter` đổi tên `03.`, điền header, unmerge `B17:F17`, xóa hàng 15-40.
7. `step7_generate_summary_report()`: Trích xuất `D3:J3`, đọc XML của `CTS_Verifier`, tạo block mới, lọc module fail (`Failed > 0`), lọc testcase fail.
8. `step8_publish_to_googleqa()`: Upload trực tiếp từ Windows lên GOOGLEQA và đồng bộ sang Server 66.

---

## 3. Cơ chế An toàn Dữ liệu & Xử lý Ngoại lệ (Safety & Error Handling)
1. **Kiểm tra Unmerge trước khi xóa dòng:** Luôn tự động unmerge các cell merge nằm trong khoảng dòng cần xóa để tránh hỏng file Excel.
2. **Xóa sạch dữ liệu lỗi cũ:** Trước khi ghi danh sách fail mới, xóa sạch toàn bộ data từ dòng 3 trở đi của 2 sheet `Nissan Fail Module List` và `Nissan Fail TestCase List`.
3. **Sao lưu trước khi chỉnh sửa:** Tự động tạo bản copy `.bak` cho mọi file Excel trước khi can thiệp.
