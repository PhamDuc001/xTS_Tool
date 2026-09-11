# Danh Sách Các Điểm Cần Làm Rõ Trước Khi Tích Hợp "Generate Report" Vào `xTS_Tool`

Tài liệu này tổng hợp toàn bộ các thắc mắc kỹ thuật, các điểm chưa rõ ràng hoặc các trường hợp biên (edge cases) sau khi nghiên cứu kỹ bộ tài liệu đặc tả tại thư mục `docs/GenerateReport_Specification` ([01_WORKFLOW_OVERVIEW.md](./01_WORKFLOW_OVERVIEW.md), [02_STEP_BY_STEP_PIPELINE.md](./02_STEP_BY_STEP_PIPELINE.md), [03_DATA_DICTIONARY_AND_FORMATS.md](./03_DATA_DICTIONARY_AND_FORMATS.md), [04_INTEGRATION_REQUIREMENTS_XTS_TOOL.md](./04_INTEGRATION_REQUIREMENTS_XTS_TOOL.md)).

---

## 1. Cơ Chế Kích Hoạt & Đồng Bộ Với Server APTRA (Bước 4 & Bước 5)

1. **Cách thức kích hoạt công cụ phân tích trên APTRA:**
   - Trong tài liệu [02_STEP_BY_STEP_PIPELINE.md](./02_STEP_BY_STEP_PIPELINE.md) ghi: *"Bước 5: Chạy công cụ phân tích APTRA (Analysis Engine)"*.
   - **Thắc mắc:** Công cụ này được kích hoạt như thế nào?
     - **Phương án A:** Server APTRA chạy ngầm daemon/cron tự động quét thư mục `/nas/APTRA/{Project}/{Version}/` khi có dữ liệu mới đẩy vào?
     - **Phương án B:** Server 66 (hoặc tool từ client) phải SSH vào `aptra@loghub.lge.com` và thực thi một lệnh script cụ thể? Nếu là lệnh script, đường dẫn chính xác và các tham số truyền vào là gì?
     - **Trả lời (User):** Phương án A. Khi đến bước này, hiện pop-up yêu cầu user request chạy server APTRA để tạo các file sau khi upload các file lên server APTRA. Khi user confirm OK request xong thì đến bước tiếp theo.
2. **Cơ chế xác định APTRA đã phân tích xong:**
   - Sau khi đồng bộ dữ liệu sang APTRA, tool làm thế nào để biết quá trình phân tích hoàn tất và các file `.xlsx`, `.csv` đã sẵn sàng để tải về?
   - **Trả lời (User):** User sẽ confirm tại Pop-up trước đó là quá trình chạy generate trên APTRA đã hoàn tất.
   - Thời gian chờ phân tích trung bình là bao lâu? Cần thiết lập timeout tối đa là bao nhiêu phút (ví dụ: polling mỗi 10 giây, tối đa 15 phút)?
   - **Trả lời (User):** User sẽ confirm OK là sẽ hoàn tất.
   - **Khuyến nghị bổ sung:** Khi người dùng bấm "OK / Đã Chạy Xong", Tool sẽ thực hiện một bước kiểm tra nhanh (Validation Check) kiểm tra sự tồn tại của file `YAK.31.03.30_summary.csv` hoặc các file `*Result.xlsx` trên APTRA. Nếu đã có đủ file thì đi tiếp, nếu chưa có file thì nhắc nhở người dùng kiểm tra lại trạng thái server APTRA.

---

## 2. Giao Tiếp Mạng & Phương Thức Truyền Dữ Liệu Giữa Các Server

1. **Phương thức truyền file giữa Server 66 và APTRA / GOOGLEQA:**
   - Tài liệu nêu kiến trúc: Server 66 chuyển dữ liệu sang APTRA và GOOGLEQA (cùng IP `10.158.15.144` / `loghub.lge.com` nhưng khác user: `aptra` và `googleqa`).
   - **Thắc mắc:** Lệnh copy giữa Server 66 sang APTRA/GOOGLEQA được thực hiện bằng cách nào?
     - Server 66 có sẵn kết nối SSH Key (passwordless) sang `aptra` và `googleqa` hay không?
     - Hay phải dùng lệnh `scp` / `rsync` có kèm mật khẩu (qua `sshpass`)?
     - Hay tool từ máy Windows Client (PyQt6) sẽ đóng vai trò trung gian SFTP?
   - **Khuyến nghị giải pháp:**
     - **Đối với dữ liệu nặng (Các file vài trăm MB đến GB: `01.Full/*.zip`, `00.OEM_APFE*.zip`, `00.Internal/*Results`):**
       Truyền **trực tiếp giữa Server 66 và APTRA / GOOGLEQA** qua mạng nội bộ 10.x của datacenter. Tool `xTS_Tool` phát lệnh shell qua SSH Paramiko sang Server 66 để thực thi lệnh `curl` với giao thức SFTP (đã test thực tế chạy ổn định 100%, không cần cài `sshpass` hay cấu hình SSH Key):
       - Upload sang GOOGLEQA:
         `curl -s -k -u "googleqa:googleqa" -T <file> sftp://loghub.lge.com/home/googleqa/GOOGLEQA/Official_Test_results/{Project}/{Version}/`
       - Copy sang APTRA:
         `curl -s -k -u "aptra:aptra" -T <file> sftp://loghub.lge.com/home/aptra/APTRA/{Project}/{Version}/`
       *Ưu điểm:* Tận dụng băng thông gigabit nội bộ giữa 2 máy chủ Linux, chỉ mất vài chục giây cho hàng trăm MB dữ liệu, không làm nghẽn mạng máy trạm Windows.

---

## 3. Môi Trường Xử Lý File Excel (`03.*.xlsx` và `Summary.xlsx`)

1. **Xử lý Excel chạy trên máy Client (Windows) hay trên Server 66 (Linux)? Có thể download trực tiếp về Local được không?**
   - **Ý kiến User:** "Tôi nghĩ download về local các file excel này để xử lý cho dễ. Nhưng nếu download trực tiếp từ server GOOGLEQA về máy local được thì download luôn, tránh download 2 lần. Bạn hãy check lại phần này cho tôi, recommend nên như nào, download trực tiếp được không?"
   - **Khuyến nghị & Kết quả kiểm tra:**
     - **HOÀN TOÀN ĐƯỢC VÀ ĐÂY LÀ PHƯƠNG ÁN TỐI ƯU NHẤT!**
     - **Lý do:**
       1. Máy trạm Windows kết nối SFTP trực tiếp đến cả 3 server (`10.218.158.66`, `aptra@loghub.lge.com`, `googleqa@loghub.lge.com`) cực kỳ nhanh chóng và độc lập.
       2. Toàn bộ các file `.xlsx` kết quả từng bài test từ APTRA và file Summary mẫu từ GOOGLEQA có dung lượng rất nhẹ (chỉ từ 50KB - 80KB mỗi file, tổng cộng 8 file chỉ khoảng 600KB). Việc tải trực tiếp về Windows qua SFTP chỉ mất 1-2 giây.
       3. **Luồng xử lý tối ưu:**
          - `xTS_Tool` tải trực tiếp `*Result.xlsx` từ server APTRA về thư mục tạm trên Windows (`temp_report/`).
          - `xTS_Tool` tải trực tiếp file Summary mẫu từ server GOOGLEQA về `temp_report/`.
          - Xử lý toàn bộ logic bằng `openpyxl` ngay trên máy Local (đổi tên `03.`, điền metadata, unmerge, xóa rows 15-40, trích xuất số liệu D3:J3, tạo bảng fail).
          - Xử lý xong, `xTS_Tool` upload trực tiếp các file `03.*.xlsx` và file Summary hoàn chỉnh lên thư mục phát hành trên GOOGLEQA.
       4. **Lợi ích:** Tránh hoàn toàn việc tải trung chuyển qua Server 66 (không bị tải 2 lần), không phụ thuộc vào Python/openpyxl của Server 66, tốc độ chạy tức thì và người dùng có thể mở xem trước file Excel ngay trên máy mình trước khi phát hành.

---

## 4. Nguồn Dữ Liệu `01.Full/` & Mối Quan Hệ Với `report_collector.py` Hiện Tại

1. **Nguồn gốc dữ liệu trong thư mục `Report_tmp/01.Full/`:**
   - **Trả lời (User):** Folder `01.Full` sẽ do kỹ sư chuẩn bị trước chứa kết quả các folder các bài test xTS, phần này sẽ được nhập Path trên giao diện trước khi bấm Run.
2. **Kịch bản làm sạch thư mục tạm `Report_tmp`:**
   - **Trả lời (User):** Thư mục này do kỹ sư chuẩn bị và điền path trước khi chạy, đảm bảo dữ liệu sạch.

---

## 5. Danh Sách Đầy Đủ Các Test Suite & Quy Tắc Ánh Xạ Tên File

1. **Quy tắc ánh xạ tên file chính xác từ APTRA sang `03.`:**
   - `AtsInteractiveResults.xlsx` ➔ `03.LGE_{Model}_{ModelCode}_AtsInteractive_Result_Final_{SW}.xlsx`
   - `AtsMultideviceResults.xlsx` ➔ `03.LGE_{Model}_{ModelCode}_AtsMultidevice_Result_Final_{SW}.xlsx`
   - `ATSResult.xlsx` ➔ `03.LGE_{Model}_{ModelCode}_ATS_Result_Final_{SW}.xlsx`
   - `BFGResult.xlsx` ➔ `03.LGE_{Model}_{ModelCode}_BFG_Result_Final_{SW}.xlsx`
   - `CTSonGSIResult.xlsx` ➔ `03.LGE_{Model}_{ModelCode}_CTSonGSI_Result_Final_{SW}.xlsx`
   - `CTSResult.xlsx` ➔ `03.LGE_{Model}_{ModelCode}_CTS_Result_Final_{SW}.xlsx`
   - `STSResult.xlsx` ➔ `03.LGE_{Model}_{ModelCode}_STS_Result_Final_{SW}.xlsx`
   - `VTSResult.xlsx` ➔ `03.LGE_{Model}_{ModelCode}_VTS_Result_Final_{SW}.xlsx` *(Lưu ý: dòng 71 tài liệu cũ có typo ghi nhầm STS, trên server thực tế là VTS)*.
   - **Bộ test `CTS_Verifier`:** APTRA không sinh file cho bộ test này. Tool sẽ tự động trích xuất trực tiếp số liệu (`Pass=50, Total=50, Done=1`) từ file XML:
     `/home/lge/GoogleQA/Report_tmp/01.Full/01.CTS_Verifier/*/test_result.xml` (thẻ `<Summary pass="50" failed="0" modules_done="1" modules_total="1" />`) để điền vào dòng `CTS-Verifier` của bảng Summary.
2. **Xử lý khi chạy một phần bài test (Partial Test Run):**
   - **Trả lời (User):** Sẽ để trống các dòng (pass, fail, total module,...) của các bài test không chạy, và quy trình vẫn tiếp tục xử lý bình thường, không báo lỗi.

---

## 6. Logic Cập Nhật Bảng Summary & Xử Lý Sheet Lỗi (Fail Lists)

1. **Tiêu chí tự động nhận diện block của version trước trong sheet `Summary`:**
   - **Khuyến nghị thuật toán:**
     1. Quét từ dòng cuối cùng (`ws.max_row`) ngược lên đầu trang tại cột C để tìm ô có giá trị bằng `"Summary"`. Đây là dòng kết thúc của block cuối cùng (`last_block_end`).
     2. Từ `last_block_end`, quét ngược lên trên tại cột B để tìm ô `"HW (PCB) version"`. Đây là dòng bắt đầu của block cuối cùng (`last_block_start`).
     3. Vị trí đặt block mới sẽ là `last_block_end + 3` (đúng chuẩn cách 2 dòng trống).
     4. *Ưu điểm:* Thuật toán này tự động thích ứng với mọi độ dài khối bảng (dù 10 bài test, 12 bài test hay 15 dòng) và không bao giờ bị lệch dòng.
2. **Quy tắc làm sạch dữ liệu cũ trong 2 sheet `Nissan Fail Module List` và `Nissan Fail TestCase List`:**
   - **Trả lời (User):** Đúng, phải xóa sạch toàn bộ data cũ từ dòng 3 trở đi trước khi ghi dữ liệu lỗi mới vào. Bảng tiêu đề ở dòng 2 và viền khung vẫn được giữ nguyên vẹn (ngay cả khi version này không có lỗi nào).

---

## 7. Cấu Hình & Tự Động Hóa Template Mẫu (Previous Summary Template)

1. **Đường dẫn file Summary mẫu của version trước:**
   - **Khuyến nghị giải pháp:**
     - Thiết kế ô nhập đường dẫn (được lưu nhớ trong `config.json`).
     - Kèm theo nút **"🔍 Tự Động Tìm Bản Gần Nhất"**:
       - Khi bấm nút này, Tool sẽ tự động kết nối SSH vào GOOGLEQA `/home/googleqa/GOOGLEQA/Official_Test_results/{Model}/`, liệt kê các thư mục version và tìm file `*Summary*.xlsx` của version có thời gian cập nhật gần nhất để tự động điền vào ô.
       - Kỹ sư vẫn có thể tự gõ hoặc bấm nút "Browse" để chọn file khác theo ý muốn.

---

## 8. Thiết Kế Giao Diện (UI/UX) Tích Hợp Vào `xTS_Tool`

1. **Vị trí hiển thị trên giao diện:**
   - **Trả lời (User):** Chọn **Lựa chọn 1**: Thêm sub-tab thứ 3 vào `ServerTab`: **"📑 Tạo Báo Cáo Chứng Chỉ (Generate Report)"**.
   - Phù hợp với luồng 3 bước trong `ServerTab`:
     1. `⚙️ Quy Trình Pre-Setup (xTS Flash & Setup)`
     2. `📊 Thu Thập & Tổ Chức Báo Cáo (Collect & Report)`
     3. `📑 Tạo Báo Cáo Chứng Chỉ (Generate Report)`
2. **Chế độ chạy (Execution Mode):**
   - **Trả lời (User):** Cần cả 2 chế độ:
     - **"🚀 Chạy Toàn Bộ (Run All)":** Tự động thực hiện tuần tự toàn bộ quy trình từ đầu đến cuối (có dừng ở Pop-up APTRA để chờ user xác nhận).
     - **"🛠️ Chạy Từng Bước (Step-by-Step)":** Cho phép kỹ sư chọn chạy riêng rẽ từng bước (ví dụ: chỉ chạy bước tải file, chỉ chạy bước format Excel, hoặc chỉ chạy bước upload lên GOOGLEQA) để phục vụ debug nhanh khi cần.

---

## 9. Quy Tắc Tên File và Mã Model Rút Gọn

1. **Mã Model trong tên file `03.` và file Summary:**
   - Trên giao diện UI sẽ có ô: `Model Code` (mặc định gợi ý `PZ1D`).
   - Tên file `03.` sẽ được sinh ra: `03.LGE_Nissan_AIVI_Full_12.3_{Model_Code}_{Suite}_Result_Final_{SW}.xlsx`.
   - Tên file Summary chính thức: `Nissan_{Model_Code}_Google Certification Summary_{Short_SW}.xlsx`.
   - Trong đó `{Short_SW}` là phần phiên bản phần mềm sau dấu chấm đầu tiên (ví dụ `YAK.31.03.30` ➔ `31.03.30`).
