# Quy Trình Chi Tiết Từng Bước (Step-by-Step Pipeline)

Tài liệu này ghi lại chi tiết từng thao tác kỹ thuật, các lệnh shell/python tương ứng, đường dẫn input/output và trạng thái kiểm tra thực tế đã thực hiện.

---

## Bước 1: Chuẩn bị dữ liệu kết quả chạy test thô (Raw Test Suites)
- **Vị trí trên Server 66 (`10.218.158.66`):**
  `/home/lge/GoogleQA/Report_tmp/01.Full/`
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
- **Đặc điểm:** Mỗi thư mục con chứa kết quả chạy bài test gồm các file log (`test_result.xml`, logs thiết bị, screenshot,...).

---

## Bước 2: Chạy công cụ `ReportGenerator.py` trên Server 66
- **Công cụ:**
  `/home/lge/Environment/tools/GenerReport_Update_0623/ReportGenerator.py`
- **Lệnh thực thi:**
  ```bash
  python3 /home/lge/Environment/tools/GenerReport_Update_0623/ReportGenerator.py -p /home/lge/GoogleQA/Report_tmp/01.Full/
  ```
- **Kết quả sinh ra tại `/home/lge/GoogleQA/Report_tmp/`:**
  1. `00.Internal/`: Chứa các folder `*Results` (ví dụ `CTSResults/`, `ATSResults/`...) bên trong gồm các file báo cáo HTML, XML và thư mục `DataforAuto/`. Đồng thời chứa các gói nén `02.LGE_{Model}_{Suite}_Result_{SW_Version}.zip`.
  2. `00.OEM_APFE/` và file nén `00.OEM_APFE.zip`.
  3. `00.OEM_APFE_UPLOAD/` và file nén `00.OEM_APFE_UPLOAD.zip`.
  4. Tại `01.Full/`: Mỗi folder bộ test được nén thành file `.zip` tương ứng (vd: `01.CTS.zip`, `01.ATS.zip`...).

---

## Bước 3: Đồng bộ dữ liệu sang Server GOOGLEQA
- **Mục đích:** Lưu trữ bản gốc các bộ test phục vụ chứng chỉ Google.
- **Server đích:** `loghub.lge.com` (`googleqa:googleqa`), thư mục gốc `/nas/GOOGLEQA/`.
- **Thư mục tạo:**
  `/home/googleqa/GOOGLEQA/Official_Test_results/Nissan_AIVI_Full_12.3_PZ1D_B7/YAK.31.03.30/` (hoặc tên model mới `PZ1D_26MY`).
- **Nội dung copy sang:**
  - Toàn bộ các folder và file `.zip` trong `01.Full/` (`01.ATS`, `01.CTS`, `01.VTS`...).
  - Hai file zip OEM: `00.OEM_APFE.zip` và `00.OEM_APFE_UPLOAD.zip`.
- **Phương thức thực hiện:** SFTP / rsync / curl qua mạng nội bộ LG.

---

## Bước 4: Đồng bộ dữ liệu sang Server APTRA
- **Mục đích:** Cung cấp input đầu vào cho công cụ phân tích số liệu của hệ thống APTRA.
- **Server đích:** `loghub.lge.com` (`aptra:aptra`), thư mục gốc `/nas/APTRA/`.
- **Thư mục tạo:**
  `/home/aptra/APTRA/Nissan_AIVI_Full_12.3_PZ1D_B7/YAK.31.03.30/`
- **Nội dung copy sang:**
  - Copy toàn bộ các folder `*Results/` trong `00.Internal/` (chứa các file HTML và thư mục `DataforAuto` có chứa các file XML chi tiết bài test).

---

## Bước 5: Chạy công cụ phân tích APTRA (Analysis Engine)
- **Mục đích:** Phân tích các XML trong `DataforAuto/` và tổng hợp thành bảng tính Excel và chỉ số Pass/Fail/Assumption Failure.
- **Kết quả sinh ra tại thư mục APTRA:**
  - Các file Excel kết quả chi tiết:
    `ATSResult.xlsx`, `CTSResult.xlsx`, `BFGResult.xlsx`, `STSResult.xlsx`, `CTSonGSIResult.xlsx`, `AtsInteractiveResults.xlsx`, `AtsMultideviceResults.xlsx`...
  - File tóm tắt chỉ số: `YAK.31.03.30_summary.csv`.
  - Các file metrics: `YAK.31.03.30_defect.dat`, `YAK.31.03.30_pass.dat`, `YAK.31.03.30_pass_tc.dat`.

---

## Bước 6: Thu thập file `.xlsx` về Server 66
- **Thư mục tạo trên Server 66:**
  `/home/lge/GoogleQA/Report_tmp/ResultFinal/`
- **Nội dung copy về:**
  - Tải toàn bộ các file `*Result.xlsx` từ APTRA về thư mục `ResultFinal/`.

---

## Bước 7: Đổi tên các file kết quả theo chuẩn `03.`
- **Quy tắc đổi tên:**
  Dựa trên tên file `02.` tương ứng trong `00.Internal`:
  - Tên cũ: `02.LGE_{Model}_{Suite}_Result_{SW_Version}.zip`
  - Tên mới cho file `.xlsx`: `03.LGE_{Model}_{Suite}_Result_Final_{SW_Version}.xlsx`
- **Ví dụ thực tế:**
  - `ATSResult.xlsx` ➔ `03.LGE_Nissan_AIVI_Full_12.3_PZ1D_ATS_Result_Final_YAK.31.03.30.xlsx`
  - `CTSResult.xlsx` ➔ `03.LGE_Nissan_AIVI_Full_12.3_PZ1D_CTS_Result_Final_YAK.31.03.30.xlsx`

---

## Bước 8: Chuẩn hóa và làm sạch file Excel `03.*.xlsx`
Thao tác thực hiện trên từng file `.xlsx` tại `ResultFinal/`:
1. **Sheet `Test Summary`:**
   - Điền thông tin vào các ô:
     - `C3`: Project (Model) (vd: `Nissan_AIVI_Full_12.3_PZ1D_26MY`)
     - `C4`: HW (PCB) version (vd: `C`)
     - `C5`: SW version (vd: `YAK.31.03.30`)
     - `C6`: MICOM version (vd: `v3.27.37`)
     - `G2`: OEM Delivery (vd: `09/11/2026`)
     - `G3`: Test Start (vd: `09/07/2026`)
     - `G4`: Test End (vd: `09/10/2026`)
     - `G6`: Tester (vd: `duc4.pham`)
   - Unmerge ô `B17:F17`.
   - Xóa bỏ toàn bộ từ hàng 15 đến hàng 40 (bỏ phần hướng dẫn tiếng Hàn cũ và ô trống thừa).
   - Đảm bảo giữ nguyên các công thức `=E12/C12` và các sheet con (`Test Result_Detail`, `Failed Test Cases`).

---

## Bước 9: Chuẩn bị file Google Certification Summary từ version mẫu
- **Đường dẫn lấy mẫu (cấu hình qua UI):**
  `/home/googleqa/GOOGLEQA/Official_Test_results/{Model_Reference}/{Previous_Version}/`
- **Ví dụ mẫu:**
  `/home/googleqa/GOOGLEQA/Official_Test_results/Nissan_AIVI_Full_12.3_P61R/YAK.31.06.38.U0M/Nissan_P61R_Google Certification Summary.xlsx`
- **Copy về Server 66:**
  `/home/lge/GoogleQA/Report_tmp/Nissan_P61R_Google Certification Summary.xlsx`

---

## Bước 10: Cập nhật khối bảng phiên bản mới vào sheet `Summary`
1. **Sao chép block mẫu:**
   - Tìm khối bảng của version trước (gồm 15 dòng, ví dụ dòng 132 – 146).
   - Nếu không tìm thấy khối bảng hợp lệ -> **Bật Warning cảnh báo ngay**.
   - Copy format và dán vào dòng mới cách 2 dòng trống (dòng 149 – 163).
2. **Cập nhật Metadata block mới:**
   - Dòng 149: `HW (PCB) version `: `C`
   - Dòng 150: `SW version `: `YAK.31.03.30`
   - Dòng 151: `MICOM version `: `v3.27.37`
3. **Trích xuất 7 chỉ số từ các file `03.*.xlsx`:**
   - Với mỗi bài test (CTS, ATS, BFG, STS, ...), mở sheet `Test Result_Detail` của file tương ứng.
   - Tại dòng 3: lấy 7 giá trị từ ô `D3` đến `J3` (`Pass`, `Fail`, `Assumption Failure`, `Ignored`, `Total Tests`, `Module Done`, `Total Module`).
   - Điền vào dòng tương ứng trong khối bảng mới.
4. **Cập nhật công thức Summary:**
   - Dòng cuối của block điền công thức `=SUM(D153:D162)` đến `=SUM(J153:J162)`.

---

## Bước 11: Cập nhật sheet `Nissan Fail Module List`
1. Quét cột `Fail` trong bảng mới của sheet `Summary`.
2. Nếu có bộ test có `Fail > 0` (ví dụ `CTS` có `Fail = 1`):
   - Mở file kết quả tương ứng (`03...CTS_Result_Final...xlsx`).
   - Vào sheet `Test Result_Detail`, quét từ dòng 5 trở đi.
   - Lọc các module có **`Failed > 0`**.
   - Copy 7 giá trị từ Cột C đến Cột I (`Module`, `Passed`, `Failed`, `Assumption Failure`, `Ignored`, `Total Tests`, `Done`).
   - Ghi vào sheet `Nissan Fail Module List` của file Summary:
     - Cột B: Tên suite (`CTS`)
     - Cột C - I: 7 giá trị vừa copy
     - Cột J: để trống
3. **Lưu ý:** Nếu không có test case fail nào (`Fail = 0`), giữ nguyên sheet và bảng header ở dòng 2, để trống phần data từ dòng 3.

---

## Bước 12: Cập nhật sheet `Nissan Fail TestCase List`
1. Với bộ test có `Fail > 0`:
   - Mở sheet `Failed Test Cases` của file kết quả tương ứng.
   - Quét các dòng từ dòng 5 trở đi:
     - Cột C: `Module`
     - Cột D: `Test Case`
   - Ghi vào sheet `Nissan Fail TestCase List` của file Summary:
     - Cột A (`No`): số thứ tự tăng dần (`1, 2, 3...`)
     - Cột B (`Test Category`): tên suite (`CTS`)
     - Cột C (`Module`): tên module lỗi
     - Cột D (`Test Case`): tên test case lỗi cụ thể
2. **Lưu ý:** Nếu không có test case fail, giữ nguyên sheet và header ở dòng 2, để trống dữ liệu từ dòng 3.

---

## Bước 13: Đóng gói và phát hành chính thức lên GOOGLEQA
- Thư mục phát hành chính thức:
  `/home/googleqa/GOOGLEQA/Official_Test_results/Nissan_AIVI_Full_12.3_PZ1D_26MY/YAK.31.03.30/`
- Nội dung gói phát hành đầy đủ gồm:
  1. Thư mục và file `.zip` bài test (`01.*`).
  2. Các gói nén báo cáo nội bộ (`02.*.zip`).
  3. Toàn bộ các file Excel kết quả chi tiết đã chuẩn hóa (`03.*.xlsx`).
  4. File Summary chính thức: `Nissan_{Model}_Google Certification Summary_{Short_Version}.xlsx`.
