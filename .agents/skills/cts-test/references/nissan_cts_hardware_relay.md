# Phần Cứng Môi Trường Kiểm Chuẩn CTS & Điều Khiển Relay PCB

Tài liệu này hướng dẫn chi tiết hệ thống phần cứng, cơ chế cấp nguồn và mạch rơ-le điều khiển tự động trên dàn máy kiểm chuẩn CTS máy chủ `10.218.153.44`.

---

## 1. Bản Đồ Ghép Nối Thiết Bị (Device Mapping)

Dàn máy kiểm chuẩn sử dụng 3 bộ Head Unit Nissan AIVI chạy đồng thời:

| Tên DUT | Serial Number (ADB) | Cổng Rơ-le Arduino | Lệnh Tắt Nguồn | Lệnh Bật Nguồn | Chu Kỳ Khởi Động Lại (Hard Reboot) |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **DUT 1** | `22324141` | Cổng 1 (Relay 1) | `R1off` | `R1` | `python3 ControlPCB.py R1off && sleep 5 && python3 ControlPCB.py R1` |
| **DUT 2** | `70b1036` | Cổng 2 (Relay 2) | `R2off` | `R2` | `python3 ControlPCB.py R2off && sleep 5 && python3 ControlPCB.py R2` |
| **DUT 3** | `5a9ba6a2` | Cổng 3 (Relay 3) | `R3off` | `R3` | `python3 ControlPCB.py R3off && sleep 5 && python3 ControlPCB.py R3` |

---

## 2. Giao Tiếp Mạch Relay Arduino (`ControlPCB.py`)

- **Vị trí script:** `/home/lge/Environment/scripts/ControlPCB.py`
- **Cổng kết nối Host:** `/dev/arduino` (USB Serial Converter)
- **Tốc độ truyền (Baud rate):** `9600 bps`
- **Mã nguồn cốt lõi:**
  ```python
  import sys, serial
  ser = serial.Serial('/dev/arduino', 9600)
  ser.write(bytes(str(sys.argv[1]), 'ascii'))
  ```

### Khi Nào Cần Sử Dụng Relay PCB?
1. **Thiết Bị Treo ADB (Offline / Unauthorized):**
   Khi thiết bị mất phản hồi ADB, không thể gõ `adb reboot`, chạy lệnh relay ngắt nguồn và bật lại để đưa DUT về trạng thái sạch.
2. **Hạ Nhiệt Độ Chip Xử Lý (Cool-down giải quyết Thermal Throttling):**
   Trước khi chạy lại các bài đo FPS Media Codec (`CtsVideoTestCases`, `CtsMediaDecoderTestCases`), ngắt nguồn thiết bị từ 5-10 phút để chip Qualcomm C2 QTI hạ nhiệt về dưới ngưỡng bảo vệ nhiệt của SoC.
3. **Reset Khối Bộ Nhớ Đệm và Dịch Vụ Hệ Thống:**
   Xóa sạch các deadlock ngầm của CarService, Binder IPC và SystemUI sau nhiều ngày chạy liên tục.

---

## 3. Khởi Động Lại Toàn Bộ Cụm 3 DUTs (Full Cluster Cycle)

Để reset toàn bộ cả 3 thiết bị cùng lúc trước khi bắt đầu một phiên chạy lớn:

```bash
python3 /home/lge/Environment/scripts/ControlPCB.py R1off
python3 /home/lge/Environment/scripts/ControlPCB.py R2off
python3 /home/lge/Environment/scripts/ControlPCB.py R3off
sleep 10
python3 /home/lge/Environment/scripts/ControlPCB.py R1
python3 /home/lge/Environment/scripts/ControlPCB.py R2
python3 /home/lge/Environment/scripts/ControlPCB.py R3
# Đợi 45 giây cho cả 3 thiết bị boot xong hệ thống Android
sleep 45
adb devices -l
```
