# Kiến Trúc Chiến Lược Phối Hợp: Single-Multi Hybrid Plan

Tài liệu này giải thích cấu trúc và nguyên lý vận hành của kế hoạch kiểm thử chuẩn **`NissanEU_CTS_Plan_Multiple_Single.xlsx`** trên Android Automotive OS.

---

## 1. Tại Sao Phải Phân Tách Single & Multiple?

Kiểm thử toàn bộ CTS trên thiết bị Automotive gồm **815 modules** và hơn **2.1 triệu test cases**. Nếu đưa toàn bộ vào một câu lệnh chạy duy nhất:
1. **OOM & Rò rỉ Native Memory:** Các bài test Vulkan (`CtsDeqpTestCases` với 2,003,149 bài test) hoặc Media Codec ngốn hàng chục gigabyte RAM trên host và GPU memory trên DUT. Sau 8-10 tiếng, daemon Tradefed dễ bị văng hoặc rớt ADB.
2. **Xung Đột Giao Diện & Window Management:** `CtsWindowManagerDeviceTestCases` liên tục khởi tạo, phóng to, thu nhỏ và thay đổi mật độ màn hình. Nếu chạy chung shard với các module kiểm tra sensor hay mạng sẽ gây crash chéo.
3. **Chi Phí Retry Không Tưởng:** Nếu chạy gộp, mỗi lần retry Tradefed phải duyệt lại toàn bộ 815 modules trong subplan, làm tăng thời gian chuẩn bị lên hàng chục phút cho mỗi lượt thử.

---

## 2. Chi Tiết Danh Sách 14 Module Cô Lập (Single Execution)

Trong file `NissanEU_CTS_Plan_Multiple_Single.xlsx`, 14 module sau được chỉ định chạy độc lập với số lượt retry cấu hình riêng:

| STT | Tên Module | Lệnh Thực Thi | Số Lần Retry (`NumberOfRetry`) | Đặc Thù Kỹ Thuật |
| :---: | :--- | :--- | :---: | :--- |
| 1 | `CtsWindowManagerDeviceTestCases` | `run cts -m CtsWindowManagerDeviceTestCases` | 2 | Quản lý đa màn hình Automotive, chuyển đổi display metrics. Cần retry 2 lần để hội tụ 100%. |
| 2 | `CtsLibcoreTestCases` | `run cts -m CtsLibcoreTestCases` | 1 | Socket, mạng tầng thấp, múi giờ và đồng bộ ngày giờ. |
| 3 | `CtsNetTestCases` | `run cts -m CtsNetTestCases` | 1 | Firewall, kết nối Wi-Fi, kiểm tra route mạng. |
| 4 | `CtsStatsdAtomHostTestCases` | `run cts -m CtsStatsdAtomHostTestCases` | 1 | Bộ đệm logging statsd, thu thập telemetry hệ thống. |
| 5 | `CtsHostsideNetworkTests` | `run cts -m CtsHostsideNetworkTests` | 1 | VPN, Data Saver, kiểm soát lưu lượng nền. |
| 6 | `CtsAppTestCases` | `run cts -m CtsAppTestCases` | 1 | Foreground Services, Binder IPC, Activity Manager. |
| 7 | `CtsAutoFillServiceTestCases` | `run cts -m CtsAutoFillServiceTestCases` | 1 | Khung tự động điền mật khẩu và dữ liệu biểu mẫu. |
| 8 | `CtsDevicePolicyTestCases` | `run cts -m CtsDevicePolicyTestCases` | 1 | Quản lý thiết bị doanh nghiệp, quyền admin. |
| 9 | `CtsMultiUserHostTestCases` | `run cts -m CtsMultiUserHostTestCases` | 1 | Quản lý đa người dùng (Driver, Passenger) phía Host. |
| 10 | `CtsMultiUserTestCases` | `run cts -m CtsMultiUserTestCases` | 1 | Kiểm thử tài khoản phụ trên DUT. |
| 11 | `CtsDomainVerificationDeviceMultiUserTestCases` | `run cts -m CtsDomainVerificationDeviceMultiUserTestCases` | 1 | Xác thực domain và Android App Links. |
| 12 | `CtsAccessibilityServiceTestCases` | `run cts -m CtsAccessibilityServiceTestCases` | 2 | Dịch vụ trợ năng cho người khuyết tật, dễ lag UI. |
| 13 | `CtsEdiHostTestCases` | `run cts -m CtsEdiHostTestCases --no-skip-device-info` | 0 | Thu thập thông tin phần cứng điện tử (EDI). |
| 14 | `CtsDeqpTestCases` | `run cts -m CtsDeqpTestCases` | 0 | 2,003,149 bài test đồ họa Vulkan/OpenGL. Chạy cực nặng (~11 giờ). |

---

## 3. Lệnh Chạy 801 Module Chính (Multiple Main Run)

Sau khi tách 14 module trên, toàn bộ 801 module còn lại được chạy bằng một câu lệnh duy nhất với **26 Exclude Filters**:

```bash
run cts \
  --exclude-filter "CtsMediaTestCases" \
  --exclude-filter "CtsMediaTestCases[instant]" \
  --exclude-filter "CtsDeqpTestCases" \
  --exclude-filter "CtsLibcoreTestCases" \
  --exclude-filter "CtsNetTestCases" \
  --exclude-filter "CtsNetTestCases[instant]" \
  --exclude-filter "CtsStatsdAtomHostTestCases" \
  --exclude-filter "CtsStatsdAtomHostTestCases[instant]" \
  --exclude-filter "CtsWindowManagerDeviceTestCases" \
  --exclude-filter "CtsHostsideNetworkTests" \
  --exclude-filter "CtsHostsideNetworkTests[instant]" \
  --exclude-filter "CtsCarTestCases" \
  --exclude-filter "CtsAppTestCases" \
  --exclude-filter "CtsAppTestCases[instant]" \
  --exclude-filter "CtsAutoFillServiceTestCases" \
  --exclude-filter "CtsAutoFillServiceTestCases[instant]" \
  --exclude-filter "CtsDomainVerificationDeviceMultiUserTestCases" \
  --exclude-filter "CtsDevicePolicyTestCases" \
  --exclude-filter "CtsMultiUserHostTestCases" \
  --exclude-filter "CtsMultiUserTestCases" \
  --exclude-filter "CtsEdiHostTestCases" \
  --exclude-filter "CtsAccessibilityServiceTestCases" \
  --exclude-filter "CtsAccessibilityServiceTestCases[instant]" \
  --exclude-filter "CtsDevicePolicyTestCases[run-on-clone-profile]" \
  --exclude-filter "CtsDevicePolicyTestCases[run-on-secondary-user]" \
  --exclude-filter "CtsDevicePolicyTestCases[run-on-work-profile]" \
  --shard-count 3 -s 22324141 -s 70b1036 -s 5a9ba6a2
```

- **Cấu hình Sharding:** 3 Shards tương ứng với 3 thiết bị vật lý `22324141`, `70b1036`, `5a9ba6a2`.
- **Cấu hình Auto-Retry:** `NumberOfRetry = 4` (Tự động retry tối đa 4 vòng nếu có ca fail).

---

## 4. Cơ Chế Hợp Nhất Báo Cáo (Report Generator Integration)

Sau khi hoàn tất cả 14 single runs và multiple main run, công cụ `ReportGenerator.py` được kích hoạt:

```bash
python3 /home/lge/Environment/tools/GenerReport_Update_0623/ReportGenerator.py -p /home/lge/GoogleQA/P33B_26MY/03.REPORT/01.Full/
```

### Luồng xử lý của Report Generator:
1. Quét thư mục `android-cts/results/`, tìm kiếm các session hợp lệ có chứa `test_result.xml`.
2. Sắp xếp thứ tự session theo thời gian và phân loại module.
3. Giải nén và trích xuất kết quả cuối cùng (kết quả của lần retry thành công nhất) cho từng module.
4. Tổng hợp thành 3 cấu trúc thư mục báo cáo chuẩn:
   - `Internal/`: Báo cáo nội bộ đầy đủ logcat, screenshot và XML.
   - `OemApfe/`: Báo cáo tinh gọn định dạng OEM nộp hãng xe.
   - `OemApfeUpload/`: Các gói nén `.zip` sẵn sàng upload lên Google Partner Portal hoặc Aptra portal.
