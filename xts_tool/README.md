# xTS Pre-Setup Manager (PyQt6)

Công cụ giao diện đồ họa (UI Tool) viết bằng Python (PyQt6) chạy trên Windows, dùng để quản lý kết nối SSH đến các máy Ubuntu Server và tự động hóa quy trình Pre-setup cho các bài kiểm thử Android Certification: **ATS**, **CTS**, **CTS on GSI (GSI)**, **STS**, **VTS**.

---

## 🌟 Tính Năng Nổi Bật

1. **Giao diện Đa Cửa Sổ (Multi-tab):**
   - Mỗi tab là một phiên làm việc độc lập với 1 PC Linux Ubuntu Server.
   - Thêm tab linh hoạt bằng nút **➕ Thêm Cửa Sổ Server Mới**.
   - Hỗ trợ lưu cấu hình server vào `config.json` để tự động load lại khi mở app.

2. **Cơ Chế Bảo Đảm Duy Nhất 1 Thiết Bị ("1 Device Only Enforcement"):**
   - Chạy lệnh `adb devices` và `fastboot devices` trên server từ xa.
   - **0 device**: Báo lỗi và khóa tiến trình chạy pre-setup.
   - **> 1 devices**: Cảnh báo số lượng và serial các thiết bị, yêu cầu người dùng ngắt bớt chỉ để lại duy nhất 1 thiết bị trước khi chạy.
   - **1 device**: Hiển thị trạng thái màu xanh (Serial, trạng thái `adb` hoặc `fastboot`).

3. **Tự Động Nhận Diện Đường Dẫn Binary (Userdebug & User):**
   - Mặc định truy cập vào thư mục gốc `/home/lge/Environment/Storage/Binary/`.
   - Sử dụng regex và quét file script để tự động tìm đường dẫn chứa bản build:
     - `sit.userdebug/.../RELEASE_...` chứa `./fastboot_n_fullnavi_blank_flash.sh`
     - `sit.user/.../RELEASE_...` chứa `./fastboot_n_fullnavi_reflash.sh`
   - Hiển thị Popup xác nhận đường dẫn (**Confirm Paths Dialog**) trước khi chạy, cho phép user kiểm tra, sửa đổi hoặc quét lại trực tiếp từ server.

4. **Đầy Đủ 5 Quy Trình Pre-setup Theo Guide YAK:**
   - **ATS**: Flash userdebug -> Google Attestation Key (hỗ trợ retry) -> MTC & Calibration (`do_calibration.sh`) -> Flash user -> Manual Authentication -> Lock Bootloader -> Manual Authentication.
   - **CTS**: Flash userdebug -> Google Attestation Key -> MTC -> Flash user -> Manual Authentication -> Lock Bootloader -> Manual Authentication.
   - **STS**: Flash userdebug -> Google Attestation Key -> MTC -> Lock Bootloader (không flash user, không authen thủ công).
   - **CTS on GSI**: Flash userdebug -> Google Attestation Key -> MTC -> Flash user -> Manual Authentication -> Flash GSI Boot-debug -> Flash GSI System image (`fastbootd`) -> Flash lại Boot.img gốc.
   - **VTS**: Flash userdebug -> Google Attestation Key -> MTC -> Flash user -> Manual Authentication -> Flash GSI Boot-debug -> Flash GSI System image (`fastbootd`).

5. **2 Chế Độ Chạy Linh Hoạt:**
   - **Bắt đầu chạy toàn bộ (Run All)**: Tự động chạy tuần tự từ bước đầu đến bước cuối (dừng lại khi có yêu cầu xác thực thủ công).
   - **Chạy từng bước (Step-by-step)**: Mỗi bước có nút **▶ Chạy bước này** riêng biệt, hỗ trợ debug hoặc re-flash từng công đoạn.

6. **Xử Lý Lỗi & Tương Tác Thủ Công (Interactive Dialogs):**
   - **Manual Authentication**: Khi đến bước xác thực trên màn hình thiết bị, xuất hiện popup nhắc nhở. Người dùng thao tác xong và bấm xác nhận để tiếp tục.
   - **Error Handling**: Khi script gặp lỗi, hiển thị hộp thoại với 3 lựa chọn: **[Thử lại (Retry)]**, **[Bỏ qua (Skip)]**, **[Hủy bỏ (Abort)]**.
   - **Real-time Log Viewer**: Xem log trực tiếp từ lệnh SSH (stdout/stderr) với màu sắc trực quan, hỗ trợ nút xóa log và lưu log ra file text.

7. **Thu Thập & Tổ Chức Báo Cáo (Collect & Organize Report):**
   - **Phân loại Session Data-driven**: Phân tích trực tiếp từ dữ liệu thực thi XML/HTML (`test_result.xml` / `test_result_failures_suite.html`), loại bỏ hoàn toàn việc phụ thuộc vào chuỗi câu lệnh Tradefed (`-m`, `-t`, `--include-filter`).
   - **Nhận diện Module Thông Minh**: Bóc tách chuẩn hóa các biến thể `[instant]`, `[secondary_user]`, đảm bảo module đơn lẻ chạy kèm instant app luôn được phân loại chính xác là Single Module.
   - **Hỗ trợ Gom Nhiều Module Retry (Targeted Multi-Module)**: Tự động gom các session retry nhiều module (`--include-filter`) thành thư mục `{id}.{moduleA_moduleB}` trong `Report/single/` khi có chứng cứ testcase pass.
   - **Cơ Chế Auto-Prune Session Cũ**: Khi retry thành công 100% cho nhóm multi-module, tool tự động dọn dẹp sạch các session fail cũ trong `results/` và `logs/`, chỉ giữ lại session pass mới nhất.
   - **Lọc Lịch Sử Chọn Lọc**: Áp dụng cơ chế "2 đầu + 2 cuối" cho các chuỗi retry dài để tối ưu dung lượng lưu trữ báo cáo.
   - **Tự động Phân Luồng & Tái Cấu Trúc Báo Cáo**:
     - Thư mục `Report/single/` tập trung toàn bộ module, testcase và nhóm multi-module đã có kết quả PASS.
     - Các module retry chưa pass được đưa ra ngoài thư mục gốc `Report/` để tester dễ dàng theo dõi.
     - Dữ liệu Multiple toàn suite được tổ chức trực tiếp tại `Report/results/` và `Report/logs/`.
     - Chi tiết quy chuẩn xem tại [COLLECT_REPORT_SPEC.md](docs/COLLECT_REPORT_SPEC.md).


---

## 🚀 Cách Cài Đặt & Khởi Chạy

### Yêu Cầu Môi Trường
- Windows OS
- Python 3.10+ (Đã cài sẵn `py -3`)
- Các thư viện Python:
  ```powershell
  py -3 -m pip install PyQt6 paramiko
  ```

### Khởi Chạy Nhanh
- Nhấp đúp chuột vào file:
  ```
  D:\Training\Guide\YAK\xts_tool\run_tool.bat
  ```
- Hoặc mở PowerShell/CMD và chạy:
  ```powershell
  cd D:\Training\Guide\YAK\xts_tool
  py -3 main.py
  ```

---

## ⚙ Cấu Trúc File & Thư Mục

```
D:\Training\Guide\YAK\xts_tool\
├── main.py                     # File khởi chạy chính
├── main_window.py              # Giao diện chính quản lý các tab server
├── server_tab.py               # Giao diện và logic của từng tab server
├── workflow_runner.py          # Luồng thực thi (QThread) các bước pre-setup
├── ssh_client.py               # Quản lý kết nối SSH và stream command Paramiko
├── device_checker.py           # Module phân tích adb devices & fastboot devices
├── confirm_paths_dialog.py     # Hộp thoại xác nhận đường dẫn, authen và xử lý lỗi
├── config.json                 # Cấu hình server mẫu, đường dẫn mặc định và timeout
├── run_tool.bat                # File batch click đúp để mở tool trên Windows
└── README.md                   # Tài liệu hướng dẫn sử dụng
```
