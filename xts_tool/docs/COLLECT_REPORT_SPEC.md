# ĐẶC TẢ KIẾN TRÚC & QUY CHUẨN THU THẬP BÁO CÁO (COLLECT REPORT MODE)
> **Tài liệu tham chiếu chuẩn** cho công cụ `xTS Tool` (`report_collector.py`)  
> **Áp dụng từ:** PR #4 (Commit `19b9589` / `33f0b90`)

---

## 1. Cấu Trúc Cây Thư Mục Báo Cáo Chuẩn (`Report/`)

Cấu trúc đích được sinh ra tại `<test_root>/Report/` tuân thủ nghiêm ngặt mô hình phân tách **Root (Multiple & Chưa Pass)** và **`single/` (Đã Pass)**:

```text
<test_root>/Report/
├── results/                                     # Dữ liệu session Multiple (đã lọc 2 đầu + 2 cuối)
│   ├── 2026.10.20_10.00.00/
│   └── 2026.10.20_10.00.00.zip
├── logs/                                        # Log tương ứng của session Multiple
│   └── 2026.10.20_10.00.00/
│
├── single/                                      # [KHU VỰC ĐÃ PASS] - Chỉ chứa module & testcase đã PASS
│   ├── 01.CtsNetTestCase/                       # Module đơn lẻ retry đã PASS
│   │   ├── results/
│   │   └── logs/
│   ├── 02.CtsNetTestCase_testRequestNetwork/    # Testcase lẻ retry đã PASS ({mod_name}_{tc_name})
│   │   ├── results/
│   │   └── logs/
│   └── 03.CtsNetTestCase_testRequest/           # Testcase lẻ khác đã PASS (tách folder độc lập)
│       ├── results/
│       └── logs/
│
├── 04.CtsCarTestCases/                          # [KHU VỰC CHƯA PASS] - Nằm ở ngoài Root Report/
│   ├── results/
│   └── logs/
└── 05.CtsDeqpTestCases_multi/                   # Module từng fail trong Multiple và retry vẫn chưa pass
    ├── results/
    └── logs/
```

---

## 2. 5 Quy Tắc Thu Thập & Tổ Chức Dữ Liệu

### Quy tắc 1: Phân loại Session (`parse_session`)
Mỗi session trong thư mục nguồn `results/` được bóc tách từ `test_result.xml` và `test_result_failures_suite.html`, phân loại thành 3 nhóm:
- **`multiple`**: Session chạy tổng thể nhiều module (`len(base_mods) > 1`, `tot_mods > 2`, hoặc command line chứa từ khóa `multiple`).
- **`single`**: Session chạy retry 1 module đơn lẻ (`-m <module>` hoặc kết quả chỉ gồm 1 module duy nhất).
- **`testcase`**: Session chạy retry 1 testcase cụ thể (`-t <test>`, `#<method>`, hoặc chỉ chạy duy nhất 1 testcase).

### Quy tắc 2: Lọc lịch sử chọn lọc "2 đầu + 2 cuối" (`select_history_sessions`)
Áp dụng cho các chuỗi retry của Multiple và Single Module nhằm tối ưu dung lượng file zip nộp chứng chỉ:
1. Xác định session **Pass cuối cùng** và cắt bỏ toàn bộ các session fail thừa phát sinh sau đó.
2. Nếu số lượng session `< 5`: Giữ lại toàn bộ.
3. Nếu số lượng session `≥ 5`: Chỉ giữ lại đúng **4 session cốt lõi**:
   - `[0]`: Session đầu tiên (lần chạy đầu / gốc ghi nhận fail).
   - `[1]`: Session thứ hai (lần retry đầu).
   - `[-2]`: Session áp chót.
   - `[-1]`: Session cuối cùng (kết quả pass).
4. Các session thừa ở giữa sẽ tự động được tỉa gọn (**PRUNE**) khỏi cả `results/` lẫn `logs/`.

### Quy tắc 3: Quy ước đặt tên thư mục (`{id}.{Name}`)
- Tiền tố số thứ tự tăng dần 2 chữ số: `01.`, `02.`, `03.`... (tính tiếp theo ID lớn nhất đang tồn tại qua `get_max_existing_id`).
- Module fail trong Multiple sau đó retry: Thêm hậu tố `_multi` (ví dụ: `{id}.{module_name}_multi`).
- Testcase chạy lẻ: Ghép tên dạng **`{id}.{mod_name}_{tc_name}`** (được sanitize ký tự đặc biệt).
- **So khớp thư mục (Exact Match):**
  - Chỉ reuse folder nếu tên khớp tuyệt đối `clean == want` (sau khi bóc tách tiền tố số `^\d+\.\s*`).
  - Tuyệt đối không dùng substring match để tránh lồng nhầm testcase ngắn vào testcase dài.

### Quy tắc 4: Quan hệ giữa Multiple và Single/Testcase
- **Bỏ qua Module đơn lẻ nếu Multiple đã Pass:**
  Nếu module đã Pass trong session Multiple mới nhất (`passed_in_latest_multi`), tool sẽ **bỏ qua không tạo folder single riêng** ở BƯỚC 3 để tránh sinh dữ liệu dư thừa.
- **Dọn dẹp thư mục thừa an toàn (BƯỚC 5 Cleanup):**
  Khi module đã pass trong Multiple, tool dọn dẹp các thư mục module single thừa, nhưng **so khớp chính xác tên module** (`base_name.lower() == pm.lower()`), **tuyệt đối không xóa nhầm** các thư mục retry cấp testcase (`{mod_name}_{tc_name}`).

### Quy tắc 5: Phân luồng vị trí Pass vs Chưa Pass (BƯỚC 5 Chuẩn hóa)
- Mọi module / testcase nào **ĐÃ PASS** ➔ Chuyển toàn bộ vào nằm trong thư mục **`Report/single/`**.
- Mọi module nào **CHƯA PASS** (vẫn còn test fail) ➔ Đưa ra ngoài **Root `Report/`** để người phụ trách kiểm thử mở ra là nhìn thấy ngay các module còn nợ lỗi cần xử lý tiếp.
- Dữ liệu Multiple sau khi gộp 2 đầu + 2 cuối luôn nằm trực tiếp ở **`Report/results/`** và **`Report/logs/`**.

---

## 3. Phân Tích 2 Lỗi Đã Được Xử Lý Triệt Để Tại PR #4

### Case 1 — Testcase bị lồng nhầm folder
- **Triệu chứng cũ:** Cả 2 testcase `testRequestNetwork` và `testRequest` đều bị nhét chung vào folder `01.CtsNetTestCase_testRequestNetwork`.
- **Nguyên nhân:** Hàm `match_testcase_folder()` dùng heuristic `tc_clean in f_lower`. Do chuỗi `"testrequest"` là substring nằm trọn vẹn trong `"01.ctsnettestcase_testrequestnetwork"`, tool nhận nhầm folder đã có là của `testRequest`.
- **Giải pháp PR #4:** Bỏ heuristic substring, chuẩn hóa và so khớp tuyệt đối:
  ```python
  want = (mod_name + "_" + sanitize_name(tc_name)).lower()
  clean = re.sub(r"^\d+\.\s*", "", f).strip().lower()
  if clean == want:
      return f
  ```

### Case 2 — Folder retry bị xóa mất ở BƯỚC 5
- **Triệu chứng cũ:** `Report/single/` bị rỗng hoàn toàn, mất toàn bộ folder retry của testcase lẻ.
- **Nguyên nhân:** BƯỚC 5 dùng điều kiện `pm.lower() in base_name.lower() and len(pm) > 5`. Tên module `CtsNetTestCase` là substring của tên folder testcase `CtsNetTestCase_testRequestNetwork`, khiến lệnh `shutil.rmtree()` xóa nhầm toàn bộ kết quả retry testcase.
- **Giải pháp PR #4:** Đổi sang so khớp tuyệt đối:
  ```python
  if base_name.lower() == pm.lower():
      shutil.rmtree(p, ignore_errors=True)
      break
  ```

---

## 4. Lưu Ý Quan Trọng Về Điều Kiện Tạo `Report/results` & `Report/logs`
- Thư mục `Report/single/` luôn được tạo sẵn ở bước khởi tạo đầu hàm (`os.makedirs(single_dir, exist_ok=True)`).
- Trong khi đó, `Report/results/` và `Report/logs/` **chỉ được tạo khi thư mục nguồn có ít nhất 1 session Multiple** (`if multi_sessions:`).
- Nếu một lần test chỉ toàn các session single retry (không có session multiple gốc), root `Report/` sẽ không sinh `results/` và `logs/` (đây là hành vi chuẩn theo thiết kế).
