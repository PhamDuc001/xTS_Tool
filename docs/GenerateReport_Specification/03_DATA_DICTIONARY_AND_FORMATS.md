# Từ Điển Dữ Liệu & Định Dạng Bảng Tính (Data Dictionary & Excel Formats)

Tài liệu này cung cấp chi tiết vị trí ô (cell coordinates), kiểu dữ liệu, định dạng (formatting) và dữ liệu mẫu thực tế trích xuất từ các file báo cáo.

---

## 1. Từ điển dữ liệu đầu vào (Input Metadata Dictionary)

Các thông số này do người dùng nhập trên giao diện của `xTS_Tool`:

| Tham số | Ý nghĩa | Ví dụ thực tế | Kiểu dữ liệu | Phạm vi ảnh hưởng |
| :--- | :--- | :--- | :---: | :--- |
| **`Project (Model)`** | Tên đầy đủ của dự án / Model xe | `Nissan_AIVI_Full_12.3_PZ1D_26MY` | String | Điền vào ô `C3` của các file `03.*.xlsx`, tạo folder lưu trữ trên GOOGLEQA/APTRA |
| **`Model Short Code`** | Mã model viết tắt | `PZ1D` (hoặc `P61R`) | String | Dùng đặt tên file `03.` và file `Summary.xlsx` |
| **`HW (PCB) version`** | Phiên bản phần cứng bo mạch | `C` | String | Điền vào ô `C4` file `03.`, dòng `HW` của file Summary |
| **`SW version`** | Phiên bản phần mềm đầy đủ | `YAK.31.03.30` | String | Điền vào ô `C5` file `03.`, dòng `SW` file Summary, tên folder version |
| **`SW Short Version`** | Phiên bản phần mềm rút gọn | `31.03.30` | String | Dùng trong tên file Summary: `Nissan_{Model}_Google Certification Summary_{Short_SW}.xlsx` |
| **`MICOM version`** | Phiên bản chip vi điều khiển MICOM | `v3.27.37` | String | Điền vào ô `C6` file `03.`, dòng `MICOM` file Summary |
| **`OEM Delivery`** | Ngày bàn giao cho OEM (Nissan) | `09/11/2026` | String (`MM/DD/YYYY`) | Điền vào ô `G2` file `03.*.xlsx` |
| **`Test Start`** | Ngày bắt đầu thực hiện test | `09/07/2026` | String (`MM/DD/YYYY`) | Điền vào ô `G3` file `03.*.xlsx` |
| **`Test End`** | Ngày kết thúc test | `09/10/2026` | String (`MM/DD/YYYY`) | Điền vào ô `G4` file `03.*.xlsx` |
| **`Tester`** | Tên/ID kỹ sư thực hiện | `duc4.pham` | String | Điền vào ô `G6` file `03.*.xlsx` |
| **`Previous Summary Path`**| Đường dẫn file summary mẫu | `/home/googleqa/GOOGLEQA/.../Summary.xlsx` | Path | Dùng làm template copy bảng lịch sử |

---

## 2. Cấu trúc File `03.LGE_{Model}_{Suite}_Result_Final_{SW}.xlsx`

### Sheet 1: `Test Summary` (14 dòng sạch sẽ)
Sau khi chuẩn hóa, sheet này chỉ gồm **14 hàng** (đã unmerge `B17:F17` và xóa hàng 15-40):

```
+----+-------------------+---------------------------------------------+----+---+---------------+------------+---+---+
|    |         B         |                      C                      | D  | E |       F       |     G      | H | I |
+----+-------------------+---------------------------------------------+----+---+---------------+------------+---+---+
|  1 | Test Information  |                                             |    |   |               |            |   |   |
|  2 | Division          | VS Smart Validation System Development Team |    |   | OEM Delivery  | 09/11/2026 |   |   |
|  3 | Project (Model)   | Nissan_AIVI_Full_12.3_PZ1D_26MY             |    |   | Test Start    | 09/07/2026 |   |   |
|  4 | HW (PCB) version  | C                                           |    |   | Test End      | 09/10/2026 |   |   |
|  5 | SW version        | YAK.31.03.30                                |    |   | Variant       |            |   |   |
|  6 | MICOM version     | v3.27.37                                    |    |   | Tester        | duc4.pham  |   |   |
|  7 | Test Suite        | CTS 14_r12                                  |    |   | Version Type  | user       |   |   |
|  8 | Fingerprint       | nissan/car-aivi2_n/aivi2_n_full:14/...      |    |   |               |            |   |   |
|  9 |                   |                                             |    |   |               |            |   |   |
| 10 | Test Summary      |                                             |    |   |               |            |   |   |
| 11 |                   | Total                                       |Tested|Passed| Failed    | Done       |Pass Rate|Remark|
| 12 | Test Case         | 2,210,385                                   |2210385|2210384| 1        |            |=E12/C12|      |
| 13 | Implication       |                                             |    |   |               |            |   |   |
+----+-------------------+---------------------------------------------+----+---+---------------+------------+---+---+
```

- **Vùng Merged Cells hợp lệ:** `C2:E2`, `G2:I2`, `C3:E3`, `G3:I3`, `C4:E4`, `G4:I4`, `C5:E5`, `G5:I5`, `C6:E6`, `G6:I6`, `C7:E7`, `G7:I7`, `C8:I8`, `I11:K11`, `I12:K12`, `C13:K13`.
- **Định dạng ô:** Font `Calibri 11.0`, căn giữa `center/center`, viền `thin` xung quanh các ô có dữ liệu.

---

### Sheet 2: `Test Result_Detail`
Nơi chứa kết quả chi tiết từng module test và dòng tổng hợp số liệu tại hàng 3:
- **Hàng 2 (Header tóm tắt):**
  `C2: Total | D2: Pass | E2: Fail | F2: Assumption Failure | G2: Ignored | H2: Total Tests | I2: Done(=true) | J2: Total Module Count`
- **Hàng 3 (Dòng dữ liệu trích xuất sang Summary):**
  - `D3`: Pass count (`=SUM(D5:D50000)`) ➔ Giá trị số (vd CTS: `2210384`)
  - `E3`: Fail count (`=SUM(E5:E50000)`) ➔ Giá trị số (vd CTS: `1`)
  - `F3`: Assumption Failure (`=SUM(F5:F50000)`) ➔ Giá trị số (vd CTS: `10403`)
  - `G3`: Ignored (`=SUM(G5:G50000)`) ➔ Giá trị số (vd CTS: `768`)
  - `H3`: Total Tests (`=SUM(H5:H50000)`) ➔ Giá trị số (vd CTS: `2221556`)
  - `I3`: Module Done (`=COUNTIF(I5:I50000,"t*")`) ➔ Giá trị số (vd CTS: `832`)
  - `J3`: Total Module Count (`=COUNTA(I5:I50000)`) ➔ Giá trị số (vd CTS: `832`)
- **Hàng 4 (Header chi tiết):**
  `B4: No | C4: Module | D4: Passed | E4: Failed | F4: Assumption Failure | G4: Ignored | H4: Total Tests | I4: Done | J4: Remark`
- **Hàng 5 trở đi:** Danh sách từng module. Nếu module nào có `Failed > 0` (cột E), module đó sẽ được trích xuất sang sheet `Nissan Fail Module List`.

---

### Sheet 3: `Failed Test Cases`
- **Hàng 4 (Header):**
  `B4: No | C4: Module | D4: Test Case`
- **Hàng 5 trở đi:** Danh sách từng testcase bị fail cụ thể:
  - `B5`: `1`
  - `C5`: `arm64-v8a CtsAppSecurityHostTestCases`
  - `D5`: `android.appsecurity.cts.ListeningPortsTest#testNoRemotelyAccessibleListeningUdpPorts`

---

## 3. Cấu trúc File `Nissan_{Model}_Google Certification Summary_{Version}.xlsx`

### Sheet 1: `Summary`
Gồm khối bảng 15 dòng tổng hợp cho version:

| Dòng | Cột B | Cột C | Cột D (Pass) | Cột E (Fail) | Cột F (Assumption Failure) | Cột G (Ignored) | Cột H (Total Tests) | Cột I (Module Done) | Cột J (Total Module) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | HW (PCB) version | C | | | | | | | |
| **2** | SW version | YAK.31.03.30 | | | | | | | |
| **3** | MICOM version | v3.27.37 | | | | | | | |
| **4** | | **Test Category** | **Pass** | **Fail** | **Assumption Failure** | **Ignored** | **Total Tests** | **Module Done** | **Total Module** |
| **5** | Nissan P61R | ATS (2026_r2) | 1,312 | 0 | 358 | 14 | 1,684 | 96 | 96 |
| **6** | | ATS-In-Car (2026_r2) | *None* | *None* | *None* | *None* | *None* | *None* | *None* |
| **7** | | ATS_Interactive (2026_r2) | 30 | 0 | 5 | 0 | 35 | 7 | 7 |
| **8** | | ATS-Multidevice (2026_r2) | 0 | 0 | 1 | 0 | 1 | 1 | 1 |
| **9** | | BFG (2026_r2) | 15 | 0 | 0 | 0 | 15 | 7 | 7 |
| **10**| | CTS (14_r12) | 2,210,384| 1 | 10,403 | 768 | 2,221,556| 832 | 832 |
| **11**| | CTSonGSI (14_r12) | 178,116 | 0 | 7,967 | 580 | 186,663 | 413 | 413 |
| **12**| | STS (sts-r54) | 1,045 | 0 | 469 | 1 | 1,515 | 25 | 25 |
| **13**| | VTS | 80,050 | 0 | 53 | 38,154 | 118,257 | 370 | 370 |
| **14**| | CTS-Verifier (14_r12) | 50 | 0 | 0 | 0 | 50 | 1 | 1 |
| **15**| | **Summary** | `=SUM(D5:D14)` | `=SUM(E5:E14)` | `=SUM(F5:F14)` | `=SUM(G5:G14)` | `=SUM(H5:H14)` | `=SUM(I5:I14)` | `=SUM(J5:J14)` |

---

### Sheet 2: `Nissan Fail Module List`
Bảng liệt kê các module bị Fail:

| Cột A | Cột B (Test Category) | Cột C (Module) | Cột D (Passed) | Cột E (Failed) | Cột F (Assumption Failure) | Cột G (Ignored) | Cột H (Total Tests) | Cột I (Done) | Cột J (Remark) |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| | **Test Category** | **Module** | **Passed** | **Failed** | **Assumption Failure** | **Ignored** | **Total Tests** | **Done** | **Remark** |
| | CTS | arm64-v8a CtsAppSecurityHostTestCases | 167 | 1 | 0 | 1 | 169 | true | |

- **Điều kiện:** Chỉ xuất hiện khi có module có `Failed > 0`.
- **Nếu `Fail = 0` toàn bộ:** Bảng giữ nguyên tiêu đề, không có dòng dữ liệu nào.

---

### Sheet 3: `Nissan Fail TestCase List`
Bảng liệt kê chi tiết từng testcase bị Fail:

| Cột A (No) | Cột B (Test Category) | Cột C (Module) | Cột D (Test Case) |
| :---: | :---: | :--- | :--- |
| **No** | **Test Category** | **Module** | **Test Case** |
| 1 | CTS | arm64-v8a CtsAppSecurityHostTestCases | `android.appsecurity.cts.ListeningPortsTest#testNoRemotelyAccessibleListeningUdpPorts` |

- **Điều kiện:** Đếm tăng dần `No = 1, 2, 3...` cho toàn bộ các case fail của tất cả các bộ test.
- **Nếu `Fail = 0` toàn bộ:** Giữ nguyên bảng tiêu đề, không có dòng dữ liệu nào.
