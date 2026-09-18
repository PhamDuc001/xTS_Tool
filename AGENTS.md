# NGUYÊN TẮC BẮT BUỘC: LẬP PLAN CHI TIẾT & XIN PHÉP TRƯỚC KHI THỰC HIỆN

Tài liệu này định nghĩa quy tắc tối cao (Core Safety & Execution Policy) mà mọi AI Agent phải tuân thủ nghiêm ngặt trong suốt quá trình làm việc.

---

## ⛔ CÁC ĐIỀU CẤM TUYỆT ĐỐI (STRICTLY FORBIDDEN)

1. **CẤM TỰ Ý TẠO / SỬA / XÓA FILE:**
   - Không được tự ý tạo mới, chỉnh sửa, ghi đè hoặc xóa bất kỳ file nào trên máy tính Local (Windows).
   - Không được tự ý tạo, chỉnh sửa hoặc xóa file trên các máy chủ từ xa (Remote Linux Servers) qua SSH hoặc SFTP.
   - Không được tự ý nạp, cài đặt, hoặc ghi file vào các thiết bị kiểm thử phần cứng (DUT / Head Unit / Android Automotive) qua ADB hoặc fastboot.

2. **CẤM TỰ Ý GIT COMMIT & GIT PUSH:**
   - Tuyệt đối không tự ý chạy `git commit` hoặc `git push` lên repository nếu người dùng chưa xem xét và cho phép rõ ràng.

3. **CẤM TỰ Ý CHẠY CÁC LỆNH CAN THIỆP HỆ THỐNG / PHẦN CỨNG:**
   - Không tự ý chạy các lệnh thay đổi trạng thái phần cứng (Relay PCB, reboot, flash ROM, factory reset) mà không trình bày trước phương án và đợi sự đồng ý.

---

## 📋 QUY TRÌNH BẮT BUỘC 3 BƯỚC (THE 3-STEP PROTOCOL)

Khi nhận bất kỳ yêu cầu nào liên quan đến phát triển tính năng, sửa lỗi, tạo công cụ, can thiệp thiết bị hoặc cập nhật mã nguồn, Agent **BẮT BUỘC** thực hiện theo đúng 3 bước:

### Bước 1: Khảo Sát & Lập Kế Hoạch Chi Tiết (Plan First)
Agent chỉ được sử dụng các công cụ đọc/tra cứu (read-only tools) để khảo sát và trình bày **Kế hoạch chi tiết (Detailed Implementation Plan)** cho người dùng, bao gồm:
- **Mục tiêu:** Mô tả rõ mục đích của hành động.
- **Danh sách file dự kiến tác động:** Đường dẫn chính xác của từng file sẽ tạo mới hoặc sửa đổi (trên Local, Remote Linux Server, hoặc DUT).
- **Chi tiết nội dung/giải pháp:** Tóm tắt logic thay đổi, đoạn mã hoặc script dự kiến triển khai.
- **Các lệnh dự kiến thực thi:** Liệt kê đầy đủ các câu lệnh shell/ADB/Git sẽ chạy.

### Bước 2: Chờ Xác Nhận Của Người Dùng (Wait for Explicit Approval)
- Agent **PHẢI DỪNG LẠI** sau khi trình bày Plan và hỏi ý kiến người dùng.
- **KHÔNG ĐƯỢC PHÉP** tự ý suy đoán hoặc mặc định là người dùng đã đồng ý.
- Chỉ khi nhận được sự đồng ý rõ ràng (ví dụ: *"đồng ý"*, *"tiến hành"*, *"implement đi"*, *"ok"*...), Agent mới được bước sang Bước 3.

### Bước 3: Thực Thi Đúng Phạm Vi Đã Duyệt (Execute Within Approved Scope)
- Chỉ thực hiện chính xác những việc đã được nêu trong Plan đã được duyệt.
- Nếu phát sinh bất kỳ thay đổi nào ngoài phạm vi Plan ban đầu, Agent phải dừng lại và xin phép bổ sung.
