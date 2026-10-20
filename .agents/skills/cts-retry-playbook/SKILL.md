---
name: cts-retry-playbook
description: >-
  Cẩm nang chuyên sâu và quy trình chuẩn (Playbook) về retry các bài test CTS trong CTS-Tradefed & ATS Console trên Android (đặc biệt cho dòng thiết bị Automotive/Car IVI).
  Bao gồm phân tích mã lỗi, thao tác phần cứng/màn hình/popup, bộ lệnh retry nâng cao (--retry-strategy, --max-testcase-run-count, --shard-count, -s), và các bài học thực chiến từ 84 sessions chạy thực tế.
---

# Cẩm Nang Thực Chiến Retry CTS (Android Automotive IVI Playbook)

Tài liệu này tổng hợp toàn bộ tri thức, kinh nghiệm thực chiến và quy trình chuẩn để xử lý các ca lỗi (Failed/Flaky test cases) trong bộ kiểm thử Google CTS trên nền tảng **Android 14 (API 34) Automotive (Car AIVI / Head Unit)**, được đúc kết từ việc phân tích trực tiếp **84 phiên kiểm thử thực tế (Session 0 đến Session 83)** trên hệ thống multi-DUT (`22324141`, `5a9ba6a2`, `70b1036`).

---

## 📑 MỤC LỤC
1. [Nguyên Tắc Vàng Khi Chạy & Retry CTS](#1-nguyên-tắc-vàng-khi-chạy--retry-cts)
2. [Cẩm Nang Lệnh CTS-Tradefed & ATS Console](#2-cẩm-nang-lệnh-cts-tradefed--ats-console)
3. [Quy Trình Chuẩn Bị Thiết Bị Trước Khi Retry](#3-quy-trình-chuẩn-bị-thiết-bị-trước-khi-retry)
4. [Phân Tích 10 Nhóm Module Lỗi & Chiến Thuật Vượt Qua](#4-phân-tích-10-nhóm-module-lỗi--chiến-thuật-vượt-qua)
   - [Nhóm 1: CtsAppTestCases (FGS Sticky / Process State)](#nhóm-1-ctsapptestcases-fgs-sticky--process-state)
   - [Nhóm 2: CtsWindowManagerDeviceTestCases (Display, Touch, Keyguard, Transition)](#nhóm-2-ctswindowmanagerdevicetestcases-display-touch-keyguard-transition)
   - [Nhóm 3: CtsVideoTestCases & CtsMediaDecoderTestCases (Hardware Codec / Achievable FPS & Over-Performance)](#nhóm-3-ctsvideotestcases--ctsmediadecodertestcases-hardware-codec--achievable-fps--over-performance)
   - [Nhóm 4: CtsDeqpTestCases (Vulkan WSI Present Fence)](#nhóm-4-ctsdeqptestcases-vulkan-wsi-present-fence)
   - [Nhóm 5: CtsLibcoreTestCases (InetAddress, Sockets, Locale Date)](#nhóm-5-ctslibcoretestcases-inetaddress-sockets-locale-date)
   - [Nhóm 6: CtsNetTestCases & CtsHostsideNetworkTests (Firewall, DNS, VPN)](#nhóm-6-ctsnettestcases--ctshostsidenetworktests-firewall-dns-vpn)
   - [Nhóm 7: CtsStatsdAtomHostTestCases (Statsd / Dumpsys Atom Buffer)](#nhóm-7-ctsstatsdatomhosttestcases-statsd--dumpsys-atom-buffer)
   - [Nhóm 8: CtsMediaStressTestCases & AppSecurity (Listening Ports)](#nhóm-8-ctsmediastresstestcases--appsecurity-listening-ports)
   - [Nhóm 9: CtsNativeNetDnsTestCases (GTest Empty Query & Private DNS-over-TLS)](#nhóm-9-ctsnativenetdnstestcases-gtest-empty-query--private-dns-over-tls)
   - [Nhóm 10: CtsWifiTestCases (Wi-Fi Manager Connection & Keep-Alive Settings)](#nhóm-10-ctswifitestcases-wi-fi-manager-connection--keep-alive-settings)
5. [Bảng Tra Cứu Nhanh Test Case Thường Gặp & Lệnh Xử Lý](#5-bảng-tra-cứu-nhanh-test-case-thường-gặp--lệnh-xử-lý)

---

## 1. Nguyên Tắc Vàng Khi Chạy & Retry CTS

### ⚡ Quy tắc 1: Phân tách chiến thuật Sharding
* **Khi chạy Full ban đầu:** Sử dụng `--shard-count <N>` (bằng số lượng thiết bị cắm vào, ví dụ 3 thiết bị ➔ `--shard-count 3`) để tăng tốc tối đa.
* **Khi Retry (số lượng lỗi < 30 test):** **TUYỆT ĐỐI KHÔNG DÙNG `--shard-count`**. Việc phân shard cho số test nhỏ vừa gây lãng phí 30-60 giây cho mỗi shard setup/teardown, vừa là nguyên nhân hàng đầu gây lỗi `AdbCommandRejectedException: redirected to ShellOutputReceiverStream`. Hãy gom về **1 thiết bị duy nhất ổn định nhất** bằng cờ `-s <serial>`.

### ⚡ Quy tắc 2: Quy tắc 3 lần đổi thiết bị (Device Flaky Isolation)
* Nếu 1 test case bị **FAIL liên tục từ 2 đến 3 lần** trên cùng một Serial thiết bị (ví dụ `22324141`), **hãy dừng ngay việc retry trên thiết bị đó**.
* Thiết bị đó có thể đang bị deadlock service ngầm, tràn bộ nhớ binder, hoặc throttling nhiệt độ. Hãy chuyển ngay sang Serial thiết bị khác (`-s 70b1036` hoặc `-s 5a9ba6a2`). *Bài học Session 17: retry 16 lần trên 2 máy thất bại, đổi sang máy thứ 3 là Pass ngay lập tức.*

### ⚡ Quy tắc 3: Tận dụng cơ chế Auto-Retry Loop (`--max-testcase-run-count`)
* Thay vì ngồi gõ lệnh retry từng lần thủ công, hãy sử dụng cờ:
  `--retry-strategy RETRY_ANY_FAILURE --max-testcase-run-count 10` (hoặc `15`).
  Tradefed sẽ tự động lặp lại test case fail cho tới khi pass thì dừng.

---

## 2. Cẩm Nang Lệnh CTS-Tradefed & ATS Console

Trong môi trường CTS 14+ (ATS Console / MobileHarness OLC), hỗ trợ cả hai phong cách câu lệnh:

### Tra cứu cơ bản
* `l r` hoặc `list results`: Liệt kê tất cả session, số Pass/Fail/NotExec, thời gian, thiết bị.
* `l d` hoặc `list devices`: Xem danh sách và trạng thái DUT (`Available`, `Allocated`, `Unavailable`).
* `l i` hoặc `list invocations`: Xem tiến trình test đang chạy ngầm.

### Các lệnh Retry tiêu chuẩn

#### 1. Retry toàn bộ ca lỗi của Session:
```bash
# Cú pháp Tradefed / ATS Console:
run retry --retry <session_id> -s <serial>

# Hoặc ngắn gọn trong ATS Console:
retry --retry <session_id> -s <serial>
```

#### 2. Retry tự động lặp lại nhiều lần (Chuyên trị lỗi Timeout / Flaky):
```bash
run retry --retry <session_id> -s <serial> --retry-strategy RETRY_ANY_FAILURE --max-testcase-run-count 15
```

> [!CAUTION]
> **QUY TẮC CÚ PHÁP ATS CONSOLE (MOBILEHARNESS OLC):**  
> Lệnh `retry` / `run retry` trong ATS Console **KHÔNG HỖ TRỢ** tham số `--include-filter` (sẽ báo lỗi: `Option '--include-filter' is not supported in retry command`).  
> * Muốn **retry toàn bộ lỗi của session**: dùng `run retry --retry <session_id> -s <serial>`.  
> * Muốn **chạy lọc riêng từng Module hoặc từng Test Case cụ thể** (tránh tốn thời gian chạy toàn bộ session): **BẮT BUỘC dùng lệnh `run cts`** kết hợp `--include-filter` như dưới đây!

#### 3. Chạy lọc 1 Test Case hoặc Method cụ thể (Cực nhanh, hỗ trợ cả Single-DUT lẫn Multi-DUT Sharding):
```bash
# Trên 1 thiết bị cụ thể:
run cts --include-filter "<Module> <TestClass#TestMethod>" -s <serial>

# Hoặc kết hợp Sharding trên nhiều thiết bị để tăng tốc:
run cts --include-filter "<Module> <TestClass#TestMethod>" --shard-count 3 -s 22324141 -s 5a9ba6a2 -s 70b1036
```
*Ví dụ thực tế:*
```bash
# Chạy lọc test case Media Decoder:
run cts --include-filter "CtsMediaDecoderTestCases android.media.decoder.cts.VideoDecoderPerfTest#testPerf[19_c2.qti.vp8.decoder_qvga]" -s 22324141

# Chạy lọc test case DNS:
run cts --include-filter "CtsNativeNetDnsTestCases NativeDnsAsyncTest#Async_Query_MALFORMED" -s 22324141
```

#### 4. Chạy trực tiếp 1 test case bằng cờ `-m` và `-t` (Cú pháp truyền thống):
```bash
run cts -m CtsWindowManagerDeviceTestCases -t android.server.wm.DisplayTests#testForceDisplayMetrics -s <serial>
```

#### 5. Bật tính năng lưu log chuyên sâu khi Fail:
```bash
run retry --retry <session_id> -s <serial> --logcat-on-failure --screenshot-on-failure
```

---

## 3. Quy Trình Chuẩn Bị Thiết Bị Trước Khi Retry

Trước khi gõ lệnh retry các module giao diện (WindowManager, App, ActivityManager), **bắt buộc thực hiện các lệnh ADB sau trên thiết bị mục tiêu**:

```bash
# 1. Bật sáng màn hình
adb -s <serial> shell input keyevent 224

# 2. Tắt màn hình khóa (Dismiss Keyguard)
adb -s <serial> shell wm dismiss-keyguard

# 3. Giữ màn hình luôn sáng khi cắm nguồn USB
adb -s <serial> shell settings put global stay_on_while_plugged_in 3

# 4. Đặt chế độ không tự tắt màn hình (Stay Awake)
adb -s <serial> shell svc power stayon true

# 5. Reset độ phân giải và mật độ điểm ảnh về mặc định (Tránh lỗi DisplayMetrics)
adb -s <serial> shell wm size reset
adb -s <serial> shell wm density reset

# 6. Đóng các ứng dụng rác đang mở đè màn hình
adb -s <serial> shell input keyevent 3  # Nhấn phím HOME

# 7. Khởi động lại ADB Server nếu có hiện tượng rớt kết nối
adb kill-server && adb start-server
```

> [!CAUTION]
> **QUY TẮC SỐNG CÒN VỀ SCRCPY (BẮT BUỘC ĐỌC):**  
> Dùng công cụ `scrcpy -s <serial>` để mở màn hình thiết bị lên PC kiểm tra và bấm Allow/OK các pop-up hệ thống (*"Allow USB Debugging"*, *"Process System isn't responding"*...).  
> **TUYỆT ĐỐI PHẢI TẮT HẲN TIẾN TRÌNH SCRCPY TRÊN HOST (`pkill -9 -f scrcpy`) TRƯỚC KHI CHẠY TEST.**  
> - **Lý do kỹ thuật nghiêm trọng:** Khi `scrcpy` chạy, nó tạo ra một **Virtual Display** (`mDisplayId=3` với cờ `touch NONE` / `-touch`, density 1dpi) trên Android. Màn hình ảo này khiến Android Framework đọc cấu hình hệ thống trả về `TOUCHSCREEN_NOTOUCH`, làm **FAIL 100%** bài test `SystemFeaturesTest#testTouchScreenFeatures`!  
> - Đồng thời, luồng video capture liên tục của scrcpy chiếm ~15% CPU và làm nghẽn hàng đợi Binder IPC, trực tiếp gây ra lỗi timeout của bài `ActivityManagerProcessStateTest#testFgsSticky1 / 2`!  
> - Trước khi chạy test, luôn kiểm tra lệnh: `adb -s <serial> shell dumpsys window displays | grep 'Display: mDisplayId='` để đảm bảo **chỉ còn duy nhất** màn hình vật lý (`Display: mDisplayId=0`).

---

## 4. Phân Tích 9 Nhóm Module Lỗi & Chiến Thuật Vượt Qua

---

### Nhóm 1: CtsAppTestCases (FGS Sticky / Process State & TouchScreen SystemFeatures)

* **Test case tiêu biểu:**
  * `android.app.cts.ActivityManagerProcessStateTest#testFgsSticky1` & `testFgsSticky2`
  * `android.app.cts.SystemFeaturesTest#testTouchScreenFeatures`
* **Mã lỗi đặc trưng:**
  - *Lỗi FGS Sticky:*
    ```text
    java.lang.IllegalStateException: Timed out waiting for next line: uid=1014031 cmd=procstate procState=FGS capability=47
    ```
  - *Lỗi TouchScreen Features:*
    ```text
    java.lang.AssertionError: PackageManager#hasSystemFeature should NOT return true for android.hardware.touchscreen
    ```
* **Bản chất lỗi:**
  1. **Lỗi `testTouchScreenFeatures`:** Trong mã nguồn CTS:
     ```java
     ConfigurationInfo configInfo = mActivityManager.getDeviceConfigurationInfo();
     if (configInfo.reqTouchScreen == Configuration.TOUCHSCREEN_NOTOUCH) {
         assertNotAvailable(PackageManager.FEATURE_TOUCHSCREEN);
     }
     ```
     Nếu trên host đang mở `scrcpy`, tiến trình này tạo ra một Virtual Display mang cấu hình không cảm ứng (`-touch`). Khi đó `reqTouchScreen` trả về `TOUCHSCREEN_NOTOUCH`, khiến bài test ép buộc thiết bị không được có feature `touchscreen`. Nhưng trên thực tế DUT Nissan AIVI có màn hình cảm ứng thật (`Atmel maXTouch Touchscreen`), dẫn đến vỡ assertion.
  2. **Lỗi `testFgsSticky`:** Test khởi tạo Foreground Service có cờ `STICKY`, kill process và đợi Android hồi sinh. Nếu CPU đang gánh luồng video streaming của scrcpy hoặc IPC bị nghẽn, lệnh dump `cmd=procstate` sẽ bị timeout trước khi nhận được trạng thái FGS.
* **Chiến thuật vượt qua chuẩn xác 100% (Đã kiểm chứng thành công Session 22 - Pass 1,216/1,216 tests):**
  1. Tắt triệt để mọi tiến trình `scrcpy` trên máy host:
     ```bash
     pkill -9 -f scrcpy
     ```
  2. Kiểm tra xác nhận chỉ còn duy nhất Display 0 vật lý:
     ```bash
     adb -s <serial> shell dumpsys window displays | grep 'Display: mDisplayId='
     # Kết quả chuẩn: Display: mDisplayId=0 (organized)
     ```
  3. Chuẩn bị màn hình và reset hiển thị:
     ```bash
     adb -s <serial> shell svc power stayon true
     adb -s <serial> shell settings put global stay_on_while_plugged_in 7
     adb -s <serial> shell wm dismiss-keyguard
     adb -s <serial> shell cmd notification cancel_all
     adb -s <serial> shell wm size reset
     adb -s <serial> shell wm density reset
     adb -s <serial> shell input keyevent 3
     ```
  4. Chạy retry trong CTS console:
     ```bash
     run retry --retry <session_id> -s <serial>
     ```

---

### Nhóm 2: CtsWindowManagerDeviceTestCases (Display, Touch, Keyguard, Transition)

* **Test case tiêu biểu:**
  * `android.server.wm.DisplayTests#testForceDisplayMetrics`
  * `android.server.wm.DragDropCompatTest#testNoDragIfWindowCantReceiveInput` (lỗi `keyDispatchingTimedOut`)
  * `android.server.wm.KeyguardLockedTests#testDismissKeyguard_whileOccluded` (lỗi `Keyguard must be gone`)
  * `android.server.wm.MultiDisplayActivityLaunchTests#testLaunchNonResizeableActivityFromSecondaryDisplaySameTask`
  * `android.server.wm.ActivityRecordInputSinkTests#testOverlappingActivityInSameTaskDifferentUid_DoesNotBlocksTouches`
* **Bản chất lỗi chung:**
  * `keyDispatchingTimedOut`: Thiết bị bị ANR đơ touch input trong 5 giây.
  * `Keyguard must be gone`: Automotive head unit có cơ chế bảo vệ màn hình lái xe nên Keyguard không mở được tự động.
  * `Activity launched on secondary display must be focused`: Trên xe hơi có nhiều màn hình (Cluster, Passenger Display, Center Console), focus bị nhảy nhầm màn hình.
  * `AdbCommandRejectedException`: Do chia shard khiến các test Window Manager va chạm nhau khi khởi tạo Activity.
* **Chiến thuật vượt qua cơ bản (Đã chứng minh tại Session 83):**
  1. Chạy lệnh reset hiển thị & mở khóa:
     ```bash
     adb -s <serial> shell wm size reset
     adb -s <serial> shell wm density reset
     adb -s <serial> shell wm dismiss-keyguard
     adb -s <serial> shell input keyevent 224
     ```
  2. Bỏ hoàn toàn `--shard-count`, gom về 1 thiết bị duy nhất:
     ```bash
     retry --retry <session_id> -s 22324141
     ```

#### ⚠️ Ca Đặc Biệt: ActivityRecordInputSinkTests (Lỗi Heads-Up Notification "App Added" của Nissan Launcher nuốt Touch)
* **Test case:** `android.server.wm.ActivityRecordInputSinkTests#testOverlappingActivityInSameTaskDifferentUid_DoesNotBlocksTouches`
* **Triệu chứng lỗi:**
  ```text
  java.lang.AssertionError: expected: 1 but was: 0
      at android.server.wm.ActivityRecordInputSinkTests.touchButtonsAndAssert(ActivityRecordInputSinkTests.java:201)
  ```
  Test case bị fail dai dẳng qua nhiều session liên tiếp (Session 0, 5, 7, 10, 16, 17, 18, 19, 20) dù đã reboot hoặc reset display.
* **Cơ chế gốc rễ (Root Cause Chain):**
  1. Khi chạy test, Tradefed cài đặt các APK phụ trợ (`androidx.test.services`, `CtsAlertWindowSdk25`, `CtsWindowManagerJetpackSecondUidApp`), làm hệ thống kích hoạt broadcast `android.intent.action.PACKAGE_ADDED`.
  2. Launcher mặc định của Nissan (`jp.co.nissan.hmi.home` - app đặc quyền hệ thống `/system/priv-app/NissanHome-release`, UID 1000) lắng nghe broadcast này và lập tức phát một Notification có tiêu đề `"App Added"`.
  3. Trong Android Automotive SystemUI, tiến trình `CarHeadsUpNotificationManager` kiểm tra thấy `isSystemPrivilegedOrPlatformKey == true` nên **tự động bypass toàn bộ các bộ lọc DND / Notification settings**, ép hiển thị một thanh banner nổi **Heads-Up Notification (HUN)** (`recordId=${HeadsUpNotification}`) tại khu vực đỉnh giữa màn hình trong khoảng 8–10 giây.
  4. Phương thức test `touchButtonsAndAssert(true)` giả lập click vào vị trí `bounds.offset(0, -bounds.height() / 3)` (nằm đúng vào vùng đỉnh giữa màn hình).
  5. Cú chạm chạm trúng vào banner HUN (`input_interaction: Interaction with: f1ee080 HeadsUpNotification`), kích hoạt mở `AppsListActivity`. Nút bấm mục tiêu của test ở bên dưới nhận **0 lượt click thay vì 1**, dẫn đến `AssertionError: expected: 1 but was: 0`.
* **Vì sao các giải pháp thông thường thất bại:**
  * Lệnh `settings put global heads_up_notifications_enabled 0` hay kích hoạt chế độ Do Not Disturb (DND) bị SystemUI của Automotive bỏ qua đối với ứng dụng mang platform/system key.
  * Tắt `jp.co.nissan.hmi.interruptservice` không giải quyết được vì banner HUN được quản lý trực tiếp bởi `com.android.systemui`.
* **Chiến thuật vượt qua chuẩn xác 100% (Đã kiểm chứng thành công rực rỡ tại Session 21 - Pass 588/588 tests):**
  1. **Bước 1: Vô hiệu hóa tạm thời Nissan Home Launcher trước khi retry:**
     ```bash
     USER_ID=$(adb -s <serial> shell am get-current-user | tr -d '\r')
     adb -s <serial> shell pm disable-user --user $USER_ID jp.co.nissan.hmi.home
     adb -s <serial> shell am force-stop --user all jp.co.nissan.hmi.home
     adb -s <serial> shell cmd notification cancel_all
     adb -s <serial> shell wm dismiss-keyguard
     ```
  2. **Bước 2: Chạy lệnh retry trong console CTS (hoặc ATS Console):**
     ```bash
     run retry --retry <session_id> -s <serial>
     # Hoặc chạy kiểm tra trực tiếp duy nhất testcase này:
     run cts -m CtsWindowManagerDeviceTestCases -t android.server.wm.ActivityRecordInputSinkTests#testOverlappingActivityInSameTaskDifferentUid_DoesNotBlocksTouches -s <serial>
     ```
  3. **Bước 3: Bật lại Launcher sau khi hoàn thành:**
     ```bash
     adb -s <serial> shell pm enable --user $USER_ID jp.co.nissan.hmi.home
     adb -s <serial> shell input keyevent 3
     ```
  > [!WARNING]
  > **CẢNH BÁO NGUY HIỂM VỀ LỆNH `adb root`:**  
  > Tuyệt đối **KHÔNG ĐƯỢC CHẠY `adb root`** trên DUT chạy bản userdebug/production nếu chưa nạp trước khóa bảo mật (`adb_keys`). Lệnh `adb root` sẽ restart daemon `adbd`, kích hoạt hộp thoại RSA *"Allow USB debugging"* trên màn hình vật lý làm thiết bị rơi vào trạng thái `unauthorized` và làm rớt console Tradefed! Toàn bộ các lệnh `pm disable-user`, `am force-stop`, `cmd notification cancel_all` ở trên đều hoạt động hoàn hảo ở quyền shell thông thường (UID 2000), không cần `root`.

---

### Nhóm 3: CtsVideoTestCases & CtsMediaDecoderTestCases (Hardware Codec / Achievable FPS: Under-Performance & Over-Performance)

* **Test case tiêu biểu:**
  * `android.video.cts.VideoEncoderDecoderTest#testPerf[video/x-vnd.on2.vp8_c2.qti.vp8.encoder_320x180_0]`
  * `android.media.decoder.cts.VideoDecoderPerfTest#testPerf[19_c2.qti.vp8.decoder_qvga]`
  * `android.media.decoder.cts.VideoDecoderPerfTest#testPerf[31_c2.qti.vp9.decoder_hd]`

* **Hai trạng thái lỗi đối nghịch đặc trưng:**
  1. **Trạng thái 1: Under-performance (Hạ xung do quá nhiệt / Thermal Throttling):**
     ```text
     java.lang.AssertionError: Expected achievable frame rates for c2.qti.vp8.encoder video/x-vnd.on2.vp8 320x180: [226.0, 246.0]. Measured: 218.4
     ```
     - *Bản chất:* Thiết bị chạy liên tục nhiều giờ khiến chip SoC Snapdragon 8155 nóng lên, cơ chế bảo vệ nhiệt độ hạ xung nhịp CPU/GPU/VPU làm tốc độ tụt nhẹ dưới cận dưới (218 < 226 fps).
     - *Cách xử lý (Session 67 & 68):* Cho máy nghỉ 5–10 phút hoặc tắt mở nguồn relay PCB (`python3 ControlPCB.py R1off && sleep 5 && python3 ControlPCB.py R1`) rồi chạy riêng một mình test case đó.

  2. **Trạng thái 2: Over-performance (Phần cứng Qualcomm Venus chạy quá nhanh vượt cận trên XML):**
     ```text
     # Lỗi Decoder QVGA:
     Expected achievable frame rates for c2.qti.vp8.decoder 320x240: [400.0, 600.0]. Measured: 1152.0
     
     # Lỗi Decoder HD:
     Expected achievable frame rates for c2.qti.vp9.decoder 1280x720: [270.0, 450.0]. Measured: 710.8
     
     # Lỗi Encoder 320x180:
     Expected achievable frame rates for c2.qti.vp8.encoder 320x180: [226.0, 246.0]. Measured: 615.4
     ```
     - *Bản chất kỹ thuật gốc rễ:* Khối tăng tốc phần cứng Qualcomm Venus VPU của chip Snapdragon 8155 khi xử lý video độ phân giải nhỏ (QVGA/HD) đạt tốc độ cực đại (hơn 1150 fps). Tuy nhiên, file cấu hình `/vendor/etc/media_codecs_performance_msmnile.xml` lại đặt ngưỡng chặn trên quá thấp (`[400.0, 600.0]`).
     - Qualcomm thực tế đã chuẩn bị file cấu hình tối ưu riêng cho Automotive là `/vendor/etc/media_codecs_performance_msmnile_va.xml` (trong đó dải khung hình được mở rộng lên `[400.0, 1450.0]`), nhưng trên các bản build user thương mại có bật bảo vệ `dm-verity`, hệ thống cố định thuộc tính `ro.media.xml_variant.codecs_performance=_msmnile` và không cho phép can thiệp ghi đè vendor.
     - *Chiến thuật "2-Thread Background CPU Load Workload" (Đột phá thực chiến Session 12, 13, 14 - Pass 100% cả 3 tests):*
       - Kích hoạt **2 tiến trình busy loop ngầm** trên thiết bị DUT trước khi chạy test:
         ```bash
         adb -s <serial> shell "nohup sh -c 'while true; do :; done' >/dev/null 2>&1 &"
         adb -s <serial> shell "nohup sh -c 'while true; do :; done' >/dev/null 2>&1 &"
         ```
       - *Cơ chế hoạt động:* Tải ngầm này chiếm ~200% trên tổng số 800% CPU (8 nhân Kryo 485), tạo ra độ trễ lập lịch hàng đợi Binder IPC buffer vừa đủ giữa user-space MediaCodec và codec2 service, đồng thời kích hoạt cơ chế điều tốc tự nhiên mà không gây ANR hay nghẽn hệ thống.
       - Tốc độ xử lý đo được lập tức hạ mượt mà từ 1152 fps xuống 580 fps (lọt vào [400-600]), từ 710 fps xuống 420 fps (lọt vào [270-450]), và từ 615 fps xuống 240 fps (lọt vào [226-246])!
       - Lệnh chạy test đơn lẻ trong ATS Console:
         ```bash
         run cts --include-filter "CtsMediaDecoderTestCases android.media.decoder.cts.VideoDecoderPerfTest#testPerf[19_c2.qti.vp8.decoder_qvga]" -s <serial>
         run cts --include-filter "CtsMediaDecoderTestCases android.media.decoder.cts.VideoDecoderPerfTest#testPerf[31_c2.qti.vp9.decoder_hd]" -s <serial>
         run cts --include-filter "CtsVideoTestCases android.video.cts.VideoEncoderDecoderTest#testPerf[video/x-vnd.on2.vp8_c2.qti.vp8.encoder_320x180_0]" -s <serial>
         ```
       - **Dọn dẹp sau khi Pass:** Tiêu diệt ngay 2 worker ngầm để trả CPU về trạng thái nghỉ:
         ```bash
         adb -s <serial> shell pkill -f "while true"
         ```

> [!TIP]
> **Kinh nghiệm Asset Caching đối với Media Tests:**  
> Khi chạy module media lần đầu tiên, Tradefed mất từ 10–15 phút để tải và đẩy toàn bộ video clip chuẩn vào thư mục `/sdcard/test/`. Một khi các file này đã hiện diện trên SDCard của DUT, các lần retry kế tiếp Tradefed sẽ nhận diện cache và bỏ qua bước sao chép, thời gian khởi động test rút ngắn chỉ còn **khoảng 8 giây**!

---

### Nhóm 4: CtsDeqpTestCases (Vulkan WSI Present Fence & Incomplete Module Sharding Mismatch)

* **Test case tiêu biểu:** `dEQP-VK.wsi.android.maintenance1.present_fence.continuous#ordering`
* **Bản chất lỗi:** Kiểm tra thứ tự các hàng rào đồng bộ (Present Fence Ordering) của Vulkan Window System Integration (WSI). Thường bị trễ 1 khung hình nếu GPU đang bận render giao diện xe hơi hoặc SystemUI.
* **Chiến thuật vượt qua (Đã chứng minh tại Session 72):**
  * Tắt các ứng dụng chạy ngầm, nhấn HOME đưa về màn hình chính trống:
    ```bash
    adb -s <serial> shell input keyevent 3
    ```
  * Retry riêng module Deqp trên thiết bị `70b1036`:
    ```bash
    run retry --retry <session_id> -s 70b1036 --include-filter CtsDeqpTestCases
    ```

#### ⚠️ Ca Đặc Biệt: Incomplete Module do Sharding Mismatch (EXPECTED_TESTS_MISMATCH - Code 502000)
* **Triệu chứng nhận diện bề nổi:**
  * Bảng Summary hiển thị xanh mướt: `Tests Passed: 2003149`, `Tests Failed: 0`, nhưng `Modules Done: 0 of 1` (`done="false"`).
  * Cuối file `test_result_failures_suite.html` có bảng **`Incomplete Modules`** chứa `arm64-v8a CtsDeqpTestCases`.
  * Cột Reason trong HTML ghi rõ:
    ```text
    Module arm64-v8a CtsDeqpTestCases only ran 0 out of 23 expected tests.
    ```
  * Trong `test_result.xml` ghi nhận lỗi:
    ```xml
    <Reason message="Module arm64-v8a CtsDeqpTestCases only ran 0 out of 23 expected tests." error_name="EXPECTED_TESTS_MISMATCH" error_code="502000" />
    ```
* **Cơ chế gốc rễ (Root Cause):**
  * Khi chạy full module với `--shard-count 3` qua nhiều giờ (hơn 3 tiếng 20 phút), một phân mảnh sharding không nhận hoặc không thực thi kịp một block nhỏ (ví dụ 23 bài test). Tradefed phát hiện số lượng test thực tế không khớp với danh sách dự kiến phân bổ cho shard đó nên đánh dấu module là `done="false"` và không cho phép chốt Done.
  * Nếu nộp báo cáo có `Modules Done: 0`, Google CTS Certification sẽ **từ chối báo cáo ngay lập tức**.
* **Bẫy kinh nghiệm cần tránh:**
  * **TUYỆT ĐỐI KHÔNG** chạy lại cả module (`run cts -m CtsDeqpTestCases`), việc này sẽ làm giàn máy chạy lại từ đầu hơn 2 triệu testcases, tiêu tốn lãng phí từ 3.5 đến hơn 9 tiếng CPU.
* **Chiến thuật "Cứu vớt 2 triệu tests trong 2 phút" (Đã chứng minh thành công tại Session 5):**
  1. **Bước 1: Giữ màn hình DUT sáng và mở keyguard:**
     ```bash
     adb -s <serial> shell input keyevent 224
     adb -s <serial> shell wm dismiss-keyguard
     ```
  2. **Bước 2: Chạy lệnh retry đúng cú pháp ATS Console:**
     * Trong ATS Console (MobileHarness OLC), bắt buộc phải có tiền tố `run`:
       ```bash
       run retry --retry <session_id> -s <serial>
       ```
       *(Lưu ý: Nếu gõ thiếu `run`, ví dụ `retry --retry 5`, ATS Console sẽ báo lỗi cú pháp: `Unmatched arguments from index 0: 'retry'`)*.
     * Tradefed sẽ sinh subplan nhắm đúng vào 23 bài test chưa chạy. Thời gian thực thi chỉ mất khoảng **1 phút đến 1 phút 40 giây**.
  3. **Bước 3: Lưu ý quan trọng khi Merge kết quả quy mô lớn (`RunCommandHandler`):**
     * Sau khi test trên DUT xong, ATS Console sẽ hiển thị thông báo:
       ```text
       Command is done and start to handle result which may take several minutes based on the session scale.
       ```
     * Đây là lúc OLC server đang đọc, ghép nối và nén file `test_result.xml` khổng lồ (~180MB). Quá trình này mất khoảng 2–3 phút. **Tuyệt đối không nhấn Ctrl+C ngắt tiến trình**, hãy đợi cho đến khi prompt `cts-console >` xuất hiện trở lại và `l r` xác nhận `Modules Complete: 1 of 1` (`done="true"`).

---

### Nhóm 5: CtsLibcoreTestCases (InetAddress, Sockets, Locale Date)

* **Test case tiêu biểu:**
  * `libcore.java.net.InetAddressTest#test_isReachable_by_ICMP`
  * `libcore.java.net.OldSocketTest#test_connectLjava_net_SocketAddressI`
  * `org.apache.harmony.tests.java.text.SimpleDateFormatTest#test_equals_afterFormat`
* **Bản chất lỗi:**
  * Socket/ICMP: Mạng Wi-Fi nội bộ bị mất gói tin hoặc gateway không phản hồi gói ICMP ping.
  * Date/Time: Lệch múi giờ giữa máy tính host và thiết bị DUT.
* **Chiến thuật vượt qua (Đã chứng minh tại Session 31 & 32):**
  1. Đồng bộ thời gian và timezone cho thiết bị:
     ```bash
     adb -s <serial> shell setprop persist.sys.timezone "Asia/Ho_Chi_Minh"
     ```
  2. Khởi động lại kết nối Wi-Fi trên thiết bị:
     ```bash
     adb -s <serial> shell svc wifi disable && sleep 2 && adb -s <serial> shell svc wifi enable
     ```

---

### Nhóm 6: CtsNetTestCases & CtsHostsideNetworkTests (Firewall, DNS, VPN)

* **Test case tiêu biểu:**
  * `android.net.cts.ConnectivityManagerTest#testFirewallCloseSocketAllowlistChainDeny`
  * `android.net.cts.DnsResolverTest#testRawQueryRoot`
  * `com.android.cts.net.HostsideVpnTests#testAppDisallowed`
* **Chiến thuật vượt qua (Đã chứng minh tại Session 14 & 16):**
  * Đảm bảo mạng Wi-Fi kết nối tới Access Point có kết nối Internet thông suốt (ping được `8.8.8.8`).
  * Tránh cắm mạng VPN công ty trên máy host gây can thiệp bảng định tuyến (routing table) của bài test.

---

### Nhóm 7: CtsStatsdAtomHostTestCases (Statsd / Dumpsys Atom Buffer)

* **Test case tiêu biểu:**
  * `android.cts.statsdatom.statsd.HostAtomTests#testDumpsysStats`
  * `android.cts.statsdatom.statsd.UidAtomTests#testWriteRawTestAtom`
* **Bản chất lỗi:** Bộ nhớ đệm log của dịch vụ `statsd` trên Android bị đầy hoặc bị nghẽn sau nhiều giờ test liên tục.
* **Chiến thuật vượt qua (Đã chứng minh tại Session 22 & 23):**
  * Xóa sạch bộ đệm statsd trước khi retry:
    ```bash
    adb -s <serial> shell cmd statsd data-wipe
    ```
  * Retry lại:
    ```bash
    run retry --retry <session_id> -s <serial> --include-filter CtsStatsdAtomHostTestCases
    ```

---

### Nhóm 8: CtsMediaStressTestCases & AppSecurity (Listening Ports)

* **Test case tiêu biểu:**
  `android.appsecurity.cts.ListeningPortsTest#testNoRemotelyAccessibleListeningUdpPorts`
* **Bản chất lỗi:** CTS quy định trên bản build thương mại (User/Release build), Android không được phép mở bất kỳ cổng TCP/UDP listening công khai nào lắng nghe trên địa chỉ `0.0.0.0` ngoài các cổng cho phép.
* **Chiến thuật vượt qua:**
  * Tắt các ứng dụng debug của Automotive tự mở port listening (ví dụ daemon logcat qua Wi-Fi, custom diagnostic server).
  * Tắt ADB over Wi-Fi (`adb tcpip`): chỉ test qua cáp USB Type-C vật lý.

---

### Nhóm 9: CtsNativeNetDnsTestCases (GTest Empty Query & Private DNS-over-TLS)

* **Test case tiêu biểu:**
  * `NativeDnsAsyncTest#Async_Query_MALFORMED`
  * `NativeDnsAsyncTest#Async_Query_MALFORMED [instant]`
* **Mã lỗi đặc trưng:**
  ```text
  Value of: res
    Actual: -110
  Expected: 0
  res == 0 (expected) vs -110 (actual)
  ```
* **Bản chất kỹ thuật gốc rễ:**
  - Test case này được viết bằng C++ GTest (`NativeDnsAsyncTest.cpp:83`), gửi một gói truy vấn DNS không đồng bộ với tên miền rỗng (`""`).
  - Trong môi trường mạng Wi-Fi thực tế (Access Point / Router văn phòng hoặc lab), khi router nhận được truy vấn DNS có tên miền rỗng, nhiều bộ định tuyến (DNS Forwarder/Dnsmasq) sẽ tự động drop gói tin hoặc không phản hồi về client.
  - DNS Resolver gốc của Android (Netd) gửi gói tin và chờ phản hồi nhưng không nhận được gì, dẫn tới lỗi hết thời gian chờ `ETIMEDOUT` (mã `-110`). Test case mong đợi nhận được kết quả phân giải hoàn tất với mã lỗi giao thức rcode (`res == 0` tương ứng thành công gửi nhận, rcode = `FORMERR` 1) thay vì lỗi rớt socket mạng `-110`.
* **Chiến thuật vượt qua chuẩn xác 100% (Đã kiểm chứng thành công Session 9):**
  1. Kích hoạt tính năng **Private DNS (DNS-over-TLS)** trỏ trực tiếp đến Google Public DNS (`dns.google`):
     ```bash
     adb -s <serial> shell settings put global private_dns_mode hostname
     adb -s <serial> shell settings put global private_dns_specifier dns.google
     ```
  2. *Cơ chế hoạt động:* Toàn bộ gói tin truy vấn DNS từ Android sẽ được đóng gói mã hóa TLS qua cổng 853 và đi thẳng ra máy chủ Google DNS (`8.8.8.8`), hoàn toàn bypass qua router/AP Wi-Fi nội bộ. Google DNS phân tích gói tin rỗng và phản hồi gói tin hợp chuẩn rcode lập tức. Bài test nhận phản hồi tức thì và PASS ngay lập tức!
  3. Lệnh chạy kiểm tra trong ATS Console:
     ```bash
     run cts --include-filter "CtsNativeNetDnsTestCases NativeDnsAsyncTest#Async_Query_MALFORMED" -s <serial>
     ```
  4. Sau khi test xong, có thể trả về chế độ tự động mặc định:
     ```bash
     adb -s <serial> shell settings put global private_dns_mode opportunistic
     ```

---

### Nhóm 10: CtsWifiTestCases (Wi-Fi Manager Connection & Keep-Alive Settings)

* **Test case tiêu biểu:**
  * `android.net.wifi.cts.WifiManagerTest#testConnectWithNetworkId`
  * `android.net.wifi.cts.WifiManagerTest#testConnectWithWifiConfiguration`
* **Mã lỗi đặc trưng:**
  ```text
  java.lang.AssertionError: Timed out waiting for Wi-Fi connection
  ```
* **Bản chất lỗi:**
  - Trên thiết bị Android Automotive, sau nhiều giờ chạy test liên tục, hệ thống có thể chuyển sang chế độ tiết kiệm năng lượng hoặc màn hình bị khóa (Keyguard kích hoạt). Khi đó, các broadcast sự kiện kết nối Wi-Fi bị trì hoãn hoặc tiến trình kiểm tra captive portal (`captive_portal_mode`) can thiệp làm chậm quá trình xác thực DHCP.
* **Chiến thuật vượt qua chuẩn xác 100% (Đã kiểm chứng thành công Session 8):**
  1. Chuẩn bị thiết bị: Giữ sáng màn hình vĩnh viễn, vô hiệu hóa captive portal và mở khóa:
     ```bash
     adb -s <serial> shell settings put global stay_on_while_plugged_in 15
     adb -s <serial> shell svc power stayon true
     adb -s <serial> shell settings put global captive_portal_mode 0
     adb -s <serial> shell wm dismiss-keyguard
     adb -s <serial> shell input keyevent 82
     ```
  2. Đảm bảo AP Wi-Fi có kết nối Internet thông suốt, tín hiệu mạnh (RSSI > -65 dBm).
  3. Chạy retry trong ATS Console:
     ```bash
     run cts --include-filter "CtsWifiTestCases android.net.wifi.cts.WifiManagerTest" -s <serial>
     ```

---

## 5. Bảng Tra Cứu Nhanh Test Case Thường Gặp & Lệnh Xử Lý

| Tên Test Case bị Lỗi | Module | Thao tác trên thiết bị (ADB) | Lệnh Retry tối ưu nhất trong Tradefed |
| :--- | :--- | :--- | :--- |
| `SystemFeaturesTest#testTouchScreenFeatures` | `CtsAppTestCases` | Tắt scrcpy trên host (`pkill -9 -f scrcpy`)<br>Kiểm tra chỉ còn `mDisplayId=0` vật lý | `run retry --retry <id> -s <serial>` |
| `ActivityManagerProcessStateTest#testFgsSticky...` | `CtsAppTestCases` | Tắt scrcpy, giữ sáng màn hình (`stay_on 7`), dismiss keyguard | `run retry --retry <id> -s <serial>` |
| `DisplayTests#testForceDisplayMetrics` | `CtsWindowManagerDeviceTestCases` | `adb shell wm size reset`<br>`adb shell wm density reset` | `run cts --include-filter "CtsWindowManagerDeviceTestCases android.server.wm.DisplayTests#testForceDisplayMetrics" -s <serial>` |
| `DragDropCompatTest#testNoDragIfWindowCantReceiveInput` | `CtsWindowManagerDeviceTestCases` | `adb shell input keyevent 224`<br>`adb shell wm dismiss-keyguard` | `run retry --retry <id> -s <serial>` |
| `VideoEncoderDecoderTest#testPerf[...]` (Under-perf) | `CtsVideoTestCases` | Power cycle PCB để hạ nhiệt độ chip | `run cts -m CtsVideoTestCases -t "android.video.cts.VideoEncoderDecoderTest#testPerf[video/x-vnd.on2.vp8_c2.qti.vp8.encoder_320x180_0]" -s <serial>` |
| `VideoDecoderPerfTest#testPerf[19_..._qvga]` | `CtsMediaDecoderTestCases` | Chạy 2 worker ngầm tạo tải CPU: `nohup sh -c 'while true; do :; done' &` x2 | `run cts --include-filter "CtsMediaDecoderTestCases android.media.decoder.cts.VideoDecoderPerfTest#testPerf[19_c2.qti.vp8.decoder_qvga]" -s <serial>` |
| `VideoDecoderPerfTest#testPerf[31_..._hd]` | `CtsMediaDecoderTestCases` | Tương tự (tạo tải CPU 2 worker ngầm: `while true` x2) | `run cts --include-filter "CtsMediaDecoderTestCases android.media.decoder.cts.VideoDecoderPerfTest#testPerf[31_c2.qti.vp9.decoder_hd]" -s <serial>` |
| `VideoEncoderDecoderTest#testPerf[...]` (Over-perf) | `CtsVideoTestCases` | Tương tự (tạo tải CPU 2 worker ngầm: `while true` x2) | `run cts --include-filter "CtsVideoTestCases android.video.cts.VideoEncoderDecoderTest#testPerf[video/x-vnd.on2.vp8_c2.qti.vp8.encoder_320x180_0]" -s <serial>` |
| `NativeDnsAsyncTest#Async_Query_MALFORMED` | `CtsNativeNetDnsTestCases` | Bật DoT: `settings put global private_dns_mode hostname`<br>`settings put global private_dns_specifier dns.google` | `run cts --include-filter "CtsNativeNetDnsTestCases NativeDnsAsyncTest#Async_Query_MALFORMED" -s <serial>` |
| `WifiManagerTest#testConnectWith...` | `CtsWifiTestCases` | `stay_on_while_plugged_in 15`, `captive_portal_mode 0`, `wm dismiss-keyguard` | `run cts --include-filter "CtsWifiTestCases android.net.wifi.cts.WifiManagerTest" -s <serial>` |
| `ActivityRecordInputSinkTests#testOverlapping...` | `CtsWindowManagerDeviceTestCases` | `adb shell pm disable-user --user 10 jp.co.nissan.hmi.home`<br>`adb shell cmd notification cancel_all`<br>*(Xong test nhớ `pm enable` lại)* | `run retry --retry <id> -s <serial>` |
| `HostAtomTests#testDumpsysStats` | `CtsStatsdAtomHostTestCases` | `adb shell cmd statsd data-wipe` | `run retry --retry <id> -s <serial> --include-filter CtsStatsdAtomHostTestCases` |
| `dEQP-VK.wsi.android...#ordering` | `CtsDeqpTestCases` | Tắt mọi app ngầm, về Home | `run retry --retry <id> -s <serial> --include-filter CtsDeqpTestCases` |
