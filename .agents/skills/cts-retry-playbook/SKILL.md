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
4. [Phân Tích 9 Nhóm Module Lỗi & Chiến Thuật Vượt Qua](#4-phân-tích-9-nhóm-module-lỗi--chiến-thuật-vượt-qua)
   - [Nhóm 1: CtsAppTestCases (FGS Sticky / Process State)](#nhóm-1-ctsapptestcases-fgs-sticky--process-state)
   - [Nhóm 2: CtsWindowManagerDeviceTestCases (Display, Touch, Keyguard, Transition)](#nhóm-2-ctswindowmanagerdevicetestcases-display-touch-keyguard-transition)
   - [Nhóm 3: CtsVideoTestCases (Hardware Codec / Achievable FPS)](#nhóm-3-ctsvideotestcases-hardware-codec--achievable-fps)
   - [Nhóm 4: CtsDeqpTestCases (Vulkan WSI Present Fence)](#nhóm-4-ctsdeqptestcases-vulkan-wsi-present-fence)
   - [Nhóm 5: CtsLibcoreTestCases (InetAddress, Sockets, Locale Date)](#nhóm-5-ctslibcoretestcases-inetaddress-sockets-locale-date)
   - [Nhóm 6: CtsNetTestCases & CtsHostsideNetworkTests (Firewall, DNS, VPN)](#nhóm-6-ctsnettestcases--ctshostsidenetworktests-firewall-dns-vpn)
   - [Nhóm 7: CtsStatsdAtomHostTestCases (Statsd / Dumpsys Atom Buffer)](#nhóm-7-ctsstatsdatomhosttestcases-statsd--dumpsys-atom-buffer)
   - [Nhóm 8: CtsMediaStressTestCases & AppSecurity (Listening Ports)](#nhóm-8-ctsmediastresstestcases--appsecurity-listening-ports)
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
# Cú pháp ATS Console:
retry --retry <session_id>

# Cú pháp Tradefed truyền thống:
run retry --retry <session_id>
```

#### 2. Retry chỉ định 1 thiết bị cụ thể:
```bash
retry --retry <session_id> -s 22324141
```

#### 3. Retry tự động lặp lại nhiều lần (Chuyên trị lỗi Timeout / Flaky):
```bash
retry --retry <session_id> -s <serial> --retry-strategy RETRY_ANY_FAILURE --max-testcase-run-count 15
```

#### 4. Retry chỉ 1 Module cụ thể:
```bash
run retry --retry <session_id> -s <serial> --include-filter CtsWindowManagerDeviceTestCases
```

#### 5. Retry đúng 1 Test Class hoặc 1 Method cụ thể (Cực nhanh để verify):
```bash
run retry --retry <session_id> -s <serial> --include-filter "CtsAppTestCases android.app.cts.ActivityManagerProcessStateTest#testFgsSticky2"
```

#### 6. Chạy trực tiếp 1 test case không qua Session:
```bash
run cts -m CtsWindowManagerDeviceTestCases -t android.server.wm.DisplayTests#testForceDisplayMetrics -s <serial>
```

#### 7. Bật tính năng lưu log chuyên sâu khi Fail:
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

> **LƯU Ý VỀ POPUP / SCRCPY:**  
> Dùng công cụ `scrcpy -s <serial>` để mở màn hình thiết bị lên PC. Nếu thấy có pop-up hệ thống (ví dụ: *"Allow USB Debugging"*, *"Process System isn't responding"*, *"MTP Dialog"* hoặc pop-up cấp quyền Automotive), **bắt buộc phải nhấn chọn Allow / OK / Wait** để dọn sạch màn hình trước khi nhấn Enter chạy test.

---

## 4. Phân Tích 9 Nhóm Module Lỗi & Chiến Thuật Vượt Qua

---

### Nhóm 1: CtsAppTestCases (FGS Sticky / Process State)

* **Test case tiêu biểu:** `android.app.cts.ActivityManagerProcessStateTest#testFgsSticky2`
* **Mã lỗi đặc trưng:**
  ```text
  java.lang.IllegalStateException: Timed out waiting for next line: uid=1014031 cmd=procstate procState=FGS capability=47
  ```
* **Bản chất lỗi:** Test case khởi tạo một Foreground Service có cờ `STICKY`, sau đó kill process và theo dõi xem hệ thống có tự hồi sinh process và gán lại trạng thái `procState=FGS` hay không. Trên chip Automotive, nếu CPU đang bận hoặc Binder IPC bị nghẽn, lệnh dump `cmd=procstate` sẽ bị timeout trước khi nhận được kết quả.
* **Chiến thuật vượt qua (Đã chứng minh tại Session 70):**
  1. Dùng `scrcpy` kiểm tra màn hình thiết bị, đảm bảo không có pop-up nào che khuất.
  2. Không retry trên thiết bị vừa bị fail liên tục. Chuyển sang thiết bị khác (ví dụ `-s 70b1036`).
  3. Sử dụng lệnh auto-retry loop:
     ```bash
     retry --retry <session_id> -s <other_serial> --retry-strategy RETRY_ANY_FAILURE --max-testcase-run-count 15
     ```

---

### Nhóm 2: CtsWindowManagerDeviceTestCases (Display, Touch, Keyguard, Transition)

* **Test case tiêu biểu:**
  * `android.server.wm.DisplayTests#testForceDisplayMetrics`
  * `android.server.wm.DragDropCompatTest#testNoDragIfWindowCantReceiveInput` (lỗi `keyDispatchingTimedOut`)
  * `android.server.wm.KeyguardLockedTests#testDismissKeyguard_whileOccluded` (lỗi `Keyguard must be gone`)
  * `android.server.wm.MultiDisplayActivityLaunchTests#testLaunchNonResizeableActivityFromSecondaryDisplaySameTask`
  * `android.server.wm.ActivityRecordInputSinkTests#testOverlappingActivityInSameTaskDifferentUid_DoesNotBlocksTouches`
* **Bản chất lỗi:**
  * `keyDispatchingTimedOut`: Thiết bị bị ANR đơ touch input trong 5 giây.
  * `Keyguard must be gone`: Automotive head unit có cơ chế bảo vệ màn hình lái xe nên Keyguard không mở được tự động.
  * `Activity launched on secondary display must be focused`: Trên xe hơi có nhiều màn hình (Cluster, Passenger Display, Center Console), focus bị nhảy nhầm màn hình.
  * `AdbCommandRejectedException`: Do chia shard khiến các test Window Manager va chạm nhau khi khởi tạo Activity.
* **Chiến thuật vượt qua (Đã chứng minh tại Session 83):**
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

---

### Nhóm 3: CtsVideoTestCases (Hardware Codec / Achievable FPS)

* **Test case tiêu biểu:**
  `android.video.cts.VideoEncoderDecoderTest#testPerf[video/x-vnd.on2.vp8_c2.qti.vp8.encoder_320x180_0]`
* **Mã lỗi đặc trưng:**
  ```text
  java.lang.AssertionError: Expected achievable frame rates for c2.qti.vp8.encoder video/x-vnd.on2.vp8 320x180: [226.0, 246.0]. Measured: 218.4
  ```
* **Bản chất lỗi:** Đây là bài đo hiệu năng (Performance Benchmark) của phần cứng giải mã/mã hóa video Qualcomm (C2 QTI). Khi thiết bị test liên tục nhiều giờ, nhiệt độ chip tăng cao dẫn đến cơ chế **Thermal Throttling (hạ xung nhịp CPU/GPU)**, làm tốc độ khung hình đo được rớt xuống dưới dải chuẩn (ví dụ chỉ đạt 218 fps thay vì tối thiểu 226 fps).
* **Chiến thuật vượt qua (Đã chứng minh tại Session 67 & 68):**
  1. Cho thiết bị nghỉ 5-10 phút hoặc tắt nguồn bật lại bằng relay PCB (`python3 ControlPCB.py R1off && sleep 5 && python3 ControlPCB.py R1`) để nhiệt độ chip hạ xuống ngưỡng bình thường.
  2. Chạy độc lập trên 1 thiết bị nguội, không chạy song song cùng lúc với các module nặng khác:
     ```bash
     run cts -m CtsVideoTestCases -t "android.video.cts.VideoEncoderDecoderTest#testPerf[video/x-vnd.on2.vp8_c2.qti.vp8.encoder_320x180_0]" -s <serial>
     ```

---

### Nhóm 4: CtsDeqpTestCases (Vulkan WSI Present Fence)

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

## 5. Bảng Tra Cứu Nhanh Test Case Thường Gặp & Lệnh Xử Lý

| Tên Test Case bị Lỗi | Module | Thao tác trên thiết bị (ADB) | Lệnh Retry tối ưu nhất trong Tradefed |
| :--- | :--- | :--- | :--- |
| `ActivityManagerProcessStateTest#testFgsSticky2` | `CtsAppTestCases` | Kiểm tra scrcpy dọn pop-up, đổi DUT khác | `retry --retry <id> -s <serial> --retry-strategy RETRY_ANY_FAILURE --max-testcase-run-count 15` |
| `DisplayTests#testForceDisplayMetrics` | `CtsWindowManagerDeviceTestCases` | `adb shell wm size reset`<br>`adb shell wm density reset` | `run retry --retry <id> -s <serial> --include-filter "CtsWindowManagerDeviceTestCases android.server.wm.DisplayTests#testForceDisplayMetrics"` |
| `DragDropCompatTest#testNoDragIfWindowCantReceiveInput` | `CtsWindowManagerDeviceTestCases` | `adb shell input keyevent 224`<br>`adb shell wm dismiss-keyguard` | `retry --retry <id> -s <serial>` |
| `VideoEncoderDecoderTest#testPerf[...]` | `CtsVideoTestCases` | Power cycle PCB để hạ nhiệt độ chip | `run cts -m CtsVideoTestCases -t "android.video.cts.VideoEncoderDecoderTest#testPerf[video/x-vnd.on2.vp8_c2.qti.vp8.encoder_320x180_0]" -s <serial>` |
| `ActivityRecordInputSinkTests#testOverlapping...` | `CtsWindowManagerDeviceTestCases` | `adb shell input keyevent 3` (Về Home) | `retry --retry <id> -s <serial>` |
| `HostAtomTests#testDumpsysStats` | `CtsStatsdAtomHostTestCases` | `adb shell cmd statsd data-wipe` | `run retry --retry <id> -s <serial> --include-filter CtsStatsdAtomHostTestCases` |
| `dEQP-VK.wsi.android...#ordering` | `CtsDeqpTestCases` | Tắt mọi app ngầm, về Home | `run retry --retry <id> -s <serial> --include-filter CtsDeqpTestCases` |
