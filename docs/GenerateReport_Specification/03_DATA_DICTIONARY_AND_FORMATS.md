# Từ Điển Dữ Liệu & Định Dạng Bảng Tính (Data Dictionary & Excel Formats)

---

## 1. Từ điển dữ liệu đầu vào (Input Metadata)

| Tên trường UI | Nhãn hiển thị | Ví dụ thực tế | Kiểu dữ liệu | Mô tả & Tác động |
| :--- | :--- | :--- | :---: | :--- |
| `txt_project_model` | Project (Model) Full | `Nissan_AIVI_Full_12.3_PZ1D_26MY` | String | Tên thư mục phát hành trên GOOGLEQA, điền ô `C3` file `03.` |
| `txt_model_code` | Model Short Code | `PZ1D` | String | Dùng trong tên file `03.` và tên file Summary |
| `txt_hw_version` | HW (PCB) version | `C` | String | Điền ô `C4` file `03.`, dòng `HW` của bảng Summary |
| `txt_sw_version` | SW version Full | `YAK.31.03.30` | String | Điền ô `C5` file `03.`, dòng `SW` của bảng Summary |
| `txt_micom_version`| MICOM version | `v3.27.37` | String | Điền ô `C6` file `03.`, dòng `MICOM` của bảng Summary |
| `date_oem_delivery`| OEM Delivery | `09/11/2026` | String | Điền ô `G2` file `03.` |
| `date_test_start` | Test Start | `09/07/2026` | String | Điền ô `G3` file `03.` |
| `date_test_end` | Test End | `09/10/2026` | String | Điền ô `G4` file `03.` |
| `txt_tester` | Tester ID | `duc4.pham` | String | Điền ô `G6` file `03.` |
| `txt_prev_summary` | Previous Summary Path | `/home/googleqa/.../Summary.xlsx` | Path | Đường dẫn template lấy mẫu |

---

## 2. Quy tắc ánh xạ tên file Suite từ APTRA sang `03.`

| Tên file từ APTRA | Tên file chuẩn hóa `03.` | Nguồn số liệu |
| :--- | :--- | :--- |
| `ATSResult.xlsx` | `03.LGE_{Model}_{ModelCode}_ATS_Result_Final_{SW}.xlsx` | APTRA |
| `AtsInteractiveResults.xlsx` | `03.LGE_{Model}_{ModelCode}_AtsInteractive_Result_Final_{SW}.xlsx` | APTRA |
| `AtsMultideviceResults.xlsx` | `03.LGE_{Model}_{ModelCode}_AtsMultidevice_Result_Final_{SW}.xlsx` | APTRA |
| `BFGResult.xlsx` | `03.LGE_{Model}_{ModelCode}_BFG_Result_Final_{SW}.xlsx` | APTRA |
| `CTSResult.xlsx` | `03.LGE_{Model}_{ModelCode}_CTS_Result_Final_{SW}.xlsx` | APTRA |
| `CTSonGSIResult.xlsx` | `03.LGE_{Model}_{ModelCode}_CTSonGSI_Result_Final_{SW}.xlsx` | APTRA |
| `STSResult.xlsx` | `03.LGE_{Model}_{ModelCode}_STS_Result_Final_{SW}.xlsx` | APTRA |
| `VTSResult.xlsx` | `03.LGE_{Model}_{ModelCode}_VTS_Result_Final_{SW}.xlsx` | APTRA |
| *(Không qua APTRA)* | `01.CTS_Verifier/` | Đọc trực tiếp thẻ `<Summary>` trong `test_result.xml` |

---

## 3. Tọa độ ô & Cấu trúc File `03.*.xlsx`

### Sheet `Test Summary` (Chuẩn 14 hàng sạch):
- Ô `C3`: `Project (Model)` (Merge `C3:E3`)
- Ô `C4`: `HW (PCB) version` (Merge `C4:E4`)
- Ô `C5`: `SW version` (Merge `C5:E5`)
- Ô `C6`: `MICOM version` (Merge `C6:E6`)
- Ô `G2`: `OEM Delivery` (Merge `G2:I2`, format `@`)
- Ô `G3`: `Test Start` (Merge `G3:I3`, format `@`)
- Ô `G4`: `Test End` (Merge `G4:I4`, format `@`)
- Ô `G6`: `Tester` (Merge `G6:I6`)
- Ô `H12`: `=E12/C12` (Pass Rate)
- **Quy tắc làm sạch:** Unmerge `B17:F17` và xóa toàn bộ từ hàng 15 đến 40.

### Sheet `Test Result_Detail`:
- Ô `D3:J3` chứa 7 giá trị tổng hợp của bộ test:
  - `D3`: Pass count
  - `E3`: Fail count
  - `F3`: Assumption Failure count
  - `G3`: Ignored count
  - `H3`: Total Tests count
  - `I3`: Module Done count
  - `J3`: Total Module count
- Từ dòng 5 trở đi: Cột E chứa số lượng `Failed` của từng module. Lọc **`Failed > 0`** để trích xuất sang file Summary.

---

## 4. Bảng Demo Dữ Liệu Thực Tế File Summary (`YAK.31.03.30`)

### Sheet `Summary`:
| Dòng | Test Category | Pass | Fail | Assumption Failure | Ignored | Total Tests | Module Done | Total Module |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **HW (PCB) version**: C | | | | | | | |
| 2 | **SW version**: YAK.31.03.30 | | | | | | | |
| 3 | **MICOM version**: v3.27.37 | | | | | | | |
| 4 | **Test Category** | **Pass** | **Fail** | **Assumption Failure** | **Ignored** | **Total Tests** | **Module Done** | **Total Module** |
| 5 | ATS (2026_r2) | 1,312 | 0 | 358 | 14 | 1,684 | 96 | 96 |
| 6 | ATS-In-Car (2026_r2) | | | | | | | |
| 7 | ATS_Interactive (2026_r2) | 30 | 0 | 5 | 0 | 35 | 7 | 7 |
| 8 | ATS-Multidevice (2026_r2) | 0 | 0 | 1 | 0 | 1 | 1 | 1 |
| 9 | BFG (2026_r2) | 15 | 0 | 0 | 0 | 15 | 7 | 7 |
| 10 | CTS (14_r12) | 2,210,384 | 1 | 10,403 | 768 | 2,221,556 | 832 | 832 |
| 11 | CTSonGSI (14_r12) | 178,116 | 0 | 7,967 | 580 | 186,663 | 413 | 413 |
| 12 | STS (sts-r54) | 1,045 | 0 | 469 | 1 | 1,515 | 25 | 25 |
| 13 | VTS | 80,050 | 0 | 53 | 38,154 | 118,257 | 370 | 370 |
| 14 | CTS-Verifier (14_r12) | 50 | 0 | 0 | 0 | 50 | 1 | 1 |
| 15 | **Summary** | `=SUM(D5:D14)` | `=SUM(E5:E14)` | `=SUM(F5:F14)` | `=SUM(G5:G14)` | `=SUM(H5:H14)` | `=SUM(I5:I14)` | `=SUM(J5:J14)` |

### Sheet `Nissan Fail Module List`:
| No | Test Category | Module | Passed | Failed | Assumption Failure | Ignored | Total Tests | Done | Remark |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| | CTS | arm64-v8a CtsAppSecurityHostTestCases | 167 | 1 | 0 | 1 | 169 | true | |

### Sheet `Nissan Fail TestCase List`:
| No | Test Category | Module | Test Case |
| :---: | :---: | :--- | :--- |
| 1 | CTS | arm64-v8a CtsAppSecurityHostTestCases | `android.appsecurity.cts.ListeningPortsTest#testNoRemotelyAccessibleListeningUdpPorts` |
