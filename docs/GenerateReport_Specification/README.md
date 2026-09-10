# Bộ Tài Liệu Đặc Tả Kỹ Thuật Tính Năng "Generate Report" Cho `xTS_Tool`

Tài liệu này được biên soạn đầy đủ và chi tiết sau quá trình khảo sát, thực nghiệm và chuẩn hóa toàn bộ luồng tạo báo cáo chứng chỉ Google Certification xTS (Android Automotive OS) trên hệ thống máy chủ LG & Nissan AIVI.

---

## 📑 Danh mục các tài liệu thành phần

| STT | Tài liệu | Nội dung chính |
| :---: | :--- | :--- |
| **01** | [**`01_WORKFLOW_OVERVIEW.md`**](./01_WORKFLOW_OVERVIEW.md) | **Tổng quan kiến trúc & sơ đồ luồng hệ thống:**<br>• Kiến trúc 4 thực thể (Local Client, Server 66, APTRA, GOOGLEQA).<br>• Sơ đồ luồng dữ liệu Mermaid.<br>• Bảng phân định vai trò và thông tin kết nối các máy chủ. |
| **02** | [**`02_STEP_BY_STEP_PIPELINE.md`**](./02_STEP_BY_STEP_PIPELINE.md) | **Quy trình chi tiết 13 bước thực thi:**<br>• Hướng dẫn chi tiết từng bước từ dữ liệu thô `01.Full/`.<br>• Lệnh gọi `ReportGenerator.py`.<br>• Đồng bộ APTRA và GOOGLEQA.<br>• Chuẩn hóa đổi tên `03.` và làm sạch file Excel.<br>• Tạo và cập nhật file Summary và danh sách Fail. |
| **03** | [**`03_DATA_DICTIONARY_AND_FORMATS.md`**](./03_DATA_DICTIONARY_AND_FORMATS.md) | **Từ điển dữ liệu & bảng tính mẫu Excel:**<br>• Bảng tọa độ chính xác từng ô (cell coordinates) cho file `03.` và file Summary.<br>• Bảng demo dữ liệu thực tế trích xuất từ bản build `YAK.31.03.30`.<br>• Quy tắc lọc Fail (`Failed > 0`) và unmerge bảo toàn công thức. |
| **04** | [**`04_INTEGRATION_REQUIREMENTS_XTS_TOOL.md`**](./04_INTEGRATION_REQUIREMENTS_XTS_TOOL.md) | **Yêu cầu kỹ thuật tích hợp vào `xTS_Tool`:**<br>• Thiết kế giao diện (UI Form) với các trường cấu hình và metadata.<br>• Thiết kế các class/module backend (`report_pipeline_engine.py`, `excel_report_formatter.py`).<br>• Cơ chế xử lý ngoại lệ, cảnh báo file mẫu và sao lưu dữ liệu an toàn. |

---

## 🚀 Tóm tắt luồng công việc chính (Quick Flowchart)

```mermaid
sequenceDiagram
    autonumber
    participant UI as xTS_Tool UI
    participant S66 as Server 10.218.158.66
    participant APTRA as APTRA Server
    participant GQ as GOOGLEQA Server

    UI->>S66: 1. Chạy ReportGenerator.py -p 01.Full/
    S66->>S66: Sinh 00.Internal, 00.OEM_APFE zips, nén 01.*
    S66->>GQ: 2. Upload 01.* và 00.OEM_APFE zips
    S66->>APTRA: 3. Copy 00.Internal/*Results (XML & HTML)
    APTRA->>APTRA: 4. Phân tích XML -> sinh *.xlsx & summary.csv
    S66->>APTRA: 5. Kéo các file *.xlsx về ResultFinal/
    S66->>S66: 6. Đổi tên thành 03.* và format header/clean rows 15-40
    S66->>GQ: 7. Lấy file Summary mẫu version trước
    S66->>S66: 8. Append block mới, map 7 chỉ số, ghi nhận Module/TC Fail
    S66->>GQ: 9. Upload gói hoàn thiện (01, 02, 03, Summary) lên GOOGLEQA
```

---
*Tài liệu được khởi tạo và kiểm chứng trực tiếp trên môi trường máy chủ ngày 10/09/2026.*
