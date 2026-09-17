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
   - Nút lớn: **"🚀 Chạy Toàn Bộ Quy Trình (Run All)"** (Mặc định chạy Fast-Track Bước 1–7 trong ~1–2 phút).
   - Checkbox: **"📦 Tự động upload gói zip nặng (Bước 8)"** (Mặc định không chọn, cho phép linh hoạt chạy gói lưu trữ nặng).
   - Bảng danh sách 8 bước kèm nút **"Chạy Bước Này"** cho từng bước độc lập (Step-by-Step Execution / Debug).
   - Nút **"📂 Mở Thư Mục Báo Cáo (Local)"**: Mở ngay folder `temp_report/` trên máy tính để kỹ sư xem trước file Excel.
3. **Khu vực Tiến độ & Console Nhật ký:**
   - Progress bar hiển thị tiến trình tổng (7 bước hoặc 8 bước).
   - Cửa sổ Text Console hiển thị log màu (INFO, SUCCESS, WARNING, ERROR).

---

## 2. Thiết kế Module Phần Mềm (Software Modules)

```
xts_tool/
├── generate_report_tab.py         # Giao diện Sub-tab 3 (PyQt6) & Controller
└── generate_report_engine.py      # Core Engine điều phối 8 bước & ExcelFormatter (openpyxl)
```

### Chi tiết 8 bước thực thi trong `GenerateReportEngine`:
1. `_step1_run_report_generator()`: Gọi lệnh chạy `ReportGenerator.py` trên Test Runner Server qua SSH.
2. `_step2_sync_to_aptra()`: Chạy `curl` SFTP song song từ Runner sang APTRA chỉ đẩy các thư mục `00.Internal/*Results/` (Critical Input Path).
3. `_step3_wait_aptra_confirmation()`: Hiển thị Pop-up chờ kỹ sư confirm APTRA chạy xong và kiểm tra file CSV trên APTRA.
4. `_step4_download_excel_to_local()`: Tải trực tiếp các file `*Result(s).xlsx` từ APTRA và file Summary mẫu từ GOOGLEQA về Windows `temp_report/`.
5. `_step5_format_suite_reports()`: Gọi `ExcelReportFormatter` đổi tên `03.*.xlsx`, điền Header (C5 là SW version mới), unmerge an toàn dải hàng 15–40 và xóa hàng thừa.
6. `_step6_generate_summary_report()`: Trích xuất 7 chỉ số (kèm fallback), bóc tách version điền động vào `Test Category` cho toàn bộ 10 suite, nhân bản block mới, cập nhật 2 sheet Fail.
7. `_step7_publish_to_googleqa()`: SFTP upload trực tiếp các file `.xlsx` nhẹ lên GOOGLEQA trong 1–2 giây và copy vào `ResultFinal/` trên runner.
8. `_step8_sync_heavy_archives_to_googleqa()`: Chạy `curl` SFTP đẩy các gói zip nén nặng (`01.*.zip`, `00.OEM*.zip`, `02.*.zip`) sang GOOGLEQA (chạy độc lập hoặc kích hoạt tự động qua checkbox).

---

## 3. Cơ chế An toàn Dữ liệu & Xử lý Ngoại lệ (Safety & Error Handling)
1. **Kiểm tra Unmerge trước khi xóa dòng:** Luôn tự động unmerge các cell merge nằm trong khoảng dòng cần xóa để tránh hỏng file Excel.
2. **Xóa sạch dữ liệu lỗi cũ:** Trước khi ghi danh sách fail mới, xóa sạch toàn bộ data từ dòng 3 trở đi của 2 sheet `Nissan Fail Module List` và `Nissan Fail TestCase List`.
3. **Sao lưu trước khi chỉnh sửa:** Tự động tạo bản copy `.bak` cho mọi file Excel trước khi can thiệp.
