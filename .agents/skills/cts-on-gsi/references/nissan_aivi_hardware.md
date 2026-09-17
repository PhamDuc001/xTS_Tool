# Kiến Trúc Môi Trường Kiểm Chuẩn Nissan AIVI Automotive

Tài liệu này mô tả chi tiết phần cứng, kết nối mạng, cơ chế giả lập xe hơi và các công cụ hỗ trợ trên hệ thống máy chủ kiểm chuẩn Nissan AIVI Android Automotive OS.

---

## 1. Thông Tin Máy Chủ & Cấu Hình Môi Trường

- **Địa chỉ máy chủ kiểm chuẩn:** `10.218.158.64`
- **Tài khoản mặc định:** `lge` / `lge@1234`
- **Thư mục Tradefed TestFolder:** `/home/lge/GoogleQA/TestFolder/GSI_cf8886c9,d930bf76/android-cts/`
- **Console thực thi:** `/home/lge/GoogleQA/TestFolder/GSI_cf8886c9,d930bf76/android-cts/tools/cts-tradefed`
- **Bộ công cụ AutoRetry nội bộ:** `/home/lge/Environment/tools/AutoRetry_V1.8_CTS_A14/`
- **TestPlan chuẩn:** `/home/lge/Environment/TestPlan/NissanEU_CTSonGSI_Full_Plan_PZ1D.xlsx`

---

## 2. Thiết Bị Kiểm Thử (DUT - Device Under Test)

- **Hệ thống IVI:** Nissan AIVI Automotive Head Unit (Gen 4 / PZ1D).
- **Hệ điều hành:** Android 14 (API 34) nạp bản Generic System Image (GSI) của Google.
- **Cấu hình đa thiết bị (Dual-DUT):**
  - DUT 1: Serial `cf8886c9`
  - DUT 2: Serial `d930bf76`
- **Kết nối ADB:** Cáp USB Type-C chuyên dụng chịu dòng cao kết nối trực tiếp vào máy chủ Linux qua hub chuẩn công nghiệp.

---

## 3. Hệ Thống Giả Lập Mạng CAN (CANat Simulation)

Trong môi trường kiểm thử phòng Lab (Bench Test), Head Unit không được gắn trên xe thực tế. Để các dịch vụ Car Service và Vehicle HAL (VHAL) hoạt động bình thường, hệ thống sử dụng hộp giả lập CANat:

- **Cổng giao tiếp Host:** `/dev/canat` hoặc cổng COM ảo USB-Serial.
- **Ứng dụng quản lý trên DUT:** `checkCanat.apk` (Package: `com.lge.canat`).
- **Tập lệnh điều khiển CANat:**
  - `python3 /home/lge/Environment/tools/AutoRetry_V1.8_CTS_A14/Canat/canat_control.py`
  - Gửi tín hiệu giả lập trạng thái chìa khóa / nguồn xe:
    - `VehicleStates:2:0`: Bật Ignition ON (ACC/RUN) - Bắt buộc cho các bài test VHAL, HVAC, Gear, Sensor.
    - `VehicleStates:0:0`: Tắt trạng thái kích hoạt sau khi test hoàn tất.

---

## 4. Bảng Điều Khiển Nguồn Rơ-le (Relay PCB Control)

Để tự động hóa việc khởi động lại phần cứng (Hard Reboot / Power Cycle) khi DUT bị treo ADB hoặc thermal throttling:

- **Script điều khiển:** `python3 /home/lge/Environment/tools/AutoRetry_V1.8_CTS_A14/Environment/scripts/ControlPCB.py`
- **Các lệnh cơ bản:**
  - Tắt nguồn cổng rơ-le 1: `python3 ControlPCB.py R1off`
  - Bật nguồn cổng rơ-le 1: `python3 ControlPCB.py R1`
  - Khởi động lại toàn bộ nguồn: `python3 ControlPCB.py R1off && sleep 5 && python3 ControlPCB.py R1`

---

## 5. Mạng & Cấu Hình Wi-Fi DUT

GSI thường không tự động lưu cấu hình Wi-Fi sau khi reboot hoặc đổi firmware.
- **Script kết nối Wi-Fi:** `/home/lge/Environment/tools/AutoRetry_V1.8_CTS_A14/Environment/scripts/connectWF.sh`
- **Cơ chế:**
  - Sử dụng APK `adbjoinwifi` (`com.steinwurf.adbjoinwifi`).
  - Gửi lệnh Broadcast Intent truyền SSID và mật khẩu Wi-Fi lab.
  - Ping kiểm tra Internet: `ping -c 3 www.google.com` hoặc `8.8.8.8`.
