---
name: cts-on-gsi
description: >-
  Cẩm nang chẩn đoán lỗi và cố vấn phương án hành động (Action Plan & Command Advisor) cho bài kiểm thử CTS on GSI trên Android Automotive (Nissan AIVI).
  Đọc trực tiếp test_result_failures_suite.html của mỗi session, phân tích nguyên nhân lỗi (đặc biệt lỗi Car HVAC / VHAL do thiếu tín hiệu CAN bus, mất Wi-Fi GSI, Limited Connection do lệch giờ hệ thống, Tradefed kẹt thiết bị Unavailable sau rớt USB, lỗi Ghidra 403),
  và đưa ra phương án hành động chuẩn xác: can thiệp thiết bị (đồng bộ giờ qua cmd alarm, captive_portal_mode, kích hoạt CANat, reboot, kết nối wifi IPv4/IPv6, keyguard) và câu lệnh Tradefed chính xác từng ký tự (include-filter, exclude-filter, not_executed, shard_count, -m, -t).
---

# CTS on GSI - Cẩm Nang Chẩn Đoán Lỗi & Chỉ Dẫn Hành Động Vận Hành (Advisor Playbook)

Tài liệu này là cẩm nang chuyên sâu dành cho **AI Agent và Kỹ sư kiểm thử** khi vận hành, phân tích lỗi và điều phối các bài test **CTS on GSI (Compatibility Test Suite on Generic System Image)** trên nền tảng **Android Automotive OS (Nissan AIVI / Head Unit)**.

---

## ⛔ NGUYÊN TẮC BẢO MẬT & AN TOÀN TỐI CAO (CRITICAL SAFETY RULES)

> [!CAUTION]
> ### 1. TUYỆT ĐỐI KHÔNG FACTORY RESET TRÊN BẢN GSI!
> - Trên bản build Android Automotive GSI, **Factory Reset (`settings / recovery / wipe`) sẽ xóa sạch cấu hình và đưa máy về màn hình thiết lập ban đầu (Setup Wizard / OOBE)**.
> - Khi ở màn hình OOBE, **USB Debugging (`adbd`) mặc định bị VÔ HIỆU HÓA (DISABLED)**.
> - Thiết bị Head Unit sẽ **MẤT HOÀN TOÀN KẾT NỐI ADB** qua cổng USB, dẫn đến brick tạm thời và bắt buộc phải can thiệp phần cứng hoặc nạp lại firmware từ đầu qua Fastboot/EDL.
> - Mọi lỗi mạng Wi-Fi ("Limited Connection"), tràn bộ nhớ, hay kẹt cache đều có thể xử lý tại chỗ qua ADB Shell mà không bao giờ cần Factory Reset.

> [!IMPORTANT]
> ### 2. NGUYÊN TẮC LẬP PLAN & XIN PHÉP (PLAN FIRST)
> - Luôn khảo sát ở chế độ **Read-Only** trước.
> - Trình bày Kế hoạch chi tiết (Mục tiêu, files tác động, câu lệnh thực thi).
> - Chỉ thực thi khi người dùng đã duyệt rõ ràng.

---

## 📑 MỤC LỤC
1. [Môi Trường Máy Chủ & Thiết Bị Thực Tế](#1-môi-trường-máy-chủ--thiết-bị-thực-tế)
2. [Quy Trình Phân Tích Báo Cáo Session (Failure HTML First)](#2-quy-trình-phân-tích-báo-cáo-session-failure-html-first)
3. [Ma Trận Phương Án Hành Động Cho CTS on GSI](#3-ma-trận-phương-án-hành-động-cho-cts-on-gsi)
   - [Ca 1: Lỗi VHAL HVAC Seat/Fan Temperature (Thiếu Tín Hiệu CAN)](#ca-1-lỗi-vhal-hvac-seatfan-temperature-thiếu-tín-hiệu-can)
   - [Ca 2: Lỗi Mạng Wi-Fi: "Limited Connection" / SSL Handshake Failed / Mất IP](#ca-2-lỗi-mạng-wi-fi-limited-connection--ssl-handshake-failed--mất-ip)
   - [Ca 3: Lỗi Tradefed Kẹt Thiết Bị: `Allocation: Unavailable` Sau Rớt USB](#ca-3-lỗi-tradefed-kẹt-thiết-bị-allocation-unavailable-sau-rớt-usb)
   - [Ca 4: Lỗi GhidraPreparer TargetSetupError (GitHub API 403 Forbidden)](#ca-4-lỗi-ghidrapreparer-targetsetuperror-github-api-403-forbidden)
   - [Ca 5: Lỗi Màn Hình Khóa & Giao Diện Cửa Sổ (WindowManager)](#ca-5-lỗi-màn-hình-khóa--giao-diện-cửa-sổ-windowmanager)
   - [Ca 6: Lỗi Tràn Hàng Đợi Statsd Telemetry](#ca-6-lỗi-tràn-hàng-đợi-statsd-telemetry)
   - [Ca 7: Gián Đoạn Tiến Trình Test (notExecuted > 0)](#ca-7-gián-đoạn-tiến-trình-test-notexecuted--0)
4. [Chiến Lược 4 Tầng Điều Phối Lệnh Tradefed](#4-chiến-lược-4-tầng-điều-phối-lệnh-tradefed)
5. [Cẩm Nang Lệnh Tradefed Console](#5-cẩm-nang-lệnh-tradefed-console)

---

## 1. Môi Trường Máy Chủ & Thiết Bị Thực Tế

| Máy Chủ (IP) | Tài Khoản | Mục Đích Chính | Thiết Bị Thường Gặp |
| :--- | :--- | :--- | :--- |
| **`10.218.153.41`** | `lge` / `lge@1234` | Chạy STS & CTS Tradefed, AutoRetry tool | DUT `59b2659a` |
| **`10.218.153.42`** | `lge` / `lge@1234` | Chạy CTS on GSI | DUT `39e8f0a1`, `b09d3499` |
| **`10.218.153.44`** | `lge` / `lge@1234` | AutoFlashing Tool V1.9, Pre-Setup | Multi-DUT flashing |

- **Đường dẫn ADB chuẩn:** `/home/lge/Environment/AndroidSDK/platform-tools/adb`
- **Wi-Fi kiểm thử chuẩn:**
  - SSID: `"GG"` (Tốc độ cao 65 - 72 Mbps, đã validate đầy đủ).
  - SSID: `"GG_Cert_Test"` (Dự phòng, kiểm tra cert).

---

## 2. Quy Trình Phân Tích Báo Cáo Session (Failure HTML First)

> [!IMPORTANT]
> **Nguyên tắc vàng:** Khi phân tích session CTS on GSI, **luôn đọc file `test_result_failures_suite.html` trước tiên**.
> - Không đọc toàn bộ file `test_result.xml` lớn (thường > 200MB) nếu chỉ cần tìm danh sách lỗi.
> - File nằm tại: `.../android-cts/results/<Session_ID>/test_result_failures_suite.html`.
> - Chứa sẵn 100% các ca FAILED kèm theo chi tiết Module, Class, Method, Error Message và Callstack.

---

## 3. Ma Trận Phương Án Hành Động Cho CTS on GSI

---

### Ca 1: Lỗi VHAL HVAC Seat/Fan Temperature (Thiếu Tín Hiệu CAN)
- **Module tiêu biểu:** `CtsCarTestCases`
- **Testcase đặc trưng:**
  - `android.car.cts.CarPropertyManagerTest#testHvacSeatTemperatureIfSupported`
  - `android.car.cts.CarPropertyManagerTest#testHvacFanDirectionIfSupported`
- **Callstack đặc trưng:**
  ```text
  java.lang.AssertionError: Expected HVAC seat temperature property to be available or return supported values, but threw CarServiceException / NOT_AVAILABLE.
  ```
- **Nguyên nhân:** Bản GSI không tự phát sinh tín hiệu CAN bus. Vehicle HAL (VHAL) trên thiết bị Nissan AIVI yêu cầu mạng CAN xe phải ở trạng thái Ignition ON (ACC/RUN) thì mới cấp quyền đọc/ghi thuộc tính điều hòa HVAC.
- **Phương án thiết bị (Device Action):**
  Bơm tín hiệu mô phỏng CAN bus qua cổng `/dev/canat` trên máy chủ Linux:
  ```bash
  # 1. Bật ứng dụng giám sát CANat trên DUT:
  adb -s <serial> shell am start -n com.lge.canat/.MainActivity
  
  # 2. Bơm tín hiệu CAN Ignition ON (VehicleStates:2:0):
  echo "VehicleStates:2:0" > /dev/canat
  adb -s <serial> shell am broadcast -a com.lge.canat.ACTION_SEND_CAN --es signal "VehicleStates:2:0"
  sleep 2
  
  # 3. Đồng bộ chu kỳ bus:
  echo "VehicleStates:0:0" > /dev/canat
  adb -s <serial> shell am broadcast -a com.lge.canat.ACTION_SEND_CAN --es signal "VehicleStates:0:0"
  ```
- **Câu lệnh Tradefed chính xác:**
  ```bash
  run cts-on-gsi -m CtsCarTestCases -t android.car.cts.CarPropertyManagerTest#testHvacSeatTemperatureIfSupported -s <serial>
  ```

---

### Ca 2: Lỗi Mạng Wi-Fi: "Limited Connection" / SSL Handshake Failed / Mất IP
- **Module tiêu biểu:** `CtsNetTestCases`, `CtsNativeNetDnsTestCases`, `StsHostTestCases`
- **Hiện tượng & Callstack đặc trưng:**
  - Thiết bị báo Wi-Fi: **"Limited Connection"** hoặc **"Connected, no internet"**.
  - Kiểm tra `dumpsys connectivity`: Capabilities chứa **`PARTIAL_CONNECTIVITY`** (thiếu cờ `VALIDATED`).
  - Kiểm tra `dumpsys network_stack` hoặc `dumpsys connectivity --diag`:
    ```text
    PROBE_HTTP http://connectivitycheck.gstatic.com/generate_204 => ret=204 OK
    PROBE_HTTPS https://www.google.com/generate_204 => javax.net.ssl.SSLHandshakeException: Chain validation failed
    DNS TLS dst{8.8.8.8} => javax.net.ssl.SSLHandshakeException: Chain validation failed
    ```
- **Nguyên nhân gốc rễ:**
  1. **Lệch đồng hồ hệ thống (System Clock Desync):** Bản build GSI sau khi flash hoặc reboot thường bị mất giờ, quay về quá khứ (ví dụ tháng 07/2026 trong khi thực tế là tháng 10/2026), và cờ `auto_time = 0`.
  2. Chứng chỉ SSL của Google chỉ có thời hạn 90 ngày và có trường `NotBefore` từ tháng 8 hoặc tháng 9/2026. Do ngày giờ hệ thống trước `NotBefore`, trình duyệt và Java SSL engine (`Conscrypt`) từ chối kết nối (`CertificateNotYetValidException` ➔ `Chain validation failed`).
  3. Gói tin HTTP thành công nhưng HTTPS bị chặn khiến Android xếp mạng vào trạng thái `PARTIAL_CONNECTIVITY`.
- **Phương án khắc phục chuẩn (Zero-touch, KHÔNG CẦN ROOT, KHÔNG FACTORY RESET):**
  ```bash
  # 1. Đồng bộ ngày giờ từ máy chủ Linux sang DUT bằng lệnh AlarmManager (không cần root):
  adb -s <serial> shell cmd alarm set-time $(date +%s%3N)
  adb -s <serial> shell settings put global auto_time 1

  # 2. Tắt cơ chế Captive Portal Probe (Bắt buộc cho môi trường lab test GSI):
  adb -s <serial> shell settings put global captive_portal_mode 0

  # 3. Kích hoạt lại Wi-Fi để cập nhật trạng thái Validated:
  adb -s <serial> shell svc wifi disable
  sleep 2
  adb -s <serial> shell svc wifi enable
  sleep 8

  # 4. Kiểm tra xác nhận kết quả:
  adb -s <serial> shell dumpsys connectivity | grep -E 'NetworkAgentInfo.*WIFI'
  # Đảm bảo cờ PARTIAL_CONNECTIVITY biến mất, xuất hiện cờ VALIDATED & IS_VALIDATED.
  ```

---

### Ca 3: Lỗi Tradefed Kẹt Thiết Bị: `Allocation: Unavailable` Sau Rớt USB
- **Hiện tượng đặc trưng:**
  Khi người dùng gõ lệnh `run retry ...`, Tradefed liên tục báo:
  ```text
  D/CommandScheduler: No available device matching all the config's requirements for cmd id X.
  Command will be rescheduled: [retry, ...]
  ```
  Trong khi `adb devices` ngoài OS vẫn nhìn thấy thiết bị bình thường.
- **Cách nhận biết:**
  - Trong console Tradefed gõ `list devices` (`l d`): Cột `State` là `ONLINE`, nhưng cột `Allocation` là **`Unavailable`**!
  - Gõ `dump commandQueue`: Thấy các lệnh retry bị kẹt ở trạng thái **`Wait_for_device`**.
- **Nguyên nhân gốc rễ:**
  - Thiết bị bị ngắt kết nối USB tạm thời trong khi đang chạy test (`usb disconnect` trong kernel log `dmesg`).
  - Tradefed bắt exception `DeviceWentOffline` và giải phóng thiết bị với cờ `DeviceAllocationState.Unavailable` để khóa an toàn. Tradefed không tự mở lại cờ này nếu không có tín hiệu reconnect mới.
- **Quy trình khắc phục chuẩn:**
  1. **Hủy toàn bộ lệnh đang nghẽn trong Queue** (Tránh kích hoạt đồng loạt hàng loạt lệnh retry đè lên nhau):
     ```text
     sts-tf > remove allCommands
     ```
  2. **Soft-reset kết nối ADB để Tradefed nhận lại thiết bị:**
     Chạy từ Linux terminal:
     ```bash
     adb -s <serial> reconnect
     ```
     *(Hoặc nếu Tradefed process bị treo lâu: gõ `exit` trong Tradefed console và chạy lại `./tools/sts-tradefed` hoặc `./tools/cts-tradefed`. Lịch sử các session cũ trong thư mục `results/` hoàn toàn không bị ảnh hưởng).*
  3. **Kiểm tra lại `list devices`**: Đảm bảo cột Allocation đã hiển thị **`Available`** rồi mới gửi lệnh retry tiếp theo.

---

### Ca 4: Lỗi GhidraPreparer TargetSetupError (GitHub API 403 Forbidden)
- **Module tiêu biểu:** `StsHostTestCases` (trong Security Test Suite / CTS on GSI).
- **Hiện tượng & Callstack:**
  ```text
  TargetSetupError: Please manually download the latest version of Ghidra zip from: [https://github.com/NationalSecurityAgency/ghidra/releases] to /tmp/tradefed_ghidra/ghidra.zip/ghidra.zip.
  Caused by: java.io.IOException: Server returned HTTP response code: 403 for URL: https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest
  ```
- **Nguyên nhân:** Tradefed cố gọi GitHub API để kiểm tra phiên bản Ghidra mới nhất, nhưng bị GitHub giới hạn request (Rate Limit 403).
- **Quy trình khắc phục:**
  1. Tạo thư mục cấu hình Ghidra offline:
     ```bash
     mkdir -p /tmp/tradefed_ghidra/ghidra.zip
     ```
  2. Copy file zip vào đúng đường dẫn **hệ thống Linux gốc** (LƯU Ý: Phải là `/tmp/...`, **không có** tiền tố `/home/lge`):
     ```bash
     cp /path/to/ghidra_*.zip /tmp/tradefed_ghidra/ghidra.zip/ghidra.zip
     ```
     *(Nếu trên máy đã có bản giải nén cũ tại `/tmp/tradefed_ghidra/ghidra_12.*.zip`, có thể dùng `cp -rl` copy thư mục sang `ghidra.zip/` để nhận diện file `support/analyzeHeadless` ngay lập tức mà không cần download lại).*

---

### Ca 5: Lỗi Màn Hình Khóa & Giao Diện Cửa Sổ (WindowManager)
- **Module tiêu biểu:** `CtsWindowManagerDeviceTestCases`
- **Phương án thiết bị (Device Action):**
  ```bash
  adb -s <serial> shell settings put global stay_on_while_plugged_in 7
  adb -s <serial> shell settings put secure lock_screen_lock_none true
  adb -s <serial> shell wm dismiss-keyguard
  adb -s <serial> shell wm size reset
  adb -s <serial> shell wm density reset
  adb -s <serial> shell input keyevent 3
  ```
- **Câu lệnh Tradefed chính xác:**
  ```bash
  run cts-on-gsi -m CtsWindowManagerDeviceTestCases --shard-count 2 -s <DUT1> -s <DUT2>
  ```

---

### Ca 6: Lỗi Tràn Hàng Đợi Statsd Telemetry
- **Module tiêu biểu:** `CtsStatsdAtomHostTestCases`
- **Phương án thiết bị (Device Action):**
  ```bash
  adb -s <serial> shell cmd statsd data-wipe
  ```
- **Câu lệnh Tradefed chính xác:**
  ```bash
  run retry --retry <session_id> -s <serial> --include-filter CtsStatsdAtomHostTestCases
  ```

---

### Ca 7: Gián Đoạn Tiến Trình Test (notExecuted > 0)
- **Nguyên nhân:** Mất kết nối USB hoặc console bị dừng.
- **Phương án thiết bị:** Kiểm tra ADB devices: `adb devices -l`.
- **Câu lệnh Tradefed chính xác:**
  ```bash
  run retry --retry <session_id> --retry-type NOT_EXECUTED -s <serial>
  ```

---

## 4. Chiến Lược 4 Tầng Điều Phối Lệnh Tradefed

1. **Tầng 1 - Baseline Run (Exclude 10 modules nặng để giảm tải và tránh timeout):**
   ```bash
   run cts-on-gsi \
     --exclude-filter "CtsMediaTestCases" \
     --exclude-filter "CtsDeqpTestCases" \
     --exclude-filter "CtsLibcoreTestCases" \
     --exclude-filter "CtsNetTestCases" \
     --exclude-filter "CtsNativeNetDnsTestCases" \
     --exclude-filter "CtsStatsdAtomHostTestCases" \
     --exclude-filter "CtsWindowManagerDeviceTestCases" \
     --exclude-filter "CtsCarTestCases" \
     --exclude-filter "CtsAppTestCases" \
     --exclude-filter "CtsLiblogTestCases" \
     --shard-count 2 -s <DUT1> -s <DUT2>
   ```
2. **Tầng 2 - Chạy Riêng Từng Module Bị Exclude (Targeted Isolation):**
   ```bash
   run cts-on-gsi -m <ModuleName> --shard-count 2 -s <DUT1> -s <DUT2>
   ```
3. **Tầng 3 - Tradefed Retry Loop:**
   ```bash
   run retry --retry <latest_session_id> --retry-type FAILED -s <serial>
   ```
4. **Tầng 4 - Xử Lý Lỗi Cứng (CANat cho HVAC, Đồng bộ giờ cho Wi-Fi, Single run `-t`).**

---

## 5. Cẩm Nang Lệnh Tradefed Console

| Thao Tác | Lệnh Console |
| :--- | :--- |
| Xem danh sách kết quả session | `l r` hoặc `list results` |
| Xem danh sách và trạng thái DUT | `l d` hoặc `list devices` |
| Xem tiến trình test đang chạy | `l i` hoặc `list invocations` |
| Xem hàng đợi các lệnh đang chờ | `dump commandQueue` |
| Hủy toàn bộ lệnh đang chờ | `remove allCommands` |
| Retry toàn bộ ca lỗi của session | `run retry --retry <ID> --retry-type FAILED -s <serial>` |
| Chạy lại các ca chưa chạy | `run retry --retry <ID> --retry-type NOT_EXECUTED -s <serial>` |
| Chạy đích danh 1 test case | `run cts-on-gsi -m <Mod> -t <Class>#<Method> -s <serial>` |
