---
name: cts-on-gsi
description: >-
  Cẩm nang chẩn đoán lỗi và cố vấn phương án hành động (Action Plan & Command Advisor) cho bài kiểm thử CTS on GSI trên Android Automotive (Nissan AIVI).
  Đọc trực tiếp test_result_failures_suite.html của mỗi session, phân tích nguyên nhân lỗi (đặc biệt lỗi Car HVAC / VHAL do thiếu tín hiệu CAN bus, mất Wi-Fi GSI, hoặc timeout),
  và đưa ra phương án hành động chuẩn xác: can thiệp thiết bị (kích hoạt CANat, reboot, kết nối wifi IPv4/IPv6, keyguard) và câu lệnh Tradefed chính xác từng ký tự (include-filter, exclude-filter, not_executed, shard_count, -m, -t).
---

# CTS on GSI - Cẩm Nang Chẩn Đoán Lỗi & Chỉ Dẫn Hành Động Vận Hành (Advisor Playbook)

Skill này biến AI Agent thành **Chuyên Gia Chẩn Đoán Lỗi CTS on GSI (GSI Diagnostic & Command Advisor)** cho thiết bị Android Automotive OS (Nissan AIVI / Head Unit).

Khi người dùng yêu cầu kiểm tra trạng thái một hoặc nhiều session test CTS on GSI, Agent **không chạy script ở máy local**, mà trực tiếp đọc file báo cáo lỗi **`test_result_failures_suite.html`**, phân tích nguyên nhân gốc rễ và đưa ra **Phương án hành động cụ thể** để người dùng thao tác trực tiếp trên Linux console:
1. **Can thiệp phần cứng / thiết bị:** Bơm tín hiệu CAN bus qua CANat (`VehicleStates:2:0`), Soft reboot (`adb reboot`), nạp Wi-Fi GSI (IPv4 / IPv6), mở sáng và gỡ màn hình khóa, hay Factory reset?
2. **Bộ câu lệnh Tradefed chính xác từng ký tự:** Chỉ rõ cờ `run retry --retry <id> --retry-type FAILED`, `NOT_EXECUTED`, `--include-filter`, gom về 1 DUT (`-s <serial>`), hoặc chạy đích danh `-m <Module> -t <Class>#<Method>`.

---

## 📑 MỤC LỤC
1. [Quy Trình Phân Tích Báo Cáo Session (Failure HTML First)](#1-quy-trình-phân-tích-báo-cáo-session-failure-html-first)
2. [Ma Trận Phương Án Hành Động Cho CTS on GSI](#2-ma-trận-phương-án-hành-động-cho-cts-on-gsi)
   - [Ca 1: Lỗi VHAL HVAC Seat/Fan Temperature (Thiếu Tín Hiệu CAN)](#ca-1-lỗi-vhal-hvac-seatfan-temperature-thiếu-tín-hiệu-can)
   - [Ca 2: Lỗi Mất Kết Nối Mạng Wi-Fi Trên Bản GSI](#ca-2-lỗi-mất-kết-nối-mạng-wi-fi-trên-bản-gsi)
   - [Ca 3: Lỗi Màn Hình Khóa & Giao Diện Cửa Sổ (WindowManager)](#ca-3-lỗi-màn-hình-khóa--giao-diện-cửa-sổ-windowmanager)
   - [Ca 4: Lỗi Tràn Hàng Đợi Statsd Telemetry](#ca-4-lỗi-tràn-hàng-đợi-statsd-telemetry)
   - [Ca 5: Gián Đoạn Tiến Trình Test (notExecuted > 0)](#ca-5-gián-đoạn-tiến-trình-test-notexecuted--0)
3. [Chiến Lược 4 Tầng Điều Phối Lệnh Tradefed](#3-chiến-lược-4-tầng-điều-phối-lệnh-tradefed)
4. [Định Dạng Báo Cáo Bắt Buộc Của Agent Khi Tư Vấn Cho User](#4-định-dạng-báo-cáo-bắt-buộc-của-agent-khi-tư-vấn-cho-user)
5. [Cẩm Nang Lệnh Tradefed Console](#5-cẩm-nang-lệnh-tradefed-console)

---

## 1. Quy Trình Phân Tích Báo Cáo Session (Failure HTML First)

> [!IMPORTANT]
> **Nguyên tắc vàng:** Khi phân tích session CTS on GSI, **luôn đọc file `test_result_failures_suite.html` trước tiên**.
> - Không đọc toàn bộ file `test_result.xml` lớn nếu chỉ cần tìm danh sách lỗi.
> - File `test_result_failures_suite.html` nằm ngay trong thư mục session:  
>   `.../android-cts/results/<Session_ID>/test_result_failures_suite.html`.
> - Chứa sẵn 100% các ca FAILED kèm theo chi tiết Class, Method, Error Message và Stacktrace.

### Các bước phân tích:
1. Đọc bảng `<table class="summary">`: Trích xuất số lượng Passed, Failed, Modules Done / Total.
2. Đọc bảng `<table class="testdetails">`: Quét các dòng có `Result: fail` để lấy tên testcase và message lỗi chính.

---

## 2. Ma Trận Phương Án Hành Động Cho CTS on GSI

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
  Thực hiện bơm tín hiệu mô phỏng CAN bus qua cổng `/dev/canat` trên máy chủ Linux:
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
- **Câu lệnh Tradefed chính xác (Tradefed Command):**
  Chạy độc lập đích danh testcase trên 1 thiết bị ổn định:
  ```bash
  run cts-on-gsi -m CtsCarTestCases -t android.car.cts.CarPropertyManagerTest#testHvacSeatTemperatureIfSupported -s <serial>
  run cts-on-gsi -m CtsCarTestCases -t android.car.cts.CarPropertyManagerTest#testHvacFanDirectionIfSupported -s <serial>
  ```

---

### Ca 2: Lỗi Mất Kết Nối Mạng Wi-Fi Trên Bản GSI
- **Module tiêu biểu:** `CtsNetTestCases`, `CtsNativeNetDnsTestCases`
- **Nguyên nhân:** Bản GSI thường bị mất DHCP IP hoặc rớt Wi-Fi sau reboot.
- **Phương án thiết bị (Device Action):**
  ```bash
  # Bật Wi-Fi và kết nối qua adbjoinwifi:
  adb -s <serial> shell svc wifi enable
  adb -s <serial> shell am start -n com.steinwurf.adbjoinwifi/.MainActivity \
      -e ssid "<SSID>" -e password_type WPA -e password "<PASSWORD>"
  sleep 5
  # Kiểm tra thông mạng IPv4 & IPv6:
  adb -s <serial> shell ping -c 3 8.8.8.8
  ```
- **Câu lệnh Tradefed chính xác (Tradefed Command):**
  ```bash
  run retry --retry <session_id> -s <serial> --include-filter CtsNetTestCases
  ```

---

### Ca 3: Lỗi Màn Hình Khóa & Giao Diện Cửa Sổ (WindowManager)
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
- **Câu lệnh Tradefed chính xác (Tradefed Command):**
  Lặp lại module WindowManager từ 2-3 lần để đạt 100% Pass:
  ```bash
  run cts-on-gsi -m CtsWindowManagerDeviceTestCases --shard-count 2 -s <DUT1> -s <DUT2>
  ```

---

### Ca 4: Lỗi Tràn Hàng Đợi Statsd Telemetry
- **Module tiêu biểu:** `CtsStatsdAtomHostTestCases`
- **Phương án thiết bị (Device Action):**
  ```bash
  adb -s <serial> shell cmd statsd data-wipe
  ```
- **Câu lệnh Tradefed chính xác (Tradefed Command):**
  ```bash
  run retry --retry <session_id> -s <serial> --include-filter CtsStatsdAtomHostTestCases
  ```

---

### Ca 5: Gián Đoạn Tiến Trình Test (notExecuted > 0)
- **Nguyên nhân:** Mất kết nối USB hoặc console bị dừng.
- **Phương án thiết bị (Device Action):**
  Kiểm tra kết nối ADB: `adb kill-server && adb start-server && adb devices -l`.
- **Câu lệnh Tradefed chính xác (Tradefed Command):**
  ```bash
  run retry --retry <session_id> --retry-type NOT_EXECUTED -s <serial>
  ```

---

## 3. Chiến Lược 4 Tầng Điều Phối Lệnh Tradefed

1. **Tầng 1 - Baseline Run (Bắt buộc dùng Exclude Filter 10 modules nặng):**
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
4. **Tầng 4 - Xử Lý Lỗi Cứng (CANat cho HVAC, Wi-Fi reconnection, Single run `-t`).**

---

## 4. Định Dạng Báo Cáo Bắt Buộc Của Agent Khi Tư Vấn Cho User

Khi người dùng yêu cầu kiểm tra kết quả một session, Agent **PHẢI** xuất ra cấu trúc chuẩn sau:

```markdown
### 📊 1. TÌNH TRẠNG PHIÊN KIỂM THỬ (SESSION SUMMARY)
- **Session ID:** [Tên session]
- **Kế hoạch kiểm thử:** CTS on GSI
- **Kết quả:** Pass: [N] | Fail: [N] | NotExecuted: [N] | Modules Done: [X/Y]
- **Tỷ lệ đạt:** [XX.XX]%

---

### 🔍 2. PHÂN TÍCH NGUYÊN NHÂN LỖI (ROOT CAUSE ANALYSIS)
*(Trích xuất trực tiếp từ test_result_failures_suite.html)*
- **[Tên Module]** `ClassTest#methodTest`
  - *Callstack trích đoạn:* `...`
  - *Nguyên nhân gốc rễ:* [CANat chưa bật / Mất Wifi / Statsd đầy / UI lock...]

---

### 🛠️ 3. PHƯƠNG ÁN XỬ LÝ THIẾT BỊ (DEVICE ACTIONS)
1. Thao tác nguồn/reboot: [adb reboot / CANat signal / StayAwake...]
2. Thao tác ADB/Shell: [Các lệnh copy-paste để chạy trên terminal]

---

### 🚀 4. CÂU LỆNH TRADEFED CHÍNH XÁC (COPY-PASTE READY)
```bash
run retry --retry <session_id> ...
```
```

---

## 5. Cẩm Nang Lệnh Tradefed Console

| Thao Tác | Lệnh Console |
| :--- | :--- |
| Xem danh sách kết quả | `l r` hoặc `list results` |
| Xem danh sách thiết bị | `l d` hoặc `list devices` |
| Xem tiến trình test đang chạy | `l i` hoặc `list invocations` |
| Retry toàn bộ ca lỗi của session | `run retry --retry <ID> --retry-type FAILED -s <serial>` |
| Chạy lại các ca chưa chạy | `run retry --retry <ID> --retry-type NOT_EXECUTED -s <serial>` |
| Chạy đích danh 1 test case | `run cts-on-gsi -m <Mod> -t <Class>#<Method> -s <serial>` |
