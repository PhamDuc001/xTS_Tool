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

### Quy tắc 1: Phân loại Session dựa trên Dữ Liệu Thực Thi (`parse_session`)
Tuyệt đối **không dựa vào chuỗi câu lệnh `command_line_args`** (`-m`, `-t`, `--include-filter` hay `run retry`) vì câu lệnh có rất nhiều biến thể và không phản ánh đúng logic. Thay vào đó, phân loại trực tiếp dựa trên cấu trúc kết quả XML/HTML:

1. **Chuẩn hóa Module gốc (`base_mods`):**  
   Bóc tách bỏ hậu tố `[...]` (như `[instant]`, `[secondary_user]`). Ví dụ: `CtsNetTestCases` và `CtsNetTestCases[instant]` đều quy về `CtsNetTestCases`.

2. **Phân tầng loại Session:**
   - **`multiple`**: Session chạy tổng thể toàn suite khi `len(base_mods) > 4` HOẶC `tot_mods > 4`.
   - **`single` (Targeted Multi-Module Retry)**: Khi chạy gom $1 < 	ext{len(base\_mods)} \le 4$ trong 1 session (ví dụ `--include-filter "mod1 tc1" --include-filter "mod2 tc2"`).  
     - Tên module đại diện ghép từ các module gốc: `mod_name = "_".join(base_mods)` (ví dụ `moduleA_moduleB`).  
     - Tên thư mục sinh ra: **`{id}.{moduleA_moduleB}`**.  
     - **Điều hướng vào `single/`:** Chỉ cần session có ít nhất 1 testcase PASS (`pass_cnt > 0`), folder sẽ được đưa vào **`Report/single/{id}.{moduleA_moduleB}/`** để làm chứng cứ cho các testcase đã pass (kể cả khi còn 1 case fail chưa fix).  
     - **Tự động Ignore/Prune session fail cũ:** Khi người dùng chạy `run retry --retry` cho session này và PASS 100%, tool sẽ tự động giữ lại duy nhất session Pass mới nhất và xóa bỏ (prune) session fail cũ trước đó.
   - **`testcase`**: Khi `len(base_mods) == 1` VÀ tổng số test thực thi bằng `1` (`total_tests == 1` hoặc `pass_cnt + fail_cnt == 1`) VÀ có `test_method`.  
     - Tên folder: `{id}.{mod_name}_{tc_name}` đặt trong `Report/single/`.
   - **`single` (Single Module Retry)**: Khi `len(base_mods) == 1` VÀ chạy nhiều hơn 1 testcase (kể cả khi chạy đồng thời biến thể `[instant]`).  
     - Tên folder: `{id}.{mod_name}` (hoặc `{id}.{mod_name}_multi`).

### Quy tắc 2: Lọc lịch sử chọn lọc "2 đầu + 2 cuối" (`select_history_sessions`)
Áp dụng cho các chuỗi retry của Multiple và Single Module thông thường nhằm tối ưu dung lượng:
1. Với Single Module thông thường:
   - Nếu $\ge 5$ sessions: Giữ `[0]`, `[1]`, `[-2]`, `[-1]`, tỉa gọn các session ở giữa.
2. Với Multi-Module Targeted Retry (`{moduleA_moduleB}`):
   - Nếu đã có session Pass 100%: Chỉ giữ lại duy nhất session Pass mới nhất, loại bỏ toàn bộ các session fail cũ.
   - Nếu chưa pass 100%: Giữ session có kết quả pass mới nhất để lưu giữ bằng chứng pass.

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
