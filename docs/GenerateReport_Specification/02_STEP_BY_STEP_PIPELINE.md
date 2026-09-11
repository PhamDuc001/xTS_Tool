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
   - Ví dụ: `03.LGE_Nissan_AIVI_Full_12.3_PZ1D_CTS_Result_Final_YAK.31.03.30.xlsx`.
2. **Điền Header (Sheet `Test Summary`):**
   - `C3`: Project (Model) Full (vd: `Nissan_AIVI_Full_12.3_PZ1D_26MY`)
   - `C4`: HW (PCB) version (vd: `C`)
   - `C5`: SW version (vd: `YAK.31.03.30`)
   - `C6`: MICOM version (vd: `v3.27.37`)
   - `G2`: OEM Delivery (vd: `09/11/2026`)
   - `G3`: Test Start (vd: `09/07/2026`)
   - `G4`: Test End (vd: `09/10/2026`)
   - `G6`: Tester (vd: `duc4.pham`)
3. **Làm sạch cấu trúc hàng:**
   - Unmerge ô `B17:F17`.
   - Xóa các dòng từ 15 đến 40 (`ws.delete_rows(15, ws.max_row - 14)`).
   - Bảo toàn công thức `=E12/C12` và các sheet con (`Test Result_Detail`, `Failed Test Cases`).

---

## Bước 8: Tạo & Cập nhật file Google Certification Summary
1. **Khối bảng mới trong sheet `Summary`:**
   - Dò tìm khối bảng của version trước (quét ngược từ dưới lên tìm ô `"Summary"` và `"HW (PCB) version"`).
   - Dán khối bảng mới cách 2 dòng trống.
   - Điền HW version, SW version, MICOM version vào đầu khối bảng.
2. **Trích xuất 7 chỉ số kiểm thử:**
   - Với mỗi bộ test (ATS, CTS, BFG, STS, CTSonGSI, AtsInteractive, AtsMultidevice, VTS):
     - Mở sheet `Test Result_Detail` của file `03.` tương ứng.
     - Lấy 7 giá trị tại ô `D3:J3`: `Pass`, `Fail`, `Assumption Failure`, `Ignored`, `Total Tests`, `Module Done`, `Total Module`.
     - Điền vào dòng của suite tương ứng trong sheet `Summary`.
   - Với `CTS_Verifier`: Đọc trực tiếp từ file XML `01.CTS_Verifier/*/test_result.xml` để lấy số liệu `Pass`, `Total`, `Module Done`.
   - Dòng cuối cùng của khối bảng: Điền công thức `=SUM(...)`.
3. **Cập nhật sheet `Nissan Fail Module List`:**
   - Xóa trắng dữ liệu cũ từ dòng 3 trở đi.
   - Nếu có suite có `Fail > 0`: Quét sheet `Test Result_Detail` từ dòng 5 trở đi, lọc các module có **`Failed > 0`**, copy 7 cột (`Module`, `Passed`, `Failed`, `Assumption Failure`, `Ignored`, `Total Tests`, `Done`) vào bảng.
   - Nếu `Fail = 0`: Để trống dữ liệu từ dòng 3, giữ nguyên khung bảng dòng 2.
4. **Cập nhật sheet `Nissan Fail TestCase List`:**
   - Xóa trắng dữ liệu cũ từ dòng 3 trở đi.
   - Nếu có suite có `Fail > 0`: Mở sheet `Failed Test Cases` của file suite đó, copy danh sách testcase fail cụ thể sang bảng với số thứ tự `No` tăng dần (1, 2, 3...).
   - Nếu `Fail = 0`: Để trống dữ liệu từ dòng 3, giữ nguyên khung bảng dòng 2.

---

## Bước 9: Phát hành gói báo cáo chính thức lên GOOGLEQA
- `xTS_Tool` kết nối SFTP trực tiếp từ Windows lên GOOGLEQA:
  Thư mục: `/home/googleqa/GOOGLEQA/Official_Test_results/{Project_Model}/{SW_Version}/`
- Upload toàn bộ:
  1. Các file Excel chi tiết `03.LGE_..._Result_Final_...xlsx`.
  2. File Summary chính thức: `Nissan_{Model_Code}_Google Certification Summary_{Short_SW}.xlsx`.
- Đồng thời copy 1 bản lưu trữ sang Server 66 (`/home/lge/GoogleQA/Report_tmp/ResultFinal/`).
