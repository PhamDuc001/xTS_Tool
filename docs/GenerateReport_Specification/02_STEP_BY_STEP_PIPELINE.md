# Quy Trình Chi Tiết Từng Bước (Step-by-Step Pipeline)

Tài liệu này ghi lại chi tiết toàn bộ **8 bước** thực thi từ dữ liệu thô `01.Full/` đến khi xuất bản báo cáo chính thức lên server GOOGLEQA.
Quy trình được tối ưu theo kiến trúc phân tách 2 phần: **Luồng báo cáo nhanh (Fast-Track: Bước 1–7)** và **Gói lưu trữ nặng độc lập (Bước 8)**.

---

## Bước 1: Chạy công cụ `ReportGenerator.py` trên Test Runner Server
- **Vị trí dữ liệu thô (`01.Full/`):**
  Thư mục do kỹ sư chỉ định trên giao diện UI (ví dụ: `/home/lge/GoogleQA/Report_tmp/01.Full/` hoặc cấu hình linh hoạt theo dự án).
  Các thư mục bộ test có mặt: `01.ATS`, `01.AtsInCar`, `01.AtsInteractive`, `01.AtsMultidevice`, `01.BFG`, `01.CTS`, `01.CTSonGSI`, `01.CTS_Verifier`, `01.STS`, `01.VTS`.
- **Lệnh thực thi qua SSH:**
  ```bash
  python3 /home/lge/Environment/tools/GenerReport_Update_0623/ReportGenerator.py -p /home/lge/GoogleQA/Report_tmp/01.Full/
  ```
- **Kết quả sinh ra tại thư mục cha (`Report_tmp/`):**
  1. `00.Internal/`: Chứa các folder `*Results` (ví dụ `CTSResults/`, `ATSResults/`...) bên trong gồm các file báo cáo HTML, XML và thư mục `DataforAuto/`. Đồng thời chứa các gói nén `02.LGE_{Model}_{Suite}_Result_{SW_Version}.zip`.
  2. `00.OEM_APFE/` và file nén `00.OEM_APFE.zip`.
  3. `00.OEM_APFE_UPLOAD/` và file nén `00.OEM_APFE_UPLOAD.zip`.
  4. Tại `01.Full/`: Mỗi folder bộ test được nén thành file `.zip` tương ứng (`01.CTS.zip`, `01.ATS.zip`...).

---

## Bước 2: Đồng bộ dữ liệu phân tích sang Server APTRA (Critical Input Path)
- **Mục đích:** Cung cấp dữ liệu đầu vào bắt buộc và tối thiểu nhất để công cụ phân tích APTRA có thể khởi chạy.
- **Server đích:** `loghub.lge.com` (`aptra:aptra`), thư mục:
  `/home/aptra/APTRA/{Project_Model}/{SW_Version}/`
- **Phương thức:** Lệnh `curl` SFTP song song trực tiếp từ Test Runner Server:
  - Chỉ copy các thư mục `*Results/` trong `00.Internal/` (chứa các file HTML, XML và thư mục con `DataforAuto/`).
- **Điểm cải tiến tối ưu:**
  - **KHÔNG upload** các file nén nặng (`01.*.zip`, `00.OEM*.zip`, `02.*.zip`) ở bước này.
  - Tránh tình trạng pipeline bị nghẽn và chờ đợi 15–30 phút chỉ để tải file lưu trữ trước khi có thể phân tích.

---

## Bước 3: Chạy công cụ phân tích APTRA & Xác nhận (Analysis & Confirm)
- **Cơ chế phối hợp:**
  - `xTS_Tool` hiển thị Pop-up thông báo:
    > ℹ️ *Đã upload dữ liệu sang APTRA thành công. Vui lòng request chạy server APTRA để tạo file báo cáo. Bấm [Đã Hoàn Thành] sau khi server APTRA chạy xong.*
  - Kỹ sư request chạy công cụ phân tích trên hệ thống APTRA.
  - Khi kỹ sư bấm [Đã Hoàn Thành], Tool tự động kiểm tra sự xuất hiện của file `*_summary.csv` trên APTRA và chuyển sang Bước 4.

---

## Bước 4: Tải trực tiếp các file kết quả về Local Windows
- **Nguồn tải:**
  - Từ APTRA (`aptra@loghub.lge.com:/home/aptra/APTRA/{Project}/{SW}/`):
    Tải các file `.xlsx` kết quả: `ATSResult.xlsx`, `CTSResult.xlsx`, `BFGResult.xlsx`, `STSResult.xlsx`, `CTSonGSIResult.xlsx`, `AtsInteractiveResults.xlsx`, `AtsMultideviceResults.xlsx`, `VTSResult.xlsx`.
  - Từ GOOGLEQA (`googleqa@loghub.lge.com`):
    Tải file Summary mẫu của version trước (`Nissan_{Model}_Google Certification Summary_{Previous_SW}.xlsx`).
- **Đích lưu:** Thư mục tạm `temp_report/` trên máy trạm Windows.

---

## Bước 5: Chuẩn hóa & Làm sạch các file Excel kết quả `03.*.xlsx`
Xử lý bằng thư viện `openpyxl` trên Python Windows cực nhanh (< 1 giây):
1. **Đổi tên file theo mẫu chuẩn:**
   - Cú pháp: `03.LGE_Nissan_AIVI_Full_12.3_{Model_Code}_{Suite}_Result_Final_{SW_Version}.xlsx`
   - Ví dụ: `03.LGE_Nissan_AIVI_Full_12.3_PZ1D_CTS_Result_Final_YAK.31.04.10.xlsx`.
   - Áp dụng đầy đủ cho cả các suite đặc thù: `AtsIncar`, `AtsInteractive`, `AtsMultidevice`, `BFG`.
2. **Điền Header (Sheet `Test Summary`):**
   - `C3`: Project (Model) Full (vd: `Nissan_AIVI_Full_12.3_PZ1D_26MY`)
   - `C4`: HW (PCB) version (vd: `C`)
   - `C5`: SW version (vd: `YAK.31.04.10`) - **BẮT BUỘC** cập nhật đúng SW version mới nhất.
   - `C6`: MICOM version (vd: `v3.27.37`)
   - `G2`: OEM Delivery (vd: `09/11/2026`, ép format text `@`)
   - `G3`: Test Start (vd: `09/07/2026`, ép format text `@`)
   - `G4`: Test End (vd: `09/10/2026`, ép format text `@`)
   - `G6`: Tester (vd: `duc4.pham`)
   - *Ô `C7`:* Giữ nguyên chuỗi phiên bản suite (vd: `CTS 14_r13`, `STS 14_sts-r55`, `VTS 14_r13`, `ATS 2026_r2`) làm nguồn trích xuất version sang bảng Summary.
3. **Làm sạch cấu trúc hàng & An toàn Unmerge:**
   - Quét và unmerge toàn bộ các merged ranges giao cắt với hàng 15 đến 40 trước khi xóa.
   - Xóa các dòng thừa từ 15 đến 40 (`ws.delete_rows(15, ws.max_row - 14)`).
   - Bảo toàn công thức `=E12/C12` tại ô `H12` và các sheet con (`Test Result_Detail`, `Failed Test Cases`).
4. **Loại bỏ chế độ lọc (AutoFilter):**
   - Mặc định các file xuất từ APTRA gán bộ lọc AutoFilter tại dòng tiêu đề của sheet `Test Result_Detail`.
   - Tool tự động xóa bỏ chế độ lọc (`ws.auto_filter.ref = None`) cho toàn bộ các sheet trong file `03.*.xlsx`, giúp bảng tính sạch sẽ, không hiển thị các nút mũi tên dropdown lọc dữ liệu.

---

## Bước 6: Tạo & Cập nhật file Google Certification Summary
1. **Khối bảng mới trong sheet `Summary`:**
   - Dò tìm khối bảng của version trước (quét ngược từ dưới lên tìm ô `"Summary"` và `"HW (PCB) version"`).
   - Dán khối bảng mới cách 2 dòng trống.
   - **Cập nhật Metadata khối mới:** Bắt buộc ghi đè `HW version` (Row 19), `SW version` (Row 20 - ví dụ `YAK.31.04.10`), và `MICOM version` (Row 21).
2. **Quy tắc đặt tên file Summary đầu ra:**
   - Bắt buộc lấy theo `Short_SW` mới nhất: `Nissan_{Model_Code}_Google Certification Summary_{Short_SW}.xlsx`.
   - Ví dụ: Với SW `YAK.31.04.10`, file sinh ra là `Nissan_PZ1D_Google Certification Summary_31.04.10.xlsx` (không giữ tên cũ `31.03.30` của template).
3. **Đồng bộ động phiên bản vào cột `Test Category` (Cột C):**
   - Áp dụng cho **TOÀN BỘ 10 Test Suite** (`ATS`, `ATS-In-Car`, `ATS_Interactive`, `ATS-Multidevice`, `BFG`, `CTS`, `CTSonGSI`, `STS`, `VTS`, `CTS-Verifier`).
   - Trích xuất version từ ô `C7` của file `03.` tương ứng (hoặc thuộc tính `suite_version` từ XML đối với `CTS-Verifier`).
   - Format: `<Base_Suite_Name> (<Version>)`, ví dụ: `CTS (14_r13)`, `STS (14_sts-r55)`, `VTS (14_r13)`, `ATS (2026_r2)`, `CTS-Verifier (14_r13)`.
4. **Trích xuất 7 chỉ số kiểm thử & Fallback tính toán:**
   - Đọc ô `D3:J3` của sheet `Test Result_Detail`. Nếu là `None` (chưa cache formula), tự động fallback cộng dồn từ các dòng module (Pass, Fail, Assumption, Ignored, Total Tests, Module Done, Total Module).
   - Với `CTS_Verifier`: Đọc thẻ `<Summary>` trong file XML `test_result.xml`.
   - Nếu suite không chạy: Để ô trống (`None`), không điền 0.
   - Dòng cuối cùng: Điền công thức `=SUM(D...:D...)` đến `=SUM(J...:J...)`.
5. **Cập nhật sheet `Nissan Fail Module List`:**
   - Xóa sạch dữ liệu cũ từ **dòng 3 trở đi** (`ws.delete_rows(3, ws.max_row - 2)`), giữ nguyên hàng 1 và hàng 2.
   - Ghi danh sách module có `Failed > 0`. Nếu không có lỗi, giữ bảng trắng từ dòng 3.
6. **Cập nhật sheet `Nissan Fail TestCase List`:**
   - Xóa sạch dữ liệu cũ từ **dòng 3 trở đi**, giữ nguyên hàng 1 và hàng 2.
   - Ghi danh sách testcase fail với số thứ tự tăng dần liên tục (1, 2, 3...).

---

## Bước 7: Phát hành báo cáo Excel lên GOOGLEQA (Fast-Track Publication)
- **Mục đích:** Đưa toàn bộ báo cáo Excel chuẩn hóa lên server GOOGLEQA ngay lập tức sau khi xử lý xong ở Local.
- **Phương thức:** SFTP trực tiếp từ máy trạm Windows lên GOOGLEQA:
  - Thư mục đích: `/home/googleqa/GOOGLEQA/Official_Test_results/{Project_Model}/{SW_Version}/`
- **Danh sách file phát hành:**
  1. Toàn bộ các file Excel chi tiết: `03.LGE_..._Result_Final_...xlsx` (dung lượng ~50–80 KB mỗi file).
  2. File Summary chính thức: `Nissan_{Model_Code}_Google Certification Summary_{Short_SW}.xlsx`.
- **Lưu trữ nội bộ trên máy runner:** Đồng thời copy 1 bản các file Excel này sang thư mục `ResultFinal/` trên máy chủ test runner.
- **Hiệu năng:** Thời gian upload chỉ mất **1–2 giây**. Kết thúc Bước 7, toàn bộ mục tiêu báo cáo kết quả kiểm thử đã hoàn thành!

---

## Bước 8: Đồng bộ gói lưu trữ nặng sang GOOGLEQA (01.*, 00.OEM, 02.*) [Tùy chọn / Độc lập]
- **Mục đích:** Lưu trữ bản gốc các bộ test thô và gói OEM phục vụ audit và release lâu dài của Google.
- **Server đích:** `loghub.lge.com` (`googleqa:googleqa`), thư mục:
  `/home/googleqa/GOOGLEQA/Official_Test_results/{Project_Model}/{SW_Version}/`
- **Phương thức:** Lệnh `curl` SFTP Server-to-Server trực tiếp giữa Test Runner Server và GOOGLEQA:
  - Đồng bộ toàn bộ các file nén thô trong `01.Full/` (`01.CTS.zip`, `01.VTS.zip`...).
  - Đồng bộ 2 file nén OEM: `00.OEM_APFE.zip` và `00.OEM_APFE_UPLOAD.zip`.
  - Đồng bộ các gói nén `02.LGE_*.zip` trong `00.Internal/`.
- **Cơ chế kích hoạt:**
  - **Mặc định:** Không chạy trong luồng chính (Fast-Track dừng tại Bước 7).
  - **Tự động:** Kỹ sư có thể tích chọn `[x] 📦 Tự động upload gói zip nặng (Bước 8)` trên UI trước khi bấm *Chạy Toàn Bộ*.
  - **Thủ công:** Kỹ sư có thể bấm nút **"Chạy Bước Này"** tại dòng Bước 8 bất kỳ lúc nào khi rảnh rỗi hoặc chạy vào cuối ngày mà không lo làm nghẽn luồng công việc chính.
- *Tham khảo chi tiết các trường hợp biên tại [05_CRITICAL_NOTES_AND_EDGE_CASES.md](./05_CRITICAL_NOTES_AND_EDGE_CASES.md).*
