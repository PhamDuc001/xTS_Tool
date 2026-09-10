# Yêu Cầu Kỹ Thuật Tích Hợp Vào `xTS_Tool` (Integration Requirements)

Tài liệu này xác định chi tiết kiến trúc phần mềm, thiết kế giao diện (UI), các mô-đun xử lý backend và cơ chế kiểm soát lỗi khi tích hợp tính năng **Generate Report** vào công cụ `xTS_Tool` (`D:\Training\Guide\YAK\xts_tool`).

---

## 1. Vị trí tích hợp trong `xTS_Tool`

Trong cấu trúc hiện tại của `xts_tool`:
- `main_window.py`: Giao diện chính chứa các tab (Server, Device Checker, Workflow Runner, Report Collector).
- `server_tab.py`: Quản lý kết nối SSH đến server test (`10.218.158.66`).
- `ssh_client.py`: Mô-đun wrapper xử lý kết nối SSH/SFTP (Paramiko).
- `workflow_runner.py`: Thực thi các lệnh và workflow chạy test.

👉 **Đề xuất tích hợp:**
Thêm một tab chuyên biệt: **"Generate Report"** (hoặc tích hợp mở rộng trong `report_collector.py`) với giao diện điều khiển quy trình khép kín từ lúc kết thúc bài test đến lúc xuất bản báo cáo lên GOOGLEQA.

---

## 2. Thiết kế giao diện (UI Form Specification)

Giao diện cần cung cấp các trường nhập liệu có lưu nhớ (persistent config trong `config.json`):

### A. Cấu hình Máy Chủ & Đường Dẫn (Server & Path Settings)
1. **Test Runner Server:** `10.218.158.66` (User: `lge`, Password: `***`, Port: `22`)
2. **Raw Test Results Path:** `/home/lge/GoogleQA/Report_tmp/01.Full/`
3. **APTRA Server:** `loghub.lge.com` / `10.158.15.144` (User: `aptra`, Password: `***`)
4. **GOOGLEQA Server:** `loghub.lge.com` / `10.158.15.144` (User: `googleqa`, Password: `***`)
5. **Previous Summary Template Path:** Đường dẫn file summary mẫu của version trước trên GOOGLEQA (ví dụ: `/home/googleqa/GOOGLEQA/Official_Test_results/Nissan_AIVI_Full_12.3_P61R/YAK.31.06.38.U0M/Nissan_P61R_Google Certification Summary.xlsx`).

### B. Thông tin kiểm thử (Test Run Metadata)
| Tên trường UI | Nhãn hiển thị | Giá trị mặc định / Gợi ý | Bắt buộc? |
| :--- | :--- | :--- | :---: |
| `txt_project_model` | Project (Model) Full | `Nissan_AIVI_Full_12.3_PZ1D_26MY` | Có |
| `txt_model_code` | Model Short Code | `PZ1D` | Có |
| `txt_hw_version` | HW (PCB) Version | `C` | Có |
| `txt_sw_version` | SW Version Full | `YAK.31.03.30` | Có |
| `txt_micom_version` | MICOM Version | `v3.27.37` | Có |
| `date_oem_delivery` | OEM Delivery Date | `09/11/2026` (Chọn lịch / DatePicker) | Có |
| `date_test_start` | Test Start Date | `09/07/2026` (Chọn lịch / DatePicker) | Có |
| `date_test_end` | Test End Date | `09/10/2026` (Chọn lịch / DatePicker) | Có |
| `txt_tester` | Tester ID | `duc4.pham` | Có |

---

## 3. Thiết kế các Mô-đun Backend (Backend Processing Modules)

Đề xuất tạo mới một mô-đun: `xts_tool/report_pipeline_engine.py` gồm các class/hàm chính:

```
xts_tool/
├── report_pipeline_engine.py      # [MỚI] Engine chính điều phối 8 bước
├── excel_report_formatter.py     # [MỚI] Xử lý openpyxl format file 03 và Summary
└── report_tab.py                 # [MỚI] Giao diện Tab Generate Report
```

### Các phương thức chính của `report_pipeline_engine.py`:
1. `run_report_generator(session)`:
   - Thực thi `python3 ReportGenerator.py -p ...` trên Server 66.
   - Theo dõi log thời gian thực.
2. `sync_raw_to_googleqa(session)`:
   - Upload toàn bộ `01.Full/*.zip` và các folder test cùng `00.OEM_APFE*.zip` sang GOOGLEQA.
3. `sync_internal_to_aptra(session)`:
   - Copy `00.Internal/*Results/` sang thư mục APTRA tương ứng.
4. `wait_or_trigger_aptra_analysis()`:
   - Kích hoạt hoặc kiểm tra sự xuất hiện của các file `.xlsx`, `.csv` trên APTRA.
5. `fetch_aptra_results(session)`:
   - Tải các file `.xlsx` về Server 66 tại `Report_tmp/ResultFinal/`.
6. `format_suite_excel_files(metadata)`:
   - Đổi tên file theo mẫu `03.LGE_{Model}_{Suite}_Result_Final_{SW}.xlsx`.
   - Mở từng file bằng `openpyxl`:
     - Điền metadata vào `C3, C4, C5, C6, G2, G3, G4, G6`.
     - Unmerge `B17:F17`.
     - Xóa các dòng từ 15 đến 40 (`delete_rows(15, rows_to_delete)`).
     - Lưu đè file.
7. `generate_google_certification_summary(metadata, prev_template_path)`:
   - Kiểm tra file template version trước:
     - Nếu không có bảng version trước: Hiển thị cảnh báo (Warning Dialog) yêu cầu người dùng cung cấp đường dẫn khác.
     - Nếu hợp lệ: Copy block cuối, dán tại vị trí mới cách 2 dòng trống.
   - Quét từng file suite `03.*.xlsx`:
     - Đọc dãy 7 giá trị từ `D3:J3` của sheet `Test Result_Detail`.
     - Điền vào dòng test category tương ứng tại sheet `Summary`.
     - Cập nhật công thức `=SUM(...)`.
   - Xử lý các case Fail:
     - Lọc các module có `Failed > 0` từ sheet `Test Result_Detail` ➔ Ghi vào `Nissan Fail Module List`.
     - Đọc các testcase từ sheet `Failed Test Cases` ➔ Ghi vào `Nissan Fail TestCase List`.
     - Nếu không có fail: Giữ nguyên khung bảng, để trống dữ liệu.
8. `publish_final_to_googleqa(session)`:
   - Upload toàn bộ gói phát hành chính thức lên GOOGLEQA.

---

## 4. Xử lý ngoại lệ và An toàn dữ liệu (Fault Tolerance & Data Safety)

1. **Sao lưu trước khi chỉnh sửa (Transactional Backup):**
   - Mọi file Excel (`03.*.xlsx` và file Summary) đều được tạo bản sao lưu `.bak` trước khi thực hiện chỉnh sửa cấu trúc. Nếu có lỗi xảy ra trong quá trình ghi bằng `openpyxl`, tự động khôi phục từ bản backup.
2. **Kiểm tra Unmerge trước khi xóa dòng:**
   - Thư viện `openpyxl` sẽ bị lỗi hoặc làm hỏng file nếu xóa dòng chứa vùng ô bị merge. Engine luôn tự động duyệt qua `ws.merged_cells.ranges` và `unmerge` tất cả các vùng nằm trong phạm vi dòng cần xóa trước khi gọi `delete_rows`.
3. **Cảnh báo file Summary mẫu không tương thích:**
   - Nếu file mẫu không chứa đúng định dạng các cột hoặc không tìm thấy bảng version trước, engine dừng ngay và thông báo lỗi rõ ràng cho người dùng, không tự ý ghi đè làm hỏng file.
4. **Thanh tiến trình & Nhật ký trực quan (Progress Bar & Live Console):**
   - Mỗi bước trong quy trình 8 bước đều phát tín hiệu (Qt Signal) cập nhật % tiến độ và ghi log chi tiết lên cửa sổ console của UI.
