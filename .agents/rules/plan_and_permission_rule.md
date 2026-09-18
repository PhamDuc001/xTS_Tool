---
trigger: always_on
---

# QUY TẮC BẮT BUỘC: LẬP PLAN CHI TIẾT & XIN PHÉP TRƯỚC KHI IMPLEMENT HOẶC PUSH CODE

## 1. CÁC ĐIỀU CẤM TUYỆT ĐỐI (STRICTLY PROHIBITED)
- ❌ **CẤM** tự ý tạo mới, sửa đổi hoặc xóa bất kỳ file nào trên máy Local (Windows), máy chủ Remote (Linux) hoặc thiết bị kiểm thử (DUT/Head Unit).
- ❌ **CẤM** tự ý chạy `git commit` hoặc `git push` code khi chưa có sự xác nhận của người dùng.
- ❌ **CẤM** tự ý chạy các lệnh can thiệp thay đổi trạng thái phần cứng/thiết bị (reboot, relay pcb, factory reset, flash sw) mà chưa hỏi ý kiến.

## 2. QUY TRÌNH THỰC THI (MANDATORY WORKFLOW)
1. **Trình bày Plan chi tiết:** Trước khi thực hiện bất kỳ thay đổi nào, Agent PHẢI trình bày:
   - Mục đích của hành động.
   - Danh sách file dự kiến tác động (kèm đường dẫn cụ thể).
   - Nội dung thay đổi / mã nguồn dự kiến tạo hoặc chỉnh sửa.
   - Các câu lệnh Shell / ADB / Git dự kiến chạy.
2. **Dừng lại và xin phép:** Agent PHẢI dừng turn và chờ phản hồi từ người dùng.
3. **Chỉ thực hiện khi được duyệt:** Chỉ khi người dùng nói "đồng ý", "tiến hành", "ok", "proceed" hoặc cho phép rõ ràng, Agent mới được phép gọi các công cụ ghi file hoặc chạy lệnh thực thi.
