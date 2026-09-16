# Quy Trình Chi Tiết Từng Bước (Step-by-Step Pipeline)

Tài liệu này ghi lại chi tiết toàn bộ các bước thực thi từ dữ liệu thô `01.Full/` đến khi xuất bản báo cáo chính thức lên server GOOGLEQA.

---

## Bước 1: Chuẩn bị dữ liệu kết quả chạy test thô (Raw Test Suites)
- **Vị trí trên Server 66 (`10.218.158.66`):**
  Thư mục do kỹ sư chỉ định trên giao diện UI (mặc định: `/home/lge/GoogleQA/Report_tmp/01.Full/`).
- **Các thư mục bộ test có mặt:**
  - `01.ATS`
  - `01.AtsInteractive`
  - `01.AtsMultidevice`
  - `01.BFG`
  - `01.CTS`
  - `01.CTSonGSI`
  - `01.CTS_Verifier`
  - `01.STS`
  - `01.VTS`

---

## Bước 2: Chạy công cụ `ReportGenerator.py` trên Server 66
- **Lệnh thực thi qua SSH:**
  ```bash
  python3 /home/lge/Environment/tools/GenerReport_Update_0623/ReportGenerator.py -p /home/lge/GoogleQA/Report_tmp/01.Full/
  ```
- **Kết quả sinh ra tại thư mục cha (`/home/lge/GoogleQA/Report_tmp/`):**
  1. `00.Internal/`: Chứa các folder `*Results` (ví dụ `CTSResults/`, `ATSResults/`...) bên trong gồm các file báo cáo HTML, XML và thư mục `DataforAuto/`. Đồng thời chứa các gói nén `02.LGE_{Model}_{Suite}_Result_{SW_Version}.zip`.
  2. `00.OEM_APFE/` và file nén `00.OEM_APFE.zip`.
  3. `00.OEM_APFE_UPLOAD/` và file nén `00.OEM_APFE_UPLOAD.zip`.
  4. Tại `01.Full/`: Mỗi folder bộ test được nén thành file `.zip` tương ứng (`01.CTS.zip`, `01.ATS.zip`...).

---

## Bước 3: Đồng bộ dữ liệu thô sang Server GOOGLEQA (Server-to-Server)
- **Mục đích:** Lưu trữ bản gốc các bộ test phục vụ chứng chỉ Google.
- **Server đích:** `loghub.lge.com` (`googleqa:googleqa`), thư mục:
  `/home/googleqa/GOOGLEQA/Official_Test_results/{Project_Model}/{SW_Version}/`
- **Phương thức:** Lệnh `curl` SFTP trực tiếp từ Server 66:
  - Copy toàn bộ các folder và file `.zip` trong `01.Full/`.
  - Copy 2 file zip OEM: `00.OEM_APFE.zip` và `00.OEM_APFE_UPLOAD.zip`.

---

## Bước 4: Đồng bộ dữ liệu sang Server APTRA (Server-to-Server)
- **Mục đích:** Cung cấp dữ liệu đầu vào cho công cụ phân tích APTRA.
- **Server đích:** `loghub.lge.com` (`aptra:aptra`), thư mục:
  `/home/aptra/APTRA/{Project_Model}/{SW_Version}/`
- **Phương thức:** Lệnh `curl` SFTP trực tiếp từ Server 66:
  - Copy toàn bộ các folder `*Results/` trong `00.Internal/` (HTML + `DataforAuto/`).

---

## Bước 5: Chạy công cụ phân tích APTRA & Xác nhận (Analysis & Confirm)
- **Cơ chế:**
  - `xTS_Tool` hiển thị Pop-up thông báo:
    > ℹ️ *Đã upload dữ liệu sang APTRA thành công. Vui lòng request chạy server APTRA để tạo file báo cáo. Bấm [Đã Hoàn Thành] sau khi server APTRA chạy xong.*
  - Kỹ sư request chạy công cụ trên APTRA.
  - Khi kỹ sư bấm [Đã Hoàn Thành], Tool kiểm tra sự xuất hiện của file `*_summary.csv` trên APTRA và tự động chuyển sang bước 6.

---

## Bước 6: Tải trực tiếp các file kết quả về Local Windows
- **Nguồn:**
  - Từ APTRA (`aptra@loghub.lge.com:/home/aptra/APTRA/{Project}/{SW}/`):
    `ATSResult.xlsx`, `CTSResult.xlsx`, `BFGResult.xlsx`, `STSResult.xlsx`, `CTSonGSIResult.xlsx`, `AtsInteractiveResults.xlsx`, `AtsMultideviceResults.xlsx`, `VTSResult.xlsx`.
  - Từ GOOGLEQA (`googleqa@loghub.lge.com`):
    Tải file Summary mẫu của version trước.
- **Đích lưu:** Thư mục tạm `temp_report/` trên máy trạm Windows.

---

## Bước 7: Chuẩn hóa & Làm sạch các file Excel kết quả `03.*.xlsx`
Xử lý bằng thư viện `openpyxl` trên Python Windows:
1. **Đổi tên file:**
   - Theo mẫu: `03.LGE_Nissan_AIVI_Full_12.3_{Model_Code}_{Suite}_Result_Final_{SW_Version}.xlsx`
   - Ví dụ: `03.LGE_Nissan_AIVI_Full_12.3_PZ1D_CTS_Result_Final_YAK.31.04.10.xlsx`.
   - *Lưu ý:* Xử lý thống nhất tên file cho cả các suite đặc thù: `AtsIncar`, `AtsInteractive`, `AtsMultidevice`, `BFG`.
2. **Điền Header (Sheet `Test Summary`):**
   - `C3`: Project (Model) Full (vd: `Nissan_AIVI_Full_12.3_PZ1D_26MY`)
   - `C4`: HW (PCB) version (vd: `C`)
   - `C5`: SW version (vd: `YAK.31.04.10`) - **BẮT BUỘC** cập nhật đúng SW version mới nhất cho toàn bộ các file `03.`.
   - `C6`: MICOM version (vd: `v3.27.37`)
   - `G2`: OEM Delivery (vd: `09/11/2026`, ép format text `@`)
   - `G3`: Test Start (vd: `09/07/2026`, ép format text `@`)
   - `G4`: Test End (vd: `09/10/2026`, ép format text `@`)
   - `G6`: Tester (vd: `duc4.pham`)
   - *Lưu ý ô `C7`:* Chứa chuỗi gốc phiên bản suite (ví dụ: `CTS 14_r13`, `STS 14_sts-r55`, `VTS 14_r13`, `ATS 2026_r2`), được giữ nguyên và dùng làm nguồn trích xuất version sang bảng Summary.
3. **Làm sạch cấu trúc hàng & An toàn Unmerge:**
   - Quét và unmerge toàn bộ các merged ranges giao cắt với hàng 15 đến 40 trước khi xóa.
   - Xóa các dòng thừa từ 15 đến 40 (`ws.delete_rows(15, ws.max_row - 14)`).
   - Bảo toàn công thức `=E12/C12` tại ô `H12` và các sheet con (`Test Result_Detail`, `Failed Test Cases`).

---

## Bước 8: Tạo & Cập nhật file Google Certification Summary
1. **Khối bảng mới trong sheet `Summary`:**
   - Dò tìm khối bảng của version trước (quét ngược từ dưới lên tìm ô `"Summary"` và `"HW (PCB) version"`).
   - Dán khối bảng mới cách 2 dòng trống.
   - **Cập nhật Metadata khối mới:** Bắt buộc ghi đè `HW version` (Row 19), `SW version` (Row 20 - ví dụ `YAK.31.04.10`, tránh giữ nguyên version cũ sao chép từ template), và `MICOM version` (Row 21).
2. **Quy tắc đặt tên file Summary đầu ra:**
   - Bắt buộc lấy theo `Short_SW` mới nhất: `Nissan_{Model_Code}_Google Certification Summary_{Short_SW}.xlsx`.
   - Ví dụ: Với SW `YAK.31.04.10`, file sinh ra phải là `Nissan_PZ1D_Google Certification Summary_31.04.10.xlsx` (tuyệt đối không giữ tên cũ `31.03.30` của template).
3. **Đồng bộ động phiên bản vào cột `Test Category` (Cột C):**
   - Áp dụng cho **TOÀN BỘ 10 Test Suite** (`ATS`, `ATS-In-Car`, `ATS_Interactive`, `ATS-Multidevice`, `BFG`, `CTS`, `CTSonGSI`, `STS`, `VTS`, `CTS-Verifier`).
   - Nguồn version:
     - 9 suite thông thường: Trích xuất từ ô `C7` của sheet `Test Summary` trong file `03.*.xlsx` tương ứng.
     - `CTS-Verifier`: Trích xuất từ thuộc tính `suite_version` của thẻ `<Result>` trong XML.
   - Format: `<Base_Suite_Name> (<Version>)`, ví dụ: `CTS (14_r13)`, `STS (14_sts-r55)`, `VTS (14_r13)`, `ATS (2026_r2)`, `CTS-Verifier (14_r13)`.
4. **Trích xuất 7 chỉ số kiểm thử & Fallback tính toán:**
   - Mở sheet `Test Result_Detail` của file `03.` tương ứng.
   - Kiểm tra ô `D3:J3`: Nếu có giá trị số hợp lệ $> 0$, sử dụng trực tiếp.
   - **Cơ chế Fallback:** Nếu ô `D3:J3` là `None` (do công thức chưa được tính toán sẵn khi lưu trên Linux), tự động duyệt từ hàng 5 đến cuối bảng để tính tổng cộng dồn từng cột (Pass, Fail, Assumption, Ignored, Total Tests, Module Done, Total Module).
   - Với `CTS_Verifier`: Đọc thẻ `<Summary>` trong file XML `test_result.xml` để lấy `Pass`, `Total`, `Module Done`.
   - Nếu suite không chạy (Partial Run): Đặt các ô D:J là `None` (ô trống), không điền 0.
   - Dòng cuối cùng của khối bảng: Điền công thức `=SUM(D...:D...)` đến `=SUM(J...:J...)`.
5. **Cập nhật sheet `Nissan Fail Module List`:**
   - Xóa sạch dữ liệu cũ từ **dòng 3 trở đi** (`ws.delete_rows(3, ws.max_row - 2)`), giữ nguyên hàng 1 và hàng 2 (Header và khung bảng).
   - Nếu có module có `Failed > 0`: Ghi danh sách module lỗi gồm 7 cột chỉ số vào bảng.
   - Nếu không có lỗi (`Fail = 0`): Giữ nguyên bảng trắng từ dòng 3 trở đi.
6. **Cập nhật sheet `Nissan Fail TestCase List`:**
   - Xóa sạch dữ liệu cũ từ **dòng 3 trở đi** (`ws.delete_rows(3, ws.max_row - 2)`), giữ nguyên hàng 1 và hàng 2.
   - Nếu có lỗi: Đọc danh sách từ sheet `Failed Test Cases` của từng file suite, đánh số thứ tự liên tục `No` (1, 2, 3...) và ghi `Test Category`, `Module`, `Test Case`.
   - Nếu không có lỗi: Giữ nguyên bảng trắng từ dòng 3 trở đi.

---

## Bước 9: Phát hành gói báo cáo chính thức lên GOOGLEQA
- `xTS_Tool` kết nối SFTP trực tiếp từ Windows lên GOOGLEQA:
  Thư mục: `/home/googleqa/GOOGLEQA/Official_Test_results/{Project_Model}/{SW_Version}/`
- Upload toàn bộ:
  1. Các file Excel chi tiết `03.LGE_..._Result_Final_...xlsx` (đủ cả 9 bài test nếu có).
  2. File Summary chính thức: `Nissan_{Model_Code}_Google Certification Summary_{Short_SW}.xlsx`.
- Đồng thời copy 1 bản lưu trữ sang thư mục `ResultFinal/` trên máy chủ test runner (hỗ trợ cấu hình linh hoạt Server 66, Server 44...).
- *Tham khảo chi tiết các trường hợp biên tại [05_CRITICAL_NOTES_AND_EDGE_CASES.md](./05_CRITICAL_NOTES_AND_EDGE_CASES.md).*
