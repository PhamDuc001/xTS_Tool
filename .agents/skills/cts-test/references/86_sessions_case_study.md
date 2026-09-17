# Case Study Thực Chiến: 86 Sessions CTS Full Trên Máy Chủ 10.218.153.44

Tài liệu này phân tích chi tiết dữ liệu thực tế từ **86 sessions kiểm thử CTS** trên cụm thiết bị Android Automotive Nissan AIVI (Android 14 API 34):
- **Server:** `10.218.153.44` (User: `lge`)
- **Đường dẫn kết quả:** `/home/lge/GoogleQA/TestFolder/CTS_22324141,70b1036,5a9ba6a2/android-cts/results/`
- **Bộ 3 DUTs:** `22324141`, `70b1036`, `5a9ba6a2` (kết nối relay nguồn phần cứng qua Arduino `R1`, `R2`, `R3`)
- **Quy mô toàn diện:** **815 modules**, **2,174,000+ test cases** (trong đó `CtsDeqpTestCases` chứa hơn 2 triệu test).

---

## 1. Bức Tranh Tổng Thể 86 Sessions

Quá trình kiểm thử CTS quy mô lớn được phân tách thành 2 luồng song song có chủ đích:
1. **Luồng Single Isolation (14 modules nhạy cảm / nặng):** Chạy riêng từng module để tránh crash hệ thống và dễ dàng kiểm soát tài nguyên.
2. **Luồng Multiple Main Run (801 modules còn lại):** Sử dụng cờ `--exclude-filter` cho 26 trường hợp đặc biệt và phân bổ 3 shards song song trên 3 DUTs.

### Các Cột Mốc Quan Trọng:

| Nhóm Phiên | Phiên Tiêu Biểu | Mục Tiêu & Kịch Bản | Kết Quả Đạt Được | Bài Học Kỹ Thuật |
| :--- | :--- | :--- | :--- | :--- |
| **Khởi động Single** | Session 0 – 6 | Chạy thử các module đơn lẻ (`CtsAccessibilityServiceTestCases`, `CtsAutoFillServiceTestCases`, `CtsWindowManagerDeviceTestCases`) | Đạt baseline từng module, phát hiện các ca nhạy cảm giao diện. | Chạy single giúp phát hiện sớm các lỗi về WindowManager trước khi chạy full suite. |
| **Deqp Khổng Lồ** | Session 6 (`12.47.48`) | Chạy `run cts -m CtsDeqpTestCases` (2 triệu test đồ họa Vulkan/OpenGL) | **Pass: 2,003,148 / Fail: 1** | Thời gian chạy ~11 tiếng liên tục. Module cực nặng, cần tản nhiệt tốt. |
| **Main Suite Baseline** | Session 7 (`17.49.40`) | Chạy 801 modules chính với 26 exclude filters, 3 shards (`22324141`, `70b1036`, `5a9ba6a2`) | **813/815 modules done<br>Pass: 171,340<br>Fail: 93** | Đạt tỷ lệ Pass 99.95% ngay từ lần chạy đầu tiên. Tránh được hoàn toàn nguy cơ OOM crash. |
| **Auto-Retry Vòng 1** | Session 8 (`12.32.11`) | `run retry --retry <sess7> --retry-type FAILED --shard-count 3` | **Pass: 171,401<br>Fail: 24** | Số lỗi giảm mạnh từ 93 xuống 24 (69 ca pass nhờ retry). |
| **Auto-Retry Vòng 2** | Session 9 (`12.52.54`) | `run retry --retry <sess8> --retry-type FAILED --shard-count 3` | **Pass: 171,408<br>Fail: 17** | Tiếp tục giảm thêm 7 ca, chỉ còn lại 17 ca lỗi cứng. |
| **Xử Lý 17 Lỗi Cứng** | Session 10 – 85 | Xử lý từng ca lỗi cứng (Throttling nhiệt độ, Statsd buffer, Keyguard, Wi-Fi) | Từng module lần lượt đạt 100% Pass hoàn hảo. | Xem chi tiết phân tích 17 ca lỗi bên dưới. |

---

## 2. Phân Tích 17 Ca Lỗi Cứng (Hard Failures) & Cách Vượt Qua

Tại Session 9 (`2026.09.13_12.52.54.379_9188`), danh sách lỗi co cụm lại thành 6 nhóm cụ thể:

### Nhóm 1: Throttling Nhiệt Độ Chip Qualcomm Codec (`CtsMediaDecoderTestCases`, `CtsVideoTestCases`)
- **Test case:**
  - `VideoDecoderPerfTest#testPerf[12_c2.qti.hevc.decoder_sd]`
  - `VideoDecoderPerfTest#testPerf[19_c2.qti.vp8.decoder_qvga]`
  - `VideoDecoderPerfTest#testPerf[21_c2.qti.vp8.decoder_vga]`
  - `VideoEncoderDecoderTest#testPerf[video/x-vnd.on2.vp8_c2.qti.vp8.encoder_320x180_0]`
- **Mã lỗi:** `Expected achievable frame rates for c2.qti.vp8.encoder: [226.0, 246.0]. Measured: 218.4`.
- **Nguyên nhân:** Sau hơn 20 giờ kiểm thử liên tục, chip SoC Qualcomm trên Head Unit bị tích nhiệt, mạch bảo vệ kích hoạt cơ chế hạ xung nhịp (Thermal Throttling), làm giảm 3-5% tốc độ mã hóa khung hình.
- **Giải pháp thực nghiệm (Đã thành công tại Session 68 & 69):**
  1. Ngắt nguồn DUT thông qua relay Arduino: `python3 ControlPCB.py R1off && sleep 15 && python3 ControlPCB.py R1`.
  2. Để thiết bị nghỉ 10 phút cho vỏ máy và tản nhiệt hạ về nhiệt độ phòng lab (< 28°C).
  3. Chạy đơn lẻ đúng test case bằng cờ `-t`:
     ```bash
     run cts -m CtsVideoTestCases -t android.video.cts.VideoEncoderDecoderTest#testPerf[video/x-vnd.on2.vp8_c2.qti.vp8.encoder_320x180_0] -s 22324141
     ```
  4. **Kết quả:** Đo đạt 235 fps -> **PASS 100%** (Session `2026.09.14_16.47.16`).

---

### Nhóm 2: Lỗi Phân Tích Báo Cáo Statsd (`CtsAppCompatHostTestCases[instant]`)
- **Test case:**
  - `CompatChangesOverrideOnReleaseBuildTest#testPutPackageOverridesSecurityExceptionNonOverridableChangeId`
  - `CompatChangesSystemApiTest#testIsChangeEnabled`
- **Mã lỗi:** `java.lang.IllegalStateException: Failed to fetch and parse the statsd output report`.
- **Nguyên nhân:** Dịch vụ statsd bị tràn hàng đợi sự kiện (event queue) do chạy hàng trăm module trước đó.
- **Giải pháp:**
  ```bash
  adb -s <serial> shell cmd statsd data-wipe
  run retry --retry <sess_id> -s <serial> --include-filter "CtsAppCompatHostTestCases[instant]"
  ```
  **Kết quả:** Dữ liệu sạch, host đọc được atom report ngay lập tức.

---

### Nhóm 3: Kiểm Tra Cổng Nghe UDP (`CtsAppSecurityHostTestCases`)
- **Test case:** `ListeningPortsTest#testNoRemotelyAccessibleListeningUdpPorts`
- **Nguyên nhân:** Thiết bị Automotive mở cổng lắng nghe UDP không bảo mật cho các daemon debug mạng hoặc adb over Wi-Fi.
- **Giải pháp:**
  - Tắt adb qua mạng Wi-Fi: chỉ kiểm thử qua cáp USB Type-C vật lý.
  - Tắt các dịch vụ daemon logging mở port `0.0.0.0`.

---

### Nhóm 4: Màn Hình Khóa & Pop-up Giao Diện (`CtsPermission3TestCases`, `CtsWindowManagerDeviceTestCases`)
- **Test case:**
  - `PermissionDecisionsTest#testClickOnDecisionAndChangeAccessUpdatesDecision`
  - `PermissionTest23#testRevokeAffectsWholeGroup`
- **Mã lỗi:** `UiDumpWrapperException: View not found after waiting for 20000ms`.
- **Nguyên nhân:** Màn hình Automotive bị tắt hoặc có thông báo hệ thống (ANR / Dialog) che mất nút bấm của UiAutomator.
- **Giải pháp (Đạt 100% Pass tại Session 84 - 1024/1024 Pass):**
  ```bash
  adb -s <serial> shell input keyevent 224
  adb -s <serial> shell wm dismiss-keyguard
  adb -s <serial> shell input keyevent 3
  ```

---

### Nhóm 5: Mất Kết Nối Wi-Fi Subsystem (`CtsWifiTestCases`)
- **Test case:** `WifiManagerTest#testConnectWithNetworkId: expected:<CONNECTED> but was:<DISCONNECTED>`.
- **Giải pháp:** Khởi động lại subsystem Wi-Fi và nạp lại cấu hình Access Point qua script `connectWF.sh`.

---

## 3. Các Kết Quả 100% Pass Đã Xác Thực Trên Server

1. **`CtsDeqpTestCases` (2,003,149 Test Cases):**  
   - Phiên: `2026.09.14_17.47.06.825_4390`  
   - Lệnh: `cts -m CtsDeqpTestCases --shard-count 3 -s 22324141 -s 70b1036 -s 5a9ba6a2`  
   - Kết quả: **2,003,149 PASS, 0 FAIL (100% PASS)**.
2. **`CtsWindowManagerDeviceTestCases` (1,024 Test Cases):**  
   - Phiên: `2026.09.15_15.40.50.866_5943`  
   - Lệnh: `cts -m CtsWindowManagerDeviceTestCases --shard-count 3`  
   - Kết quả: **1,024 PASS, 0 FAIL (100% PASS)**.
3. **`CtsCarTestCases` (430 Test Cases):**  
   - Phiên: `2026.09.16_12.03.50.347_3038`  
   - Lệnh: `cts -m CtsCarTestCases`  
   - Kết quả: **430 PASS, 0 FAIL (100% PASS)**.
