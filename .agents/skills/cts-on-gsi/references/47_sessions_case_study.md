# Case Study Thực Chiến: 47 Sessions CTS on GSI Đạt 100% Pass (0 Fails)

Tài liệu này ghi lại chi tiết quá trình kiểm thử thực tế trên hệ thống máy chủ kiểm chuẩn **Nissan AIVI Android Automotive OS 14 (API 34)**:
- **Server:** `10.218.158.64` (User: `lge`)
- **Đường dẫn kết quả:** `/home/lge/GoogleQA/TestFolder/GSI_cf8886c9,d930bf76/android-cts/results/`
- **Bộ DUT:** 2 thiết bị cắm song song (`cf8886c9`, `d930bf76`)
- **Test Plan:** `cts-on-gsi`
- **Kết quả chung cuộc:** **139,287 test cases PASS, 0 FAIL, 0 NOT_EXECUTED (100.0% Pass)**.

---

## 1. Tiến Trình 47 Sessions Hội Tụ Về 100% Pass

| Giai đoạn | Phiên (Session) | Tổng Pass | Tổng Fail | Tổng NotExec | Hành động thực hiện | Ghi chú kỹ thuật |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Giai đoạn 1** | Session 0 | 139,057 | 200 | 30 | Chạy Baseline với Exclude Filter 10 modules nặng | Chạy ~16 giờ trên 2 shards (`cf8886c9`, `d930bf76`). Tránh crash do OOM/quá nhiệt. |
| **Giai đoạn 2** | Session 1 – 10 | 139,120 | 137 | 0 | Chạy độc lập từng module bị exclude (Targeted Module Isolation) | `CtsDeqpTestCases`, `CtsMediaTestCases`, `CtsLibcoreTestCases` được bổ sung. |
| | Session 11 – 14 | 139,180 | 77 | 0 | Chạy lặp `CtsWindowManagerDeviceTestCases` 3 lần | Tăng dần từ 874 Pass -> 880 Pass 100%. |
| **Giai đoạn 3** | Session 15 – 35 | 139,260 | 18 | 0 | Vòng lặp `run retry --retry <id> --retry-type FAILED` | Tradefed tự sinh subplan `tf_retry_session_#...`, tự gộp kết quả. |
| | Session 36 – 44 | 139,285 | 2 | 0 | Chuyển sang 1 DUT ổn định nhất, dọn dẹp bộ đệm statsd, reset Wi-Fi | Khắc phục các lỗi ngẫu nhiên (flaky) do mạng và IPC binder. |
| **Giai đoạn 4** | Session 45 | **139,287** | **0** | **0** | **ĐẠT 100% PASS TOÀN BỘ BÀI TEST CTS ON GSI** | Toàn bộ 133 modules done, không còn bất kỳ ca lỗi nào. |
| **Sanity Check**| Session 46 | 2 | 0 | 0 | Chạy riêng 2 test case HVAC qua CANat để xác thực ổn định | `testHvacSeatTemperatureIfSupported`, `testHvacFanDirectionIfSupported` PASS. |

---

## 2. Phân Tích Chi Tiết Ca Lỗi Khó Nhất: HVAC Car Property

### Hiện tượng lỗi tại Session 44:
```text
android.car.cts.CarPropertyManagerTest#testHvacSeatTemperatureIfSupported: FAIL
java.lang.AssertionError: Expected HVAC seat temperature property to be available or return supported values,
but threw CarServiceException / NOT_AVAILABLE.

android.car.cts.CarPropertyManagerTest#testHvacFanDirectionIfSupported: FAIL
java.lang.AssertionError: Expected HVAC fan direction property to return valid direction flags.
```

### Nguyên nhân gốc rễ (Root Cause):
1. Đây là các bài test tương tác trực tiếp với **Vehicle HAL (VHAL)** của Android Automotive.
2. VHAL trên Head Unit Nissan chỉ kích hoạt và trả về dữ liệu hợp lệ khi hệ thống mạng CAN trên xe (hoặc thiết bị mô phỏng CAN) báo trạng thái **Ignition = ON (ACC / RUN)**.
3. Khi chạy test dài ngày, thiết bị mô phỏng CANat (cổng `/dev/canat`) bị sleep hoặc không broadcast chu kỳ frames nhiệt độ ghế (`HVAC_SEAT_TEMPERATURE`) và hướng gió quạt (`HVAC_FAN_DIRECTION`), khiến CarService timeout và coi như lỗi phần cứng.

### Giải pháp khắc phục triệt để (Session 45 & 46):
1. Kích hoạt lại CANat và cấp quyền trên DUT:
   ```bash
   adb -s <serial> install -r checkCanat.apk
   adb -s <serial> shell am start -n com.lge.canat/.MainActivity
   ```
2. Gửi tín hiệu giả lập CAN qua cổng CANat:
   - Gửi tín hiệu trạng thái xe: `VehicleStates:2:0` (Chuyển sang IGNITION ON).
   - Đợi 2 giây đồng bộ bus, sau đó gửi: `VehicleStates:0:0`.
3. Kiểm tra logcat VHAL:
   ```bash
   adb -s <serial> logcat -s CarPropertyManager VehicleHal
   ```
   Xác nhận log `HVAC properties available and responding`.
4. Chạy lại đúng 2 test case:
   ```bash
   run cts-on-gsi -m CtsCarTestCases -t android.car.cts.CarPropertyManagerTest#testHvacSeatTemperatureIfSupported -s <serial>
   run cts-on-gsi -m CtsCarTestCases -t android.car.cts.CarPropertyManagerTest#testHvacFanDirectionIfSupported -s <serial>
   ```
5. Kết quả: Cả 2 test case chuyển sang **PASS ngay trong lần thử đầu tiên**.

---

## 3. Các Bài Học Kinh Nghiệm Rút Ra (Key Takeaways)

1. **Không bao giờ chạy full 139,000 test cùng 1 lúc không có filter:**
   Bản build GSI chạy trên phần cứng OEM ô tô rất dễ gặp hiện tượng rò rỉ bộ nhớ native sau 8-10 tiếng chạy các module đồ họa (`CtsDeqpTestCases`) hoặc đa phương tiện (`CtsMediaTestCases`). Việc chia tách 10 module nặng ra chạy riêng (Tầng 1 & Tầng 2) là chìa khóa giúp giữ tính toàn vẹn của Session.

2. **Dừng sharding khi số lượng lỗi < 20:**
   Khi chỉ còn dưới 20 ca fail, việc chạy 2 shards khiến 2 DUT chia nhau mỗi máy 10 ca, nhưng chi phí khởi tạo Tradefed shard invocation mất từ 2 đến 3 phút. Đồng thời nguy cơ 1 DUT bị rớt kết nối ADB sẽ làm hỏng toàn bộ session. Hãy chọn 1 DUT ổn định nhất để xử lý dứt điểm.

3. **Tradefed Subplan Merge Logic:**
   Mỗi lần chạy `run retry --retry <session_id> --retry-type FAILED`, Tradefed không ghi đè session cũ mà tạo session mới với timestamp mới. File `test_result.xml` của session mới tự động kế thừa (merge) toàn bộ các kết quả PASS của các session trước đó, chỉ ghi nhận kết quả mới của các testcase vừa chạy lại. Vì vậy, luôn lấy Session ID mới nhất (`latest_session_id`) cho lần retry tiếp theo.
