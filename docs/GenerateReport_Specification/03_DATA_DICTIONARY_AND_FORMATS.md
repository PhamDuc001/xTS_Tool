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

### 2. Quy tắc ánh xạ tên file Suite từ APTRA sang `03.` & Sheet Summary

| Tên file từ APTRA | Tên file chuẩn hóa `03.` | Nguồn version suite | Dòng tương ứng trong sheet `Summary` |
| :--- | :--- | :--- | :--- |
| `ATSResult(s).xlsx` | `03.LGE_{Model}_{ModelCode}_ATS_Result_Final_{SW}.xlsx` | Ô C7: `ATS 2026_r2` | `ATS (2026_r2)` |
| `AtsIncarResult(s).xlsx` | `03.LGE_{Model}_{ModelCode}_AtsIncar_Result_{SW}.xlsx` | Ô C7: `ATS 2026_r2` | `ATS-In-Car (2026_r2)` |
| `AtsInteractiveResults.xlsx` | `03.LGE_{Model}_{ModelCode}_AtsInteractive_Result_Final_{SW}.xlsx` | Ô C7: `ATS 2026_r2` | `ATS_Interactive (2026_r2)` |
| `AtsMultideviceResults.xlsx` | `03.LGE_{Model}_{ModelCode}_AtsMultidevice_Result_Final_{SW}.xlsx` | Ô C7: `ATS 2026_r2` | `ATS-Multidevice (2026_r2)` |
| `BFGResult(s).xlsx` | `03.LGE_{Model}_{ModelCode}_BFG_Result_Final_{SW}.xlsx` | Ô C7: `ATS 2026_r2` | `BFG (2026_r2)` |
| `CTSResult(s).xlsx` | `03.LGE_{Model}_{ModelCode}_CTS_Result_Final_{SW}.xlsx` | Ô C7: `CTS 14_r13` | `CTS (14_r13)` |
| `CTSonGSIResult(s).xlsx` | `03.LGE_{Model}_{ModelCode}_CTSonGSI_Result_Final_{SW}.xlsx` | Ô C7: `CTS 14_r13` | `CTSonGSI (14_r13)` |
| `STSResult(s).xlsx` | `03.LGE_{Model}_{ModelCode}_STS_Result_Final_{SW}.xlsx` | Ô C7: `STS 14_sts-r55`| `STS (14_sts-r55)` |
| `VTSResult(s).xlsx` | `03.LGE_{Model}_{ModelCode}_VTS_Result_Final_{SW}.xlsx` | Ô C7: `VTS 14_r13` | `VTS (14_r13)` |
| *(Không qua APTRA)* | *(Trích xuất từ XML `CTS_Verifier`)* | XML root: `suite_version="14_r13"` | `CTS-Verifier (14_r13)` |

---

## 3. Tọa độ ô & Cấu trúc File `03.*.xlsx`

### Sheet `Test Summary` (Chuẩn 14 hàng sạch):
- Ô `C3`: `Project (Model)` (Merge `C3:E3`)
- Ô `C4`: `HW (PCB) version` (Merge `C4:E4`)
- Ô `C5`: `SW version` (Merge `C5:E5`) - **Bắt buộc điền SW Version mới nhất (vd: `YAK.31.04.10`)**
- Ô `C6`: `MICOM version` (Merge `C6:E6`)
- **Ô `C7`**: `Test Suite` (Chứa chuỗi tên & phiên bản suite của bài test, vd `CTS 14_r13`, `STS 14_sts-r55`, `ATS 2026_r2` - Dùng làm nguồn bóc tách version cho cột Test Category)
- Ô `G2`: `OEM Delivery` (Merge `G2:I2`, format `@`)
- Ô `G3`: `Test Start` (Merge `G3:I3`, format `@`)
- Ô `G4`: `Test End` (Merge `G4:I4`, format `@`)
- Ô `G6`: `Tester` (Merge `G6:I6`)
- Ô `H12`: `=E12/C12` (Pass Rate - Giữ nguyên công thức)
- **Quy tắc làm sạch:** Quét unmerge an toàn dải merge $\ge 15$ và xóa toàn bộ từ hàng 15 đến 40 (`ws.delete_rows(15, ws.max_row - 14)`).

### Sheet `Test Result_Detail`:
- Ô `D3:J3` chứa 7 giá trị tổng hợp của bộ test:
  - `D3`: Pass count
  - `E3`: Fail count
  - `F3`: Assumption Failure count
  - `G3`: Ignored count
  - `H3`: Total Tests count
  - `I3`: Module Done count
  - `J3`: Total Module count
- **Cơ chế Fallback (Tính toán khi Row 3 thiếu Cached Value):**
  - Nếu `D3:J3` là formula rỗng hoặc `None`, duyệt từ hàng 5 đến `max_row` để tính tổng cộng dồn cột D đến H, và đếm số module done (Cột I) / tổng module.
- Từ dòng 5 trở đi: Cột E chứa số lượng `Failed` của từng module. Lọc **`Failed > 0`** để trích xuất sang file Summary.

---

## 4. Bảng Demo Dữ Liệu Thực Tế File Summary (`YAK.31.04.10`)

### Sheet `Summary` (Khối mới tại hàng 19–33, duplicate từ khối cũ hàng 2–16):
| Dòng | Cột B (Thông tin xe) | Cột C (Test Category / Metadata) | Pass | Fail | Assumption Failure | Ignored | Total Tests | Module Done | Total Module |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 19 | HW (PCB) version | **C** | | | | | | | |
| 20 | SW version | **YAK.31.04.10** | | | | | | | |
| 21 | MICOM version | **v3.27.37** | | | | | | | |
| 22 | *(Header)* | **Test Category** | **Pass** | **Fail** | **Assumption Failure** | **Ignored** | **Total Tests** | **Module Done** | **Total Module** |
| 23 | **Nissan PZ1D** *(Merge B23:B33)* | **ATS (2026_r2)** | 1,689 | 0 | 444 | 14 | 2,147 | 108 | 108 |
| 24 | | **ATS-In-Car (2026_r2)** | 228 | 0 | 7 | 0 | 235 | 9 | 9 |
| 25 | | **ATS_Interactive (2026_r2)** | 30 | 0 | 5 | 0 | 35 | 7 | 7 |
| 26 | | **ATS-Multidevice (2026_r2)** | 0 | 0 | 1 | 0 | 1 | 1 | 1 |
| 27 | | **BFG (2026_r2)** | 15 | 0 | 0 | 0 | 15 | 7 | 7 |
| 28 | | **CTS (14_r13)** | 2,212,487 | 0 | 10,402 | 768 | 2,223,657 | 832 | 832 |
| 29 | | **CTSonGSI (14_r13)** | 178,495 | 0 | 7,967 | 580 | 187,042 | 413 | 413 |
| 30 | | **STS (14_sts-r55)** | 1,030 | 0 | 484 | 1 | 1,515 | 25 | 25 |
| 31 | | **VTS (14_r13)** | 80,050 | 0 | 53 | 38,154 | 118,257 | 370 | 370 |
| 32 | | **CTS-Verifier (14_r13)** | 50 | 0 | 0 | 0 | 50 | 1 | 1 |
| 33 | | **Summary** | `=SUM(D23:D32)` | `=SUM(E23:E32)` | `=SUM(F23:F32)` | `=SUM(G23:G32)` | `=SUM(H23:H32)` | `=SUM(I23:I32)` | `=SUM(J23:J32)` |

### Sheet `Nissan Fail Module List`:
*(Xóa trắng dữ liệu cũ từ hàng 3 trở đi, chỉ ghi nhận các dòng có `Failed > 0`)*
| No | Test Category | Module | Passed | Failed | Assumption Failure | Ignored | Total Tests | Done | Remark |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| | *(Trống nếu Pass 100%)* | | | | | | | | |

### Sheet `Nissan Fail TestCase List`:
*(Xóa trắng dữ liệu cũ từ hàng 3 trở đi, đánh số No từ 1 nếu có testcase fail)*
| No | Test Category | Module | Test Case |
| :---: | :---: | :--- | :--- |
| | *(Trống nếu Pass 100%)* | | |

---
*Xem thêm cẩm nang lưu ý thực tế: [05_CRITICAL_NOTES_AND_EDGE_CASES.md](./05_CRITICAL_NOTES_AND_EDGE_CASES.md).*
