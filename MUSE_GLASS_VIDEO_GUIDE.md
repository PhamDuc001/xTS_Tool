# MUSE GUIDE — Video dọc tiếng Việt kiểu Glassmorphism (glass-studio)

> **Dành cho AI agent (Muse) trong một session mới.** Đọc hết file này trước khi làm.
> Mục tiêu: khi người dùng đưa **một kịch bản**, bạn dựng được video MP4 dọc 9:16 tiếng Việt,
> chất lượng giống hệt video mẫu `rent_vs_buy` ("Thuê nhà cả đời hay vay mua nhà?", 1:44, 1080×1920, 30fps).
> File này chứa **toàn bộ mã nguồn** — bạn có thể dựng lại pipeline từ con số 0.

---

## 0. Quy tắc làm việc bắt buộc (của người dùng)

1. **Lập kế hoạch → chờ người dùng đồng ý rõ ràng ("ok", "đồng ý", "tiến hành") → mới thực hiện.**
   Không tự tạo/sửa/xóa file, không cài đặt, không chạy lệnh làm thay đổi hệ thống khi chưa được duyệt.
   Lệnh chỉ đọc (xem file, `ffprobe`, `hyperframes check/snapshot`) thì được.
2. Không tự `git commit` / `git push`.
3. Trả lời ngắn gọn bằng **tiếng Việt**. Báo tiến độ ngắn ở mỗi giai đoạn.
4. Làm ngoài phạm vi kế hoạch đã duyệt → dừng lại xin phép.
5. Máy là **Windows + PowerShell 5.1**: dùng `;` thay `&&`, đường dẫn dùng `\`.
6. **Giọng đọc là chữ ký của series — làm đúng mục 6.5, `voice_check.py` phải PASS trước khi render.**

---

## 1. Sản phẩm cuối cùng trông như thế nào

| Thành phần | Đặc tả |
|---|---|
| Khung hình | 1080×1920 (9:16), 30 fps, H.264 + AAC, ~40–50 MB cho ~1:45 |
| Nền | Gradient tối (xanh navy → tím), 3 quầng sáng mờ trôi chậm, 2 lớp sao trôi lên + nhấp nháy |
| Thẻ | Kính mờ (glassmorphism): bo 40px, viền trắng mờ, `backdrop-filter: blur`, tông blue/red/green có glow |
| Chữ | Font **Be Vietnam Pro** (render bằng code → dấu tiếng Việt đúng 100%) |
| Số liệu | Số rất lớn (168px), đếm tăng dần đúng lúc giọng đọc nói số đó |
| Chuyển động | pop (bật ra), slide (trượt vào), pulse (nhịp), shake (rung khi gây sốc) — **đúng từng từ** của lời đọc |
| Giọng | Edge TTS `vi-VN-NamMinhNeural`, tốc độ `+15%` (nhanh, dồn dập) |
| Phụ đề | Karaoke ở y=1500: chữ trắng 60px viền đen, **từ khóa chuyển xanh #4da3ff đúng lúc đọc**, dòng ~24 ký tự, vào bằng hard cut, dòng đầu mỗi cảnh pop |
| SFX | pop / ding / click / whoosh / impact, tự tổng hợp bằng numpy (không bản quyền), đặt đúng mốc cue |
| Nhạc | **Không có nhạc** (người dùng chọn chỉ SFX) |
| Chú thích | Dòng nhỏ cố định ở y=1820: giả định + "Không phải lời khuyên tài chính." |

Cấu trúc nội dung chuẩn (7 cảnh): **hook gây sốc → bối cảnh số liệu → phe A → cú sốc → phe B → bẫy ("Nhưng khoan!") → poll "Gõ 1 / Gõ 2" + lưu/theo dõi + teaser tập sau**.

---

## 2. Công nghệ & lý do chọn

| Công cụ | Vai trò | Ghi chú |
|---|---|---|
| **HyperFrames 0.8.43** (npm `hyperframes`) | Render HTML+GSAP → MP4, tự trộn các thẻ `<audio>` | Timeline GSAP `paused:true`, đăng ký `window.__timelines[id]` |
| **GSAP 3** (npm `gsap`) | Animation | Chỉ dùng tween/`set` seek-safe, KHÔNG dùng `onUpdate` |
| **edge-tts 7.x** (pip) | Giọng Việt miễn phí + **WordBoundary** (thời điểm từng từ) | Không cần Whisper. Lời đọc gửi lên server Microsoft |
| numpy, soundfile (pip) | Tạo SFX | |
| ffmpeg / ffprobe | Đo thời lượng audio | phải có trong PATH |
| Be Vietnam Pro (Google Fonts, OFL) | Font | 6 độ đậm: Regular, Medium, SemiBold, Bold, ExtraBold, Black |
| Node ≥ 20, Python ≥ 3.10 | | Trên máy này Node v26, dùng `npm.cmd` |

Vì sao không dùng AI video: chữ tiếng Việt bị sai dấu, số liệu không chính xác, không sync từng từ. Render bằng code thì sắc nét như vector và đúng 100%.

---

## 3. Cấu trúc thư mục

```
D:\Learning\video\glass-studio\
  package.json
  node_modules\              (hyperframes, gsap)
  template\
    index.html               khung HTML, build.py thay {{...}}
    engine.js                thư viện window.G (design system + motion)
    styles.css               CSS design system
  tools\
    sfx.py                   tạo assets\sfx\*.wav
    markup.py                parse cú pháp **từ khóa** và {cue:sfx}
    tts.py                   Edge TTS → vo\<scene>.mp3 + .json (word timings)
    build.py                 căn thời gian → timeline.js + index.html + lib\
    voice_check.py           đo giọng (F0/cv/tốc độ) — PHẢI PASS trước khi render (mục 6.5)
    make_vo.ps1              (chạy trên Windows người dùng) tts → voice_check → renders\<slug>_vo.zip (mục 6.6)
  assets\
    fonts\BeVietnamPro-*.ttf
    sfx\*.wav
  videos\<slug>\
    script.json              ← BẠN VIẾT (lời đọc + marker)
    scenes.js                ← BẠN VIẾT (hình ảnh từng cảnh)
    vo\  timeline.js  index.html  lib\  snapshots\   ← sinh tự động, KHÔNG sửa tay
  renders\<slug>.mp4
```

Python venv dùng chung: `D:\Learning\video\manim-studio\.venv\Scripts\python.exe`
(nếu dựng máy mới, tạo venv riêng — xem mục 4).

---

## 4. Setup từ đầu (chỉ làm khi chưa có — nhớ xin phép trước)

```powershell
# 4.1 thư mục
$R='D:\Learning\video\glass-studio'
New-Item -ItemType Directory -Force "$R\template","$R\tools","$R\assets\fonts","$R\assets\sfx","$R\videos","$R\renders" | Out-Null

# 4.2 Node packages
cd $R
'{"name":"glass-studio","private":true,"version":"0.1.0","type":"module","dependencies":{}}' | Out-File -Encoding ascii package.json
npm.cmd install hyperframes@0.8.43 gsap

# 4.3 Python (nếu chưa có venv)
python -m venv "$R\.venv"
& "$R\.venv\Scripts\python.exe" -m pip install edge-tts numpy soundfile

# 4.4 Font Be Vietnam Pro (proxy công ty → cần --ssl-no-revoke)
foreach ($w in 'Regular','Medium','SemiBold','Bold','ExtraBold','Black') {
  curl.exe --ssl-no-revoke -L -o "$R\assets\fonts\BeVietnamPro-$w.ttf" "https://github.com/google/fonts/raw/main/ofl/bevietnampro/BeVietnamPro-$w.ttf"
}

# 4.5 kiểm tra
ffprobe -version | Select-Object -First 1
node "$R\node_modules\hyperframes\dist\cli.js" doctor
```

Sau đó tạo 7 file mã nguồn ở **mục 11** (copy nguyên văn), rồi chạy `tools\sfx.py` một lần.

---

## 5. Quy trình làm một video từ kịch bản người dùng đưa

### Bước A — Phân tích kịch bản (chưa ghi file)
1. Đếm từ: **~3,3 từ/giây** ở `+15%` → 340 từ ≈ 1:44 (video mẫu), 400 từ ≈ 2:00, 480 từ ≈ 2:25.
   Thêm ~0,45 s nghỉ giữa các cảnh + 0,4 s đầu + 1,2 s cuối.
2. Chia thành **6–8 cảnh**, mỗi cảnh 7–20 giây, mỗi cảnh = 1 ý = 1 bố cục màn hình.
3. Kiểm tra số liệu: tự tính lại bằng Python nếu kịch bản có phép tính. Số trên màn hình phải khớp số được đọc.
4. Với mỗi cảnh, liệt kê: **số/chữ nào xuất hiện trên màn hình, ở từ nào trong lời đọc, kèm SFX gì**.

### Bước B — Trình bày kế hoạch cho người dùng
Gồm: slug, bảng cảnh (id, thời lượng ước tính, nội dung hình), danh sách file sẽ tạo
(`videos\<slug>\script.json`, `videos\<slug>\scenes.js`), các lệnh sẽ chạy (mục 7). **Chờ duyệt.**

### Bước C — Viết `script.json` (mục 6) → chạy `tts.py` → `build.py`
Build in ra tổng thời lượng + số cue. Nếu thời lượng lệch nhiều so với yêu cầu → báo người dùng.

### Bước D — Viết `scenes.js` (mục 8, 9) → `build.py` lại → `check` → `snapshot` → xem ảnh → sửa
Lặp tới khi đạt checklist mục 10.

### Bước E — Render (≈ 8 phút cho 1:44 với 2 worker) → `ffprobe` xác nhận → dọn thư mục tạm → báo kết quả.

---

## 6. Viết `script.json`

```json
{
 "title": "Thuê nhà cả đời hay vay mua nhà?",
 "voice": "vi-VN-NamMinhNeural",
 "rate": "+15%",
 "width": 1080,
 "height": 1920,
 "scenes": [
  { "id": "hook", "text": "... gần {n20:pop}**20 năm lương** mới mua nổi ..." },
  { "id": "poll", "gap": 0.2, "text": "..." }
 ]
}
```

Trường tùy chọn: `pitch` (mặc định `+0Hz`), `tail` (giây im lặng cuối, mặc định 1.2), mỗi scene có `gap` (mặc định 0.45).

### 6.1 Cú pháp marker trong `text`
| Cú pháp | Tác dụng |
|---|---|
| `**từ khóa**` | Trong phụ đề karaoke, các từ này chuyển **xanh dương + phóng 1.06** đúng lúc được đọc. TTS đọc bình thường. |
| `{ten}` | Mốc thời gian tên `scene.ten` = **thời điểm bắt đầu của từ ngay sau marker**. Dùng trong scenes.js: `G.t("hook.ten")`. Nếu marker ở cuối cảnh → = thời điểm kết thúc lời cảnh. |
| `{ten:sfx}` | Như trên + phát SFX (`pop`, `ding`, `click`, `whoosh`, `impact`) sớm 0,03 s trước mốc. |

Quy tắc:
- Tên cue chỉ gồm chữ/số/gạch dưới (`\w+`), duy nhất trong cảnh.
- **Đặt marker ngay trước từ mà hình cần xuất hiện**. Ví dụ muốn số 5,25 hiện khi đọc "5 tỷ": `{p3:ding}vẫn là **5 tỷ 250 triệu**` (marker đặt sớm 2 từ để thẻ kịp bật trước khi đọc số).
- Dấu câu ngay sau `**...**` được tự gộp vào từ trước.
- Mỗi cảnh 3–5 cue. Toàn video ~30 SFX (video mẫu: 31) — dày nhưng không liên tục.

### 6.2 Chọn SFX
| SFX | Dùng khi | Âm lượng |
|---|---|---|
| `pop` | Thẻ/số liệu bật ra (phổ biến nhất) | 0.45 |
| `ding` | Con số "chốt" quan trọng, kết quả tích cực, CTA | 0.35 |
| `click` | Chip nhỏ, đổi số trong dashboard, nguồn trích dẫn | 0.40 |
| `whoosh` | Chuyển ý, slide vào, "Nhưng khoan!" | 0.35 |
| `impact` | Cú sốc, số âm/đỏ, cảnh báo | 0.50 |

### 6.3 Viết lời cho TTS đọc đúng
- Viết số **theo cách muốn nghe**: "**5 tỷ 250 triệu**" (đừng viết "5,25 tỷ" nếu muốn nghe "năm tỷ hai trăm năm mươi triệu"). Edge đọc đúng "11,5%", "3,2%", "70%", "2026".
- "Q2/2026" → viết "quý hai năm 2026". "m²" → "mét vuông". "tr" → "triệu".
- Câu ngắn, nhịp nhanh, nhiều câu hỏi tu từ; xưng "bạn"/"mình".
- Màn hình được phép dùng dạng gọn (5,25 tỷ; 123 tr/m²) dù lời đọc dài.
- Giọng của series là **cố định** — xem mục 6.5. Không tự đổi giọng/tốc độ.

### 6.5 GIỌNG ĐỌC BẮT BUỘC (chữ ký âm thanh của series — KHÔNG được thay đổi)

> Lý do có mục này: một bản tập 2 do agent khác dựng nghe "đều đều, phẳng" khác hẳn tập 1. Đo ra: F0 p10 = 134 Hz, f0_cv = 0,146
> (giọng chuẩn: p10 ≈ 110, cv ≈ 0,20) và dài hơn ~15%. Đổi `rate` **không** làm thay đổi cao độ, nên giọng phẳng nghĩa là
> **đã dùng engine/giọng khác hoặc đã hậu xử lý audio**. Người xem nhận ra ngay → phải giữ đúng 100% cách làm dưới đây.

**Chỉ được tạo giọng bằng đúng một cách:**
1. `tools\tts.py` **nguyên văn** (mục 11.5) — thư viện Python `edge-tts`, gọi `edge_tts.Communicate(text, "vi-VN-NamMinhNeural", rate="+15%")`.
2. `script.json`: `"voice": "vi-VN-NamMinhNeural"`, `"rate": "+15%"`, **không có** khóa `pitch`/`volume`.
3. **Mỗi cảnh = 1 lần gọi TTS cho cả đoạn lời** (tts.py đã làm vậy). KHÔNG tách từng câu thành nhiều file rồi ghép
   — làm vậy mất ngữ điệu xuống giọng cuối đoạn và tạo khoảng lặng đều đặn kiểu robot.
4. Dùng nguyên file `vo\<scene>.mp3` mà Edge trả về. KHÔNG normalize, compress, EQ, đổi pitch, đổi tốc độ (atempo),
   cắt khoảng lặng, thêm reverb. `build.py` chỉ đặt audio lên timeline (lead-in 0,4 s, gap 0,45 s giữa cảnh, tail 1,2 s).

**CẤM tuyệt đối:** `hyperframes tts`, Kokoro, Piper, gTTS, `vi-VN-HoaiMyNeural`, giọng MAI/FPT/ElevenLabs, Azure SSML
`<prosody pitch=…>`, hay bất kỳ engine nào khác — kể cả khi Edge lỗi mạng. Nếu Edge lỗi thì **thử lại / chờ**, không đổi engine.

**Chữ ký chuẩn (đo từ tập 1 `rent_vs_buy`):**

| Chỉ số | Chuẩn | Ngưỡng PASS |
|---|---|---|
| F0 trung vị | ~151 Hz | 138–165 |
| F0 p10 | ~110 Hz | 100–126 |
| F0 p90 | ~190 Hz | 180–205 |
| f0_cv (std/median) | ~0,20 | 0,16–0,26 |
| Tốc độ (chỉ token chữ, bỏ token chứa số và nghỉ > 0,6 s) | ~4,5–4,8 từ/giây | 4,2–5,3 |

> Không đo tốc độ bằng "tổng từ / tổng thời gian": Edge gộp "190", "Ngày 2 tháng 3 năm 2026"… thành 1 token dù đọc nhiều âm tiết,
> kịch bản nhiều số sẽ bị báo chậm sai (tập 2 từng ra 2,86 dù đúng +15%). Ước thời lượng ở Bước A vẫn dùng ~3,3 từ/giây theo số từ viết.

**Kiểm tra bắt buộc** sau `tts.py`, trước khi viết scenes/render: `& $py voice_check.py <slug>` → phải in `VOICE CHECK: PASS`
(exit code 0). Sau khi render có thể kiểm lại file MP4: `& $py voice_check.py ..\renders\<slug>.mp4`. FAIL → xóa `vo\`,
kiểm lại script.json + tts.py nguyên văn, chạy lại tts.py. Không bao giờ nới ngưỡng để cho qua.

**Lỗi Edge thường gặp:**
- `NoAudioReceived`: dịch vụ chập chờn / bị giới hạn khi gọi dồn dập → tts.py đã retry; nếu vẫn lỗi, chờ 30–60 s rồi chạy lại
  (cache theo hash nên chỉ cảnh lỗi bị tổng hợp lại). Không dùng `rate="+0%"`/`"+1%"` (từng gây NoAudioReceived).
- Video dài hơn/ngắn hơn mục tiêu → **sửa số từ trong lời đọc** (~200 từ/phút), KHÔNG đổi `rate`.

### 6.6 Khi máy agent KHÔNG truy cập được Edge TTS (proxy/sandbox chặn `speech.platform.bing.com`)

Dấu hiệu: `ClientConnectorSSLError`, HTTP 400/403 từ proxy, lỗi giống hệt nhau mọi lần thử. Đây **không** phải Edge chập chờn
→ đừng retry mãi, **không đổi engine**. Giọng chuẩn sẽ do máy Windows của người dùng tạo theo quy trình sau:

1. Agent viết xong `videos\<slug>\script.json` (đã chốt lời) → gửi **nguyên văn file** cho người dùng, dừng chờ.
   Không sửa lời đọc sau bước này: `tts.py` cache theo hash của *lời đọc thuần* (voice|rate|pitch|text sau khi bỏ marker),
   lệch 1 ký tự lời đọc → hash khác → tts.py sẽ đòi tổng hợp lại (và lại lỗi mạng).
   Đổi/thêm marker `{cue:sfx}` hoặc `**từ khóa**` thì **không** sao (không ảnh hưởng hash).
2. Người dùng chạy trên Windows:
   ```powershell
   powershell -ExecutionPolicy Bypass -File D:\Learning\video\glass-studio\tools\make_vo.ps1 <slug> -Script <đường dẫn script.json nhận từ agent>
   ```
   Script chép script.json → **kiểm tra trước** (Python ≥ 3.10 có edge-tts + numpy — tự tìm `glass-studio\.venv`, venv manim-studio,
   `py -3`, `python`; ffmpeg trên PATH; script.json: JSON UTF-8, voice/rate/pitch đúng, id cảnh không dấu & không trùng,
   `**` chẵn, marker `{ten}`/`{ten:sfx}` đúng cú pháp) → chạy `tts.py` (tự thử lại 3 lần, cách 45 s) → `voice_check.py` (phải PASS) →
   nén `vo\` thành `renders\<slug>_vo.zip` (mỗi cảnh 1 `.mp3` + 1 `.json`).
3. Người dùng gửi zip cho agent → agent giải nén vào `videos\<slug>\vo\` (ghi đè), chạy `tts.py <slug>` — phải in
   `cached` cho **mọi** cảnh (nếu có cảnh `tts` = script.json lệch → báo người dùng, không tự xử lý) →
   `voice_check.py <slug>` PASS → `build.py` → snapshot → render như bình thường.

Bản giọng thay thế cũ (nếu có) không được dùng để render; chỉ giữ tạm làm backup rồi xóa sau khi bản mới PASS.

### 6.4 Video mẫu hoàn chỉnh — `videos\rent_vs_buy\script.json`
```json
{
 "title": "Thuê nhà cả đời hay vay mua nhà?",
 "voice": "vi-VN-NamMinhNeural",
 "rate": "+15%",
 "width": 1080,
 "height": 1920,
 "scenes": [
  {
   "id": "hook",
   "text": "{chip:whoosh}Hai vợ chồng trẻ ở Hà Nội, không ăn không tiêu, phải mất gần {n20:pop}**20 năm lương** mới mua nổi một căn chung cư. {vs:whoosh}Vậy nên **thuê cả đời**, {buy:pop}hay **cắn răng vay mua**? Hôm nay mình tính {go:click}bằng **con số thật**."
  },
  {
   "id": "price",
   "text": "Theo {src:click}**Bộ Xây dựng**, quý hai năm 2026, chung cư Hà Nội trung bình {p1:pop}**123 triệu** một mét vuông. Nhà thứ cấp rẻ hơn, khoảng {p2:pop}**75 triệu**. Một căn 70 mét vuông {p3:ding}vẫn là **5 tỷ 250 triệu**. Trong khi người làm công ở thành thị {p4:pop}chỉ nhận khoảng **11 triệu** một tháng."
  },
  {
   "id": "buy",
   "text": "Nếu vay 70%, bạn cần {b1:pop}**1 tỷ 575 triệu** trả trước. Để dành 15 triệu mỗi tháng, {b2:click}mất **gần 9 năm**. Phần vay {b3:click}**3 tỷ 675 triệu**, trả trong 25 năm. Năm đầu lãi ưu đãi 9%, {b4:ding}trả khoảng **31 triệu** mỗi tháng. Hết ưu đãi, lãi thả nổi 11,5%, trả góp {b5:impact}nhảy lên **37 triệu**."
  },
  {
   "id": "shock",
   "text": "Cộng lại sau 25 năm, {s1:whoosh}bạn trả ngân hàng **hơn 11 tỷ**. Riêng {s2:impact}**tiền lãi** là **7 tỷ 400 triệu**, {s3:pop}nhiều hơn cả **giá căn nhà**."
  },
  {
   "id": "rent",
   "text": "Còn thuê thì sao? Căn tương tự {r1:pop}khoảng **14 triệu** một tháng, mỗi năm {r2:pop}chỉ bằng **3,2%** giá nhà. Nếu thuê, rồi đem {r3:click}1 tỷ rưỡi ban đầu cộng phần chênh lệch mỗi tháng đi gửi lãi 6%, {r4:ding}25 năm sau bạn có khoảng **18 tỷ**."
  },
  {
   "id": "trap",
   "text": "{t0:whoosh}Nhưng khoan! Mua chỉ lời hơn thuê khi nhà tăng giá {t1:pop}**trên 5%** mỗi năm. Mà 5 năm qua, chung cư mới ở Hà Nội {t2:pop}tăng tới **25%** một năm. Phe thuê chỉ thắng {t3:click}nếu bạn **cực kỳ kỷ luật**. Và cái bẫy lớn nhất: {t4:impact}**37 triệu** trả góp còn cao hơn **lương hai người** cộng lại."
  },
  {
   "id": "poll",
   "gap": 0.2,
   "text": "Bạn chọn bên nào? {q1:pop}Gõ **1** nếu thuê và đầu tư. {q2:pop}Gõ **2** nếu quyết vay mua. {q3:ding}Lưu video lại để tính khi cần, và theo dõi kênh. {q4:whoosh}Tập sau: **gửi tiết kiệm hay mua vàng?**"
  }
 ]
}
```
Kết quả build: `1:43.9, 7 scenes, 31 cues, 31 sfx, 63 lines`.

---

## 7. Lệnh chạy (PowerShell, copy nguyên văn, thay `<slug>`)

```powershell
# --- âm thanh + timeline ---
cd D:\Learning\video\glass-studio\tools
$env:PYTHONIOENCODING='utf-8'
$py='D:\Learning\video\manim-studio\.venv\Scripts\python.exe'
& $py sfx.py                     # chỉ cần 1 lần (assets\sfx đã có thì bỏ qua)
& $py tts.py <slug>              # cache theo hash: chỉ cảnh đổi lời mới tổng hợp lại
& $py voice_check.py <slug>      # BẮT BUỘC PASS (mục 6.5) — FAIL thì dừng, không làm tiếp
& $py build.py <slug>            # BẮT BUỘC chạy lại sau MỌI lần sửa scenes.js / script.json / template

# --- kiểm tra ---
cd D:\Learning\video\glass-studio\videos\<slug>
$cli='D:\Learning\video\glass-studio\node_modules\hyperframes\dist\cli.js'
$ErrorActionPreference='Continue'     # stderr của node không làm PS 5.1 dừng
node $cli lint
node $cli check 2>&1 | ForEach-Object { "$_" } | Select-String -NotMatch 'INFO|browserGpu|At line|CategoryInfo|FullyQualified|~~~|^\+' | Select-Object -Last 40
Remove-Item snapshots -Recurse -Force -ErrorAction SilentlyContinue
node $cli snapshot --at 3,9.5,22,27.5,33,40,47,52,58,64,72,78,84,91,97,102 --no-end --describe false 2>&1 | ForEach-Object { "$_" } | Select-Object -Last 3
# → xem snapshots\contact-sheet*.jpg bằng tool xem ảnh

# --- render (frame tạm ~25 GB / 100 s → để TEMP ở ổ D) ---
$tmp='D:\Learning\video\glass-studio\.tmp'; New-Item -ItemType Directory -Force $tmp | Out-Null
$env:TEMP=$tmp; $env:TMP=$tmp
New-Item -ItemType Directory -Force ..\..\renders | Out-Null
node $cli render -q high -f 30 -w 2 -o ..\..\renders\<slug>.mp4 2>&1 | ForEach-Object { "$_" } | Select-String -NotMatch '^\s*$|RemoteException|Render:trace' | Select-Object -Last 6

# --- xác nhận + dọn ---
Remove-Item D:\Learning\video\glass-studio\.tmp -Recurse -Force
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate -show_entries format=duration -of compact D:\Learning\video\glass-studio\renders\<slug>.mp4
```

Ghi chú:
- Chọn mốc `--at` sao cho rơi vào **cuối mỗi cảnh** (lúc mọi thẻ đã hiện) và vài mốc giữa cảnh. Lấy mốc từ `timeline.js` (`scenes.<id>.start/end`).
- Render là lệnh chạy lâu: chạy sync với `initial_wait` 600–900 s; nếu chưa xong thì chờ thông báo, đừng chạy lại.
- Trước render kiểm tra dung lượng: `Get-PSDrive C,D | Select Name,@{n='FreeGB';e={[math]::Round($_.Free/1GB,1)}}`. Cần ~0,25 GB/giây video.
- RAM máy còn ít (~3 GB trống) → giữ `-w 2`.

---

## 8. Design system & bố cục 9:16

### 8.1 Lưới dọc (tọa độ là **tâm** phần tử, px)
```
y   0 ┬───────────────────────────────┐
      │   (vùng an toàn trên ~220)     │
  300 │  KICKER  +  TITLE (header)     │  G.text(S, 540, 300, ...)
  450 │                                │
      │   VÙNG NỘI DUNG  y 450 → 1380  │  thẻ, số, bar
      │   2 cột: cx 290 | cx 790, w440 │
      │   1 cột: cx 540, w ≤ 960       │
 1380 │                                │
 1500 │  PHỤ ĐỀ KARAOKE (60px)         │  G.subtitles({y:1500})
 1820 │  chú thích nhỏ (24px)          │
 1920 ┴───────────────────────────────┘
```
- Không đặt nội dung dưới 1420 (đè phụ đề) hay trên 220 (đè UI nền tảng).
- Header luôn ở y=300 (hook có thể thay bằng chip ở y=300).
- Khoảng cách dọc giữa các thẻ ~40–60 px. Tính: `cy_next = cy + h/2 + gap + h_next/2`.

### 8.2 Màu & tông
| Tông | Hex | Ý nghĩa |
|---|---|---|
| blue | `#4da3ff` | trung tính/chủ đạo, từ khóa karaoke |
| green | `#3be38f` | phe tích cực, kết quả tốt, lựa chọn 1 |
| red | `#ff5a6a` | rủi ro, chi phí, cú sốc, lựa chọn 2 |
| yellow | `#ffc857` | nhấn phụ (thời gian, lãi gửi) |
| cyan | `#5eead4` | kicker |
| icon trung tính | `#7fd4ff` | |

### 8.3 Class chữ
`kicker` (30px, in hoa, cyan) · `title` (76px/900) · `label` (34px, mờ) · `body` (40px/700) · `note` (24px) ·
`big` (168px/900, số chính) · `mid` (96px, số phụ) · `unit` (0.42em, đơn vị cạnh số) · `grad` (chữ gradient trắng→xanh nhạt) ·
`c-blue c-red c-green c-yellow c-cyan c-muted`.

### 8.4 Ngôn ngữ chuyển động (nhịp chuẩn)
- **Thẻ số**: `G.pop(card, t(cue) - 0.1)` rồi `G.count(node, 0, value, t(cue), 0.7–1.0, dec)` → thẻ bật ra trước 0,1 s, số đếm lúc đọc.
- **Hai lựa chọn đối lập**: `slide(left)` cho bên trái, `slide(right)` cho bên phải, chữ "VS" `pop` với `from:2`.
- **Dashboard tái sử dụng** (bằng chứng "cùng một thẻ chỉ thay số"): 1 thẻ to, dùng `G.swap` đổi nhãn + `G.count` từ số cũ sang số mới, `G.pulse` mỗi lần đổi.
- **Cú sốc**: số đỏ + `G.shake` + SFX `impact`; đổi tông thẻ sang đỏ: `tl.set(card.box, {className:"box glass red"}, t)`.
- **So sánh tỉ lệ**: `G.bar(...)` + `.grow(t, frac)`.
- **Chip (pill)**: `G.card(S, cx, cy, 0, 0, "pill", html)` — w=0 → tự co theo nội dung, không xuống dòng.
- **Header**: `slide("down", {dist:60})` ở đầu cảnh.
- Mỗi cảnh tự mờ đi 0,32 s trước cảnh sau (`G.scene`), không cần tự viết transition.

### 8.5 Mẫu bố cục theo loại cảnh
| Loại | Bố cục |
|---|---|
| **hook** | chip bối cảnh (y300) → thẻ số khổng lồ đếm tăng (y640, 760×400, blue) → 2 thẻ đối lập (y1130, cx290/790, 400×330, green/red) + "VS" |
| **bối cảnh số liệu** | header → chip nguồn (y500) → 2 thẻ nhỏ (y760) → thẻ tổng lớn (y1080, 960×260, blue) → thanh ngang cảnh báo (y1310, 960×130, red) |
| **phe A (dashboard)** | header → 1 thẻ 960×620 ở y820, đổi số 4–5 lần → chip cảnh báo (y1260) |
| **cú sốc** | header → thẻ tổng (y640) → thẻ đỏ (y1000) + shake → 2 bar so sánh (y1240, y1360) |
| **phe B** | header → 2 thẻ nhỏ (y680) → thẻ ngang kế hoạch (y980) → thẻ kết quả green (y1240) |
| **bẫy** | header "Nhưng khoan!" + shake → 2 thẻ số (y660) → chip (y930) → thẻ cảnh báo đỏ "A > B" (y1200) |
| **poll** | header → nút "1" green (y640, 900×230) slide trái → nút "2" red (y920) slide phải → chip lưu/theo dõi (y1140) → thẻ "Tập sau" (y1320) |

---

## 9. API `window.G` (engine.js) — tra cứu nhanh

| Hàm | Mô tả |
|---|---|
| `G.setup()` | Khởi tạo, trả về `tl` (GSAP timeline paused). Có `G.W, G.H, G.CX(=540), G.root, G.TL` |
| `G.t("scene.cue")` | Thời điểm cue (giây). Sai tên → throw lỗi rõ ràng |
| `G.sc(id)` | `{start, end, next}` của cảnh |
| `G.scene(id)` | Tạo container cảnh: hiện ở `start`, mờ trước `next` |
| `G.card(parent,cx,cy,w,h,tone,html)` | Thẻ kính. `h=0` → cao tự động. `w=0` → rộng theo nội dung (chip). tone: `"" blue red green pill "pill red"`... |
| `G.text(parent,cx,cy,cls,html,w=960)` | Khối chữ căn giữa |
| `G.place(parent,cx,cy,cls,html,style)` | Phần tử tùy ý. Trả về anchor; `.box` là phần tử nội dung |
| `G.pop(a,t,{from,d,ease})` | Bật ra (scale 0.6→1, back.out) |
| `G.slide(a,t,dir,{dist,d})` | dir: left/right/up/down |
| `G.fade(a,t,d)` / `G.show(a,t)` / `G.out(a,t,d)` | Hiện mờ / hiện ngay / ẩn |
| `G.pulse(a,t,scale)` / `G.shake(a,t)` | Nhịp / rung |
| `G.num(id,unit,cls="big grad")` | HTML số + đơn vị, span số có `id` |
| `G.count(node,from,to,t,d,dec)` | Đếm tăng (định dạng VN: `5,25`, `1.575`) |
| `G.swap(node,html,t)` | Đổi nội dung tại t |
| `G.$(sel)` | querySelector trong root |
| `G.fmt(v,dec)` | Định dạng số kiểu Việt |
| `G.bar(parent,cx,cy,w,color,label,value)` | Thanh; `.grow(t,frac,d)` |
| `G.icon(name,size,color)` | SVG: house key bank warn clock wallet chart chat bell piggy |
| `G.background({seed})` | Nền sao + quầng sáng |
| `G.subtitles({y,kwColor})` | Phụ đề karaoke (gọi sau cùng, trước finish) |
| `G.finish()` | Kết thúc timeline đúng `duration`, đăng ký `__timelines` |

Khung `scenes.js`:
```js
(function () {
  const tl = G.setup();
  const t = G.t, sc = G.sc;
  G.background({ seed: 31 });
  // ... từng cảnh trong block { } riêng ...
  G.subtitles({ y: 1500 });
  G.finish();
})();
```
Thêm icon mới: thêm path SVG (viewBox 24×24, stroke) vào object `P` trong engine.js.

---

## 10. Checklist QA (xem contact sheet trước khi render)

- [ ] `check`: **Runtime 0 lỗi**. (Cảnh báo `text_not_painted` trên phần tử `.grad` là báo nhầm — bỏ qua nếu ảnh chụp thấy chữ.)
- [ ] Mọi khung có nền sao + nội dung (nếu chỉ thấy nền → có lỗi JS, xem `check`).
- [ ] Chữ tiếng Việt đủ dấu, không bị cắt, chip không xuống dòng từng chữ.
- [ ] Không thẻ nào đè lên nhau / đè vùng phụ đề y≥1420.
- [ ] Số trên màn hình khớp lời đọc (5,25 tỷ ↔ "5 tỷ 250 triệu").
- [ ] Phụ đề: từ khóa xanh, dòng không tràn ngang.
- [ ] Cuối mỗi cảnh, mọi thẻ đã hiện đủ (chụp ở `scenes.<id>.end - 0.3`).
- [ ] Sau render: `ffprobe` thấy h264 1080×1920 30/1 + aac, thời lượng = `TL.duration`.

---

## 11. TOÀN BỘ MÃ NGUỒN (copy nguyên văn)

### 11.1 `template\index.html`
```html
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>{{TITLE}}</title>
  <link rel="stylesheet" href="lib/styles.css">
  <script src="lib/gsap.min.js"></script>
  <script src="lib/engine.js"></script>
  <script src="timeline.js"></script>
</head>
<body>
  <div id="root" data-composition-id="glass" data-start="0" data-width="{{W}}" data-height="{{H}}" data-duration="{{DURATION}}" style="width:{{W}}px;height:{{H}}px">
{{AUDIO}}
  <script>
{{SCENES}}
  </script>
  <script>
    window.__timelines = window.__timelines || {};
    window.__timelines["glass"] = G.tl;
  </script>
  </div>
</body>
</html>
```

### 11.2 `template\styles.css`
```css
/* glass-studio design system: dark gradient + stars, glassmorphism cards, big counters, karaoke subs */
@font-face { font-family: "BVP"; src: url("fonts/BeVietnamPro-Regular.ttf"); font-weight: 400; font-display: block; }
@font-face { font-family: "BVP"; src: url("fonts/BeVietnamPro-Medium.ttf"); font-weight: 500; font-display: block; }
@font-face { font-family: "BVP"; src: url("fonts/BeVietnamPro-SemiBold.ttf"); font-weight: 600; font-display: block; }
@font-face { font-family: "BVP"; src: url("fonts/BeVietnamPro-Bold.ttf"); font-weight: 700; font-display: block; }
@font-face { font-family: "BVP"; src: url("fonts/BeVietnamPro-ExtraBold.ttf"); font-weight: 800; font-display: block; }
@font-face { font-family: "BVP"; src: url("fonts/BeVietnamPro-Black.ttf"); font-weight: 900; font-display: block; }

:root {
  --blue: #4da3ff; --cyan: #5eead4; --red: #ff5a6a; --green: #3be38f; --yellow: #ffc857; --violet: #a78bfa;
  --text: #ffffff; --muted: rgba(255, 255, 255, .66);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: #05060f; }
#root {
  position: relative; overflow: hidden; color: var(--text);
  font-family: "BVP", "Segoe UI", sans-serif; -webkit-font-smoothing: antialiased;
  background:
    radial-gradient(1200px 900px at 15% 10%, #1b2a6b 0%, rgba(27, 42, 107, 0) 60%),
    radial-gradient(1000px 1000px at 90% 85%, #3a1563 0%, rgba(58, 21, 99, 0) 60%),
    linear-gradient(170deg, #070a1c 0%, #0b1030 45%, #12082a 100%);
}

/* ---------- background ---------- */
.bg-layer { position: absolute; left: 0; top: 0; width: 100%; height: 115%; pointer-events: none; }
.star { position: absolute; border-radius: 50%; background: #fff; }
.star.glow { box-shadow: 0 0 6px 2px rgba(160, 200, 255, .8); }
.orb { position: absolute; border-radius: 50%; pointer-events: none; }

/* ---------- layout primitives ---------- */
.scene { position: absolute; inset: 0; }
.anchor { position: absolute; width: 0; height: 0; }
.anchor > .box { position: absolute; left: 0; top: 0; transform: translate(-50%, -50%); }

/* ---------- glass ---------- */
.glass {
  border-radius: 40px;
  background: linear-gradient(140deg, rgba(255, 255, 255, .16) 0%, rgba(255, 255, 255, .05) 55%, rgba(255, 255, 255, .08) 100%);
  border: 1.5px solid rgba(255, 255, 255, .24);
  backdrop-filter: blur(22px) saturate(160%);
  -webkit-backdrop-filter: blur(22px) saturate(160%);
  box-shadow: 0 30px 80px rgba(0, 0, 0, .45), inset 0 1.5px 0 rgba(255, 255, 255, .35);
  display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
  padding: 28px 36px;
}
.glass.red   { border-color: rgba(255, 90, 106, .7);  box-shadow: 0 30px 80px rgba(0,0,0,.45), 0 0 60px rgba(255, 90, 106, .35), inset 0 1.5px 0 rgba(255,255,255,.3); background: linear-gradient(140deg, rgba(255, 90, 106, .22), rgba(255, 90, 106, .06)); }
.glass.green { border-color: rgba(59, 227, 143, .65); box-shadow: 0 30px 80px rgba(0,0,0,.45), 0 0 60px rgba(59, 227, 143, .3),  inset 0 1.5px 0 rgba(255,255,255,.3); background: linear-gradient(140deg, rgba(59, 227, 143, .2), rgba(59, 227, 143, .05)); }
.glass.blue  { border-color: rgba(77, 163, 255, .7);  box-shadow: 0 30px 80px rgba(0,0,0,.45), 0 0 60px rgba(77, 163, 255, .3),  inset 0 1.5px 0 rgba(255,255,255,.3); background: linear-gradient(140deg, rgba(77, 163, 255, .2), rgba(77, 163, 255, .05)); }
.glass.pill  { border-radius: 999px; padding: 18px 40px; flex-direction: row; gap: 16px; }

/* ---------- type ---------- */
.kicker { font-size: 30px; font-weight: 700; letter-spacing: .18em; text-transform: uppercase; color: var(--cyan); }
.title  { font-size: 76px; font-weight: 900; line-height: 1.08; letter-spacing: -.01em; }
.label  { font-size: 34px; font-weight: 600; color: var(--muted); line-height: 1.25; }
.body   { font-size: 40px; font-weight: 700; line-height: 1.25; }
.note   { font-size: 24px; font-weight: 500; color: rgba(255, 255, 255, .5); line-height: 1.35; }
.big    { font-size: 168px; font-weight: 900; line-height: 1; letter-spacing: -.03em; white-space: nowrap; }
.mid    { font-size: 96px;  font-weight: 900; line-height: 1; letter-spacing: -.02em; white-space: nowrap; }
.unit   { font-size: .42em; font-weight: 800; letter-spacing: 0; margin-left: .12em; }
.grad   { background: linear-gradient(180deg, #ffffff 0%, #b9d8ff 100%); -webkit-background-clip: text; background-clip: text; color: transparent; }
.c-blue { color: var(--blue); } .c-red { color: var(--red); } .c-green { color: var(--green); }
.c-yellow { color: var(--yellow); } .c-cyan { color: var(--cyan); } .c-muted { color: var(--muted); }
.icon svg { width: 100%; height: 100%; }

/* ---------- bars ---------- */
.bar-track { height: 46px; border-radius: 23px; background: rgba(255, 255, 255, .08); overflow: hidden; }
.bar-fill { height: 100%; border-radius: 23px; transform-origin: 0 50%; }

/* ---------- karaoke subtitles ---------- */
.subs { position: absolute; left: 0; width: 100%; text-align: center; pointer-events: none; }
.subline {
  position: absolute; left: 0; top: 0; width: 100%; text-align: center; white-space: nowrap;
  font-size: 60px; font-weight: 800; line-height: 1.15; color: #fff;
  text-shadow: 0 4px 0 rgba(0, 0, 0, .55), 0 0 24px rgba(0, 0, 0, .65);
  -webkit-text-stroke: 2px rgba(0, 0, 0, .55); paint-order: stroke fill;
}
.subline .w { display: inline-block; margin: 0 .13em; }
```

### 11.3 `template\engine.js`
```js
/*!
 * glass-studio engine — seek-safe helpers for HyperFrames (GSAP, paused timeline, no onUpdate).
 * Coordinates are frame pixels (1080x1920); every placed element is centred on (cx, cy).
 * Times are seconds; use G.t("scene.cue") for word-synced cue times from timeline.js.
 */
(function () {
  "use strict";
  const G = (window.G = {});
  let tl, root, TL;

  // ---------------------------------------------------------------- core
  G.setup = function () {
    TL = G.TL = window.TL;
    root = G.root = document.querySelector('[data-composition-id="glass"]') || document.getElementById("root");
    tl = G.tl = gsap.timeline({ paused: true });
    G.W = TL.width; G.H = TL.height; G.CX = TL.width / 2;
    return tl;
  };
  G.t = function (key) {
    if (!(key in TL.cues)) throw new Error("unknown cue " + key + " (check {cue} markers in script.json)");
    return TL.cues[key];
  };
  G.sc = (id) => TL.scenes[id];

  G.div = function (cls, parent, html, style) {
    const d = document.createElement("div");
    if (cls) d.className = cls;
    if (html != null) d.innerHTML = html;
    if (style) Object.assign(d.style, style);
    (parent || root).appendChild(d);
    return d;
  };

  /** Scene container: visible from scene start, fades out just before the next scene. */
  G.scene = function (id) {
    const s = TL.scenes[id];
    const el = G.div("scene", root);
    gsap.set(el, { opacity: 0 });
    tl.set(el, { opacity: 1 }, s.start - 0.05);
    tl.to(el, { opacity: 0, duration: 0.3, ease: "power1.in" }, Math.max(s.start, s.next - 0.32));
    return el;
  };

  /** Anchor at (cx, cy) holding a centred box; animate the anchor (x/y/scale/opacity), style the box. */
  G.place = function (parent, cx, cy, cls, html, style) {
    const a = G.div("anchor", parent, null, { left: cx + "px", top: cy + "px" });
    const box = G.div("box " + (cls || ""), a, html, style);
    a.box = box;
    gsap.set(a, { opacity: 0 });
    return a;
  };
  G.card = (parent, cx, cy, w, h, tone, html) =>
    G.place(parent, cx, cy, "glass " + (tone || ""), html,
      w ? { width: w + "px", height: h ? h + "px" : "auto" } : { width: "max-content", whiteSpace: "nowrap" });
  G.text = (parent, cx, cy, cls, html, w) =>
    G.place(parent, cx, cy, cls, html, { width: (w || 960) + "px", textAlign: "center" });

  // ---------------------------------------------------------------- motion vocabulary
  G.pop = function (a, t, o) {
    o = o || {};
    gsap.set(a, { opacity: 0, scale: o.from || 0.6 });
    tl.to(a, { opacity: 1, scale: 1, duration: o.d || 0.42, ease: o.ease || "back.out(2.2)" }, t);
    return a;
  };
  G.slide = function (a, t, dir, o) {
    o = o || {};
    const dist = o.dist || 220;
    const v = { left: { x: -dist }, right: { x: dist }, up: { y: dist }, down: { y: -dist } }[dir || "up"];
    gsap.set(a, Object.assign({ opacity: 0 }, v));
    tl.to(a, { opacity: 1, x: 0, y: 0, duration: o.d || 0.5, ease: "power3.out" }, t);
    return a;
  };
  G.fade = function (a, t, d) {
    gsap.set(a, { opacity: 0 });
    tl.to(a, { opacity: 1, duration: d || 0.35 }, t);
    return a;
  };
  G.show = function (a, t) { gsap.set(a, { opacity: 0 }); tl.set(a, { opacity: 1 }, t); return a; };
  G.out = function (a, t, d) { tl.to(a, { opacity: 0, scale: 0.92, duration: d || 0.25, ease: "power1.in" }, t); return a; };
  G.pulse = function (a, t, s) {
    tl.to(a, { scale: s || 1.08, duration: 0.12, ease: "power2.out" }, t)
      .to(a, { scale: 1, duration: 0.25, ease: "power2.inOut" }, t + 0.12);
    return a;
  };
  G.shake = function (a, t) {
    [-14, 12, -8, 5, 0].forEach((x, i) => tl.to(a, { x, duration: 0.05, ease: "none" }, t + i * 0.05));
    return a;
  };

  // ---------------------------------------------------------------- numbers
  /** Vietnamese number format: decimal comma, thousands dot. */
  G.fmt = function (v, dec) {
    const s = Math.abs(v).toFixed(dec || 0).split(".");
    s[0] = s[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return (v < 0 ? "-" : "") + s.join(",");
  };
  /** Discrete count-up on a text node (seek-safe: many tl.set steps). */
  G.count = function (node, from, to, t, d, dec) {
    d = d || 1.2;
    const steps = Math.max(2, Math.round(d * 30));
    gsap.set(node, { textContent: G.fmt(from, dec) });
    for (let i = 1; i <= steps; i++) {
      const u = i / steps, e = 1 - Math.pow(1 - u, 3);
      tl.set(node, { textContent: G.fmt(from + (to - from) * e, dec) }, t + d * u);
    }
    return t + d;
  };
  G.swap = function (node, html, t) { tl.set(node, { innerHTML: html }, t); return node; };
  /** <span class=num> + unit, returns {html, sel} helper. */
  G.num = (id, unit, cls) => `<span class="${cls || "big grad"}"><span id="${id}">0</span>${unit ? `<span class="unit">${unit}</span>` : ""}</span>`;
  G.$ = (sel) => root.querySelector(sel);

  // ---------------------------------------------------------------- bars
  G.bar = function (parent, cx, cy, w, color, label, value) {
    const a = G.place(parent, cx, cy, "", `
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px">
        <span class="label" style="color:#fff">${label}</span><span class="body" style="color:${color}">${value}</span></div>
      <div class="bar-track"><div class="bar-fill" style="background:${color};box-shadow:0 0 30px ${color}"></div></div>`,
      { width: w + "px" });
    a.fill = a.querySelector(".bar-fill");
    gsap.set(a.fill, { scaleX: 0 });
    a.grow = (t, frac, d) => { tl.to(a.fill, { scaleX: frac, duration: d || 0.9, ease: "power3.out" }, t); return a; };
    return a;
  };

  // ---------------------------------------------------------------- icons (inline SVG, stroke = currentColor)
  const P = {
    house: '<path d="M3 11 12 3l9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9"/><path d="m17 6 3 3"/><path d="m15 8 2 2"/>',
    bank: '<path d="M3 10 12 4l9 6"/><path d="M5 10v8M9 10v8M15 10v8M19 10v8"/><path d="M3 20h18"/>',
    warn: '<path d="M12 3 2 20h20L12 3z"/><path d="M12 10v4"/><circle cx="12" cy="17" r=".6" fill="currentColor"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    wallet: '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M16 12h5v4h-5a2 2 0 0 1 0-4z"/><path d="M3 9h15"/>',
    chart: '<path d="M4 20V4"/><path d="M4 20h16"/><path d="m7 15 4-4 3 3 5-6"/>',
    chat: '<path d="M4 5h16v11H9l-5 4z"/>',
    bell: '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    piggy: '<path d="M5 11a7 6 0 0 1 13-2h2v4l-2 1v3h-3v-2H9v2H6v-3a6 6 0 0 1-1-3z"/><circle cx="15" cy="10" r=".7" fill="currentColor"/>',
  };
  G.icon = (name, size, color) =>
    `<span class="icon" style="display:inline-block;width:${size || 64}px;height:${size || 64}px;color:${color || "#fff"}">` +
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${P[name]}</svg></span>`;

  // ---------------------------------------------------------------- background
  function rng(seed) { return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  G.background = function (o) {
    o = o || {};
    const D = TL.duration, r = rng(o.seed || 42);
    const orbs = [["#2b5cff", 900, 200, 380], ["#8b3dff", 800, 880, 1500], ["#00c2ff", 600, 940, 520]];
    orbs.forEach(([c, s, x, y], i) => {
      const orb = G.div("orb", root, null, { width: s + "px", height: s + "px", left: x - s / 2 + "px", top: y - s / 2 + "px",
        background: `radial-gradient(circle, ${c}55 0%, ${c}00 65%)` });
      const cyc = 9 + i * 3;
      tl.to(orb, { x: i % 2 ? -120 : 140, y: i % 2 ? 90 : -110, duration: cyc, ease: "sine.inOut", yoyo: true, repeat: Math.ceil(D / cyc) }, 0);
    });
    [[150, 0.35, 140, 1.3], [70, 0.7, 260, 2.4]].forEach(([n, op, drift, maxS], li) => {
      const layer = G.div("bg-layer", root);
      for (let i = 0; i < n; i++) {
        const s = 0.8 + r() * maxS;
        const st = G.div("star" + (r() < 0.18 ? " glow" : ""), layer, null, {
          width: s + "px", height: s + "px", left: r() * G.W + "px", top: r() * G.H * 1.15 + "px", opacity: op * (0.4 + r() * 0.6) });
        if (r() < 0.35) {
          const d = 1.2 + r() * 2.2;
          tl.to(st, { opacity: 0.08, duration: d, yoyo: true, repeat: Math.ceil(D / d), ease: "sine.inOut" }, r() * 2);
        }
      }
      tl.fromTo(layer, { y: 0 }, { y: -drift * (D / 60), duration: D, ease: "none" }, 0);
      if (li === 1) gsap.set(layer, { zIndex: 1 });
    });
  };

  // ---------------------------------------------------------------- karaoke subtitles
  G.subtitles = function (o) {
    o = o || {};
    const box = G.div("subs", root, null, { top: (o.y || 1500) + "px", zIndex: 50 });
    const kwColor = o.kwColor || "#4da3ff";
    TL.lines.forEach((ln) => {
      const el = G.div("subline", box);
      el.innerHTML = ln.words.map((w) => `<span class="w">${w.text.replace(/&/g, "&amp;").replace(/</g, "&lt;")}</span>`).join("");
      gsap.set(el, { opacity: 0 });
      if (ln.first) {
        gsap.set(el, { scale: 0.85 });
        tl.to(el, { opacity: 1, scale: 1, duration: 0.16, ease: "back.out(2)" }, ln.start);
      } else {
        tl.set(el, { opacity: 1 }, ln.start);
      }
      tl.set(el, { opacity: 0 }, ln.end);
      [...el.children].forEach((sp, i) => {
        const w = ln.words[i];
        if (w.kw) tl.set(sp, { color: kwColor, scale: 1.06 }, w.start);
      });
    });
  };

  // ---------------------------------------------------------------- finish
  G.finish = function () {
    tl.set({}, {}, TL.duration);
    window.__timelines = window.__timelines || {};
    window.__timelines["glass"] = tl;
  };
})();
```

### 11.4 `tools\markup.py`
```python
"""Shared parsing of script.json narration markup.

Markup inside scene "text":
  **keyword words**   -> highlighted (blue) in karaoke subtitles when spoken
  {cue}  {cue:sfx}    -> named time anchor = start of the next spoken word (end of scene if none);
                         optional sfx name from assets/sfx (pop, ding, click, whoosh, impact)
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKUP = re.compile(r"(\*\*|\{\w+(?::\w+)?\})")


def load_script(slug: str) -> tuple[Path, dict]:
    vdir = ROOT / "videos" / slug
    return vdir, json.loads((vdir / "script.json").read_text(encoding="utf-8"))


def parse(text: str) -> tuple[str, list[dict], list[dict]]:
    """Return (plain text for TTS, tokens, trailing cues)."""
    tokens: list[dict] = []
    pending: list[dict] = []
    kw = False
    buf = ""

    def flush():
        nonlocal buf, pending
        for word in buf.split():
            if tokens and not any(ch.isalnum() for ch in word):
                tokens[-1]["text"] += word  # punctuation right after a keyword: "**x**," -> "x,"
                continue
            tokens.append({"text": word, "kw": kw, "cues": pending})
            pending = []
        buf = ""

    for part in MARKUP.split(text):
        if part == "**":
            flush()
            kw = not kw
        elif MARKUP.fullmatch(part):
            flush()
            name, _, sfx = part[1:-1].partition(":")
            pending.append({"id": name, "sfx": sfx or None})
        else:
            buf += part
    flush()
    plain = " ".join(t["text"] for t in tokens)
    return plain, tokens, pending


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    return "".join(ch.lower() for ch in s if ch.isalnum())
```

### 11.5 `tools\tts.py`
```python
"""Narrate every scene of a video with Edge TTS and keep per-word timings.

  python tools/tts.py <slug>

Writes videos/<slug>/vo/<scene>.mp3 and <scene>.json (Edge WordBoundary events).
Cached by text+voice+rate hash; edit a scene's text and only that scene is re-synthesized.
"""
import asyncio
import hashlib
import json
import sys

import edge_tts

from markup import load_script, parse


async def synth(text: str, voice: str, rate: str, pitch: str, mp3) -> list[dict]:
    words: list[dict] = []
    for attempt in range(3):
        try:
            words.clear()
            com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
            with open(mp3, "wb") as f:
                async for ch in com.stream():
                    if ch["type"] == "audio":
                        f.write(ch["data"])
                    elif ch["type"] == "WordBoundary":
                        s = ch["offset"] / 1e7
                        words.append({"text": ch["text"], "start": round(s, 3), "end": round(s + ch["duration"] / 1e7, 3)})
            return words
        except Exception as e:  # network hiccups
            if attempt == 2:
                raise
            print("  retry:", e)
            await asyncio.sleep(2)
    return words


async def main(slug: str) -> None:
    vdir, script = load_script(slug)
    voice = script.get("voice", "vi-VN-NamMinhNeural")
    rate = script.get("rate", "+15%")
    pitch = script.get("pitch", "+0Hz")
    out = vdir / "vo"
    out.mkdir(exist_ok=True)
    for sc in script["scenes"]:
        plain, _, _ = parse(sc["text"])
        h = hashlib.sha1(f"{voice}|{rate}|{pitch}|{plain}".encode()).hexdigest()[:12]
        meta = out / f"{sc['id']}.json"
        if meta.exists() and json.loads(meta.read_text(encoding="utf-8")).get("hash") == h:
            print(f"cached  {sc['id']}")
            continue
        words = await synth(plain, voice, rate, pitch, out / f"{sc['id']}.mp3")
        meta.write_text(json.dumps({"hash": h, "text": plain, "words": words}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
        print(f"tts     {sc['id']}: {len(words)} words, {words[-1]['end'] if words else 0:.1f}s")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1]))
```

### 11.6 `tools\build.py`
```python
"""Assemble timing for a video: scene starts, word times, cues, SFX and karaoke lines.

  python tools/build.py <slug>

Reads  videos/<slug>/script.json + vo/*.json|mp3
Writes videos/<slug>/timeline.js, index.html, lib/ (engine, css, gsap, fonts, sfx)
"""
import difflib
import json
import shutil
import subprocess
import sys

from markup import ROOT, load_script, norm, parse

LEAD_IN = 0.4
TAIL = 1.2
LINE_CHARS = 24          # karaoke line length (vertical 1080 px, 60 px bold)
PUNCT_BREAK = ".,!?:;…"


def duration(path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def align(tokens: list[dict], words: list[dict]) -> None:
    """Give every script token start/end from Edge word boundaries (char-level diff, robust to splits/merges)."""
    a, a_idx = "", []
    for i, t in enumerate(tokens):
        n = norm(t["text"])
        a += n
        a_idx += [i] * len(n)
    b, b_idx = "", []
    for j, w in enumerate(words):
        n = norm(w["text"])
        b += n
        b_idx += [j] * len(n)
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            ti, wj = a_idx[blk.a + k], b_idx[blk.b + k]
            first.setdefault(ti, wj)
            last[ti] = wj
    for i, t in enumerate(tokens):
        if i in first:
            t["start"], t["end"] = words[first[i]]["start"], words[last[i]]["end"]
    # interpolate unmatched tokens between known neighbours
    for i, t in enumerate(tokens):
        if "start" not in t:
            prev = next((tokens[k]["end"] for k in range(i - 1, -1, -1) if "end" in tokens[k]), 0.0)
            nxt = next((tokens[k]["start"] for k in range(i + 1, len(tokens)) if "start" in tokens[k]), prev + 0.3)
            t["start"], t["end"] = prev, max(prev, nxt)


def lines_for(tokens: list[dict], scene_end: float) -> list[dict]:
    lines, cur = [], []
    for t in tokens:
        cur.append(t)
        text = " ".join(x["text"] for x in cur)
        if len(text) >= LINE_CHARS or (t["text"][-1] in PUNCT_BREAK and len(cur) >= 2):
            lines.append(cur)
            cur = []
    if cur:
        if lines and len(" ".join(x["text"] for x in lines[-1] + cur)) <= LINE_CHARS + 6:
            lines[-1] += cur
        else:
            lines.append(cur)
    out = []
    for k, ln in enumerate(lines):
        end = lines[k + 1][0]["start"] if k + 1 < len(lines) else min(ln[-1]["end"] + 0.35, scene_end)
        if end - ln[-1]["end"] > 0.6:
            end = ln[-1]["end"] + 0.35
        out.append({"start": round(ln[0]["start"], 3), "end": round(end, 3), "first": k == 0,
                    "words": [{"text": w["text"], "kw": w["kw"], "start": round(w["start"], 3)} for w in ln]})
    return out


def copy_lib(vdir) -> None:
    lib = vdir / "lib"
    lib.mkdir(exist_ok=True)
    for f in ("engine.js", "styles.css"):
        shutil.copy2(ROOT / "template" / f, lib / f)
    shutil.copy2(ROOT / "node_modules" / "gsap" / "dist" / "gsap.min.js", lib / "gsap.min.js")
    for sub in ("fonts", "sfx"):
        shutil.copytree(ROOT / "assets" / sub, lib / sub, dirs_exist_ok=True)


def main(slug: str) -> None:
    vdir, script = load_script(slug)
    t = LEAD_IN
    scenes, cues, sfx, lines, audio = {}, {}, [], [], []
    order = []
    for sc in script["scenes"]:
        sid = sc["id"]
        meta = json.loads((vdir / "vo" / f"{sid}.json").read_text(encoding="utf-8"))
        _, tokens, trailing = parse(sc["text"])
        align(tokens, meta["words"])
        dur = duration(vdir / "vo" / f"{sid}.mp3")
        start = t
        for tok in tokens:
            tok["start"] += start
            tok["end"] += start
        end = start + dur
        for tok in tokens:
            for c in tok["cues"]:
                cues[f"{sid}.{c['id']}"] = round(tok["start"], 3)
                if c["sfx"]:
                    sfx.append((tok["start"], c["sfx"]))
        for c in trailing:
            cues[f"{sid}.{c['id']}"] = round(end, 3)
            if c["sfx"]:
                sfx.append((end, c["sfx"]))
        lines += lines_for(tokens, end)
        audio.append((f"vo-{sid}", f"vo/{sid}.mp3", start, dur, 1.0))
        scenes[sid] = {"start": round(start, 3), "end": round(end, 3)}
        order.append(sid)
        t = end + sc.get("gap", 0.45)
    total = round(t - script["scenes"][-1].get("gap", 0.45) + script.get("tail", TAIL), 3)
    for i, sid in enumerate(order):
        scenes[sid]["next"] = scenes[order[i + 1]]["start"] if i + 1 < len(order) else total

    vols = {"pop": 0.45, "ding": 0.35, "click": 0.4, "whoosh": 0.35, "impact": 0.5}
    for k, (at, name) in enumerate(sorted(sfx)):
        p = ROOT / "assets" / "sfx" / f"{name}.wav"
        if not p.exists():
            sys.exit(f"unknown sfx '{name}'")
        audio.append((f"sfx-{k}-{name}", f"lib/sfx/{name}.wav", max(0.0, at - 0.03), duration(p), vols.get(name, 0.4)))

    tl = {"duration": total, "width": script.get("width", 1080), "height": script.get("height", 1920),
          "scenes": scenes, "cues": cues, "lines": lines, "data": script.get("data", {})}
    (vdir / "timeline.js").write_text("window.TL = " + json.dumps(tl, ensure_ascii=False, indent=1) + ";\n",
                                      encoding="utf-8")

    tags = "\n".join(
        f'    <audio id="{i}" src="{src}" data-start="{s:.3f}" data-duration="{d:.3f}" '
        f'data-track-index="{20 if i.startswith("vo") else 21}" data-volume="{v}" preload="auto"></audio>'
        for i, src, s, d, v in audio)
    html = (ROOT / "template" / "index.html").read_text(encoding="utf-8")
    html = (html.replace("{{DURATION}}", f"{total:.3f}").replace("{{AUDIO}}", tags)
            .replace("{{W}}", str(tl["width"])).replace("{{H}}", str(tl["height"]))
            .replace("{{TITLE}}", script.get("title", slug))
            .replace("{{SCENES}}", (vdir / "scenes.js").read_text(encoding="utf-8")))
    (vdir / "index.html").write_text(html, encoding="utf-8")
    copy_lib(vdir)
    m, s = divmod(total, 60)
    print(f"built {slug}: {int(m)}:{s:04.1f}, {len(order)} scenes, {len(cues)} cues, {len(sfx)} sfx, {len(lines)} lines")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
```
> Lưu ý: `build.py` đọc `scenes.js` → lần build đầu (khi chưa viết scenes.js) hãy tạo một `scenes.js` tạm
> chứa khung rỗng ở mục 9 để lấy `timeline.js` (thời điểm cue) rồi mới viết hình.

### 11.7 `tools\sfx.py`
```python
"""Synthesize license-free UI sound effects into assets/sfx/*.wav.

  python tools/sfx.py
"""
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100
OUT = Path(__file__).resolve().parents[1] / "assets" / "sfx"
rng = np.random.default_rng(7)


def t(sec: float) -> np.ndarray:
    return np.arange(int(SR * sec)) / SR


def norm(x: np.ndarray, peak_db: float = -3.0) -> np.ndarray:
    fade = min(len(x), int(SR * 0.01))
    x = x.copy()
    x[-fade:] *= np.linspace(1, 0, fade)
    return x / (np.abs(x).max() + 1e-9) * 10 ** (peak_db / 20)


def lowpass(x: np.ndarray, cutoff) -> np.ndarray:
    """One-pole lowpass; cutoff may be an array (time-varying)."""
    cutoff = np.broadcast_to(cutoff, x.shape)
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def pop() -> np.ndarray:
    tt = t(0.12)
    f = 950 * np.exp(-tt * 28) + 260
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 38)
    click = rng.standard_normal(len(tt)) * np.exp(-tt * 900) * 0.4
    return norm(body + click)


def ding() -> np.ndarray:
    tt = t(1.1)
    f0 = 1046.5  # C6, fits F major
    x = sum(a * np.sin(2 * np.pi * f0 * r * tt) * np.exp(-tt * d)
            for r, a, d in [(1, 1.0, 4.0), (2.0, 0.35, 6), (2.76, 0.25, 9), (5.4, 0.1, 14)])
    x *= np.minimum(1, tt / 0.004)
    return norm(x, -4)


def click() -> np.ndarray:
    tt = t(0.035)
    x = rng.standard_normal(len(tt)) * np.exp(-tt * 600)
    x = x - lowpass(x, 2500)  # high-passed tick
    x += 0.5 * np.sin(2 * np.pi * 2200 * tt) * np.exp(-tt * 300)
    return norm(x, -5)


def whoosh() -> np.ndarray:
    tt = t(0.55)
    env = np.sin(np.pi * np.clip(tt / 0.55, 0, 1)) ** 2
    cutoff = 300 + 3500 * env
    x = lowpass(rng.standard_normal(len(tt)), cutoff) * env
    return norm(x, -6)


def impact() -> np.ndarray:
    tt = t(0.7)
    f = 85 * np.exp(-tt * 4) + 38
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 6)
    thump = lowpass(rng.standard_normal(len(tt)), 400) * np.exp(-tt * 30) * 3
    return norm(body + thump, -2)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("pop", pop), ("ding", ding), ("click", click), ("whoosh", whoosh), ("impact", impact)]:
        sf.write(OUT / f"{name}.wav", fn().astype(np.float32), SR, subtype="PCM_16")
        print("wrote", OUT / f"{name}.wav")


if __name__ == "__main__":
    main()
```

### 11.8 Mẫu hoàn chỉnh `videos\rent_vs_buy\scenes.js`
```js
/* 3.1 Thuê nhà cả đời hay vay mua nhà? — 1080x1920 */
(function () {
  const tl = G.setup();
  const t = G.t, sc = G.sc;
  G.background({ seed: 31 });

  // section header (kicker + title) at top of every scene
  function header(S, kicker, title, at) {
    const h = G.text(S, G.CX, 300, "", `<div class="kicker">${kicker}</div><div class="title" style="margin-top:14px">${title}</div>`);
    G.slide(h, at, "down", { dist: 60 });
    return h;
  }

  // ------------------------------------------------------------ HOOK
  {
    const s = sc("hook"), S = G.scene("hook");
    const chip = G.card(S, G.CX, 300, 0, 0, "pill", `${G.icon("house", 44, "#7fd4ff")}<span class="body">Căn hộ 70 m² · Hà Nội</span>`);
    G.slide(chip, t("hook.chip"), "down", { dist: 80 });

    const big = G.card(S, G.CX, 640, 760, 400, "blue",
      `${G.num("n20", "", "big grad")}<div class="title" style="font-size:64px;margin-top:6px">NĂM LƯƠNG</div>
       <div class="label" style="margin-top:10px">2 người · không ăn không tiêu</div>`);
    G.pop(big, t("hook.n20") - 0.1);
    G.count(G.$("#n20"), 0, 20, t("hook.n20"), 1.0);

    const rent = G.card(S, 290, 1130, 400, 330, "green",
      `${G.icon("key", 96, "#3be38f")}<div class="mid" style="margin-top:18px">THUÊ</div><div class="label">cả đời</div>`);
    const buy = G.card(S, 790, 1130, 400, 330, "red",
      `${G.icon("bank", 96, "#ff5a6a")}<div class="mid" style="margin-top:18px">MUA</div><div class="label">vay ngân hàng</div>`);
    const vs = G.text(S, G.CX, 1130, "title grad", "VS", 200);
    G.slide(rent, t("hook.vs"), "left");
    G.slide(buy, t("hook.buy"), "right");
    G.pop(vs, t("hook.buy") + 0.15, { from: 2 });
    G.pulse(big, t("hook.go"), 1.05);
    G.pulse(vs, t("hook.go"), 1.3);
  }

  // ------------------------------------------------------------ PRICE
  {
    const s = sc("price"), S = G.scene("price");
    header(S, "Bước 1 · Giá nhà", "Một căn bao nhiêu tiền?", s.start);

    const src = G.card(S, G.CX, 500, 0, 0, "pill", `${G.icon("bank", 40, "#7fd4ff")}<span class="label" style="color:#fff">Bộ Xây dựng · Q2/2026</span>`);
    G.pop(src, t("price.src"));

    const c1 = G.card(S, 290, 760, 440, 300, "",
      `<div class="label">Sơ cấp</div>${G.num("p1", "tr/m²", "mid grad")}`);
    const c2 = G.card(S, 790, 760, 440, 300, "",
      `<div class="label">Thứ cấp</div>${G.num("p2", "tr/m²", "mid grad")}`);
    G.pop(c1, t("price.p1") - 0.1); G.count(G.$("#p1"), 0, 123, t("price.p1"), 0.8);
    G.pop(c2, t("price.p2") - 0.1); G.count(G.$("#p2"), 0, 75, t("price.p2"), 0.8);

    const total = G.card(S, G.CX, 1080, 960, 260, "blue",
      `<div class="label">70 m² × 75 triệu</div>${G.num("p3", "tỷ", "big grad")}`);
    G.pop(total, t("price.p3") - 0.1); G.count(G.$("#p3"), 0, 5.25, t("price.p3"), 1.0, 2);

    const wage = G.card(S, G.CX, 1310, 960, 130, "red",
      `<div style="display:flex;align-items:center;gap:22px">${G.icon("wallet", 56, "#ff5a6a")}
       <span class="body">Lương thành thị: <span class="c-red">11,1 tr/tháng</span></span></div>`);
    G.slide(wage, t("price.p4"), "up", { dist: 80 });
  }

  // ------------------------------------------------------------ BUY (one reused dashboard card)
  {
    const s = sc("buy"), S = G.scene("buy");
    header(S, "Bước 2 · Phe vay mua", "Vay 70% giá nhà", s.start);

    const dash = G.card(S, G.CX, 820, 960, 620, "blue", `
      <div class="label" id="bk">Tiền trả trước (30%)</div>
      <div class="big grad" style="margin:18px 0"><span id="bv">0</span><span class="unit" id="bu">tỷ</span></div>
      <div style="display:flex;align-items:center;gap:18px">${G.icon("clock", 52, "#7fd4ff")}
        <span class="body" id="bs">Để dành 15 tr/tháng</span></div>`);
    G.pop(dash, t("buy.b1") - 0.15);
    const bv = G.$("#bv"), bk = G.$("#bk"), bu = G.$("#bu"), bs = G.$("#bs");
    G.count(bv, 0, 1.575, t("buy.b1"), 0.9, 3);
    G.swap(bs, `Để dành 15 tr/tháng → <span class="c-yellow">8,75 năm</span>`, t("buy.b2"));
    G.pulse(dash, t("buy.b2"), 1.03);

    G.swap(bk, "Khoản vay · 25 năm", t("buy.b3"));
    G.count(bv, 1.575, 3.675, t("buy.b3"), 0.8, 3);
    G.swap(bs, "Lãi ưu đãi năm đầu: 9%", t("buy.b3"));

    G.swap(bk, "Trả góp mỗi tháng", t("buy.b4"));
    G.swap(bu, "tr", t("buy.b4"));
    G.count(bv, 0, 30.8, t("buy.b4"), 0.8, 1);
    G.pulse(dash, t("buy.b4"), 1.03);

    G.swap(bs, `Lãi thả nổi: <span class="c-red">11,5%</span>`, t("buy.b5") - 0.6);
    G.count(bv, 30.8, 37.2, t("buy.b5"), 0.5, 1);
    tl.set(bv.parentNode, { className: "big", color: "#ff5a6a" }, t("buy.b5"));
    tl.set(dash.box, { className: "box glass red" }, t("buy.b5"));
    G.shake(dash, t("buy.b5"));

    const tag = G.card(S, G.CX, 1260, 0, 0, "pill red", `${G.icon("warn", 44, "#ff5a6a")}<span class="body">+6,4 tr mỗi tháng</span>`);
    G.pop(tag, t("buy.b5") + 0.3);
  }

  // ------------------------------------------------------------ SHOCK
  {
    const s = sc("shock"), S = G.scene("shock");
    header(S, "Cú sốc", "Sau 25 năm trả góp", s.start);

    const tot = G.card(S, G.CX, 640, 960, 340, "",
      `<div class="label">Tổng trả ngân hàng</div>${G.num("s1", "tỷ", "big grad")}`);
    G.pop(tot, t("shock.s1") - 0.1); G.count(G.$("#s1"), 0, 11.09, t("shock.s1"), 1.0, 2);

    const it = G.card(S, G.CX, 1000, 960, 300, "red",
      `<div class="label">Riêng tiền lãi</div><span class="big c-red"><span id="s2">0</span><span class="unit">tỷ</span></span>`);
    G.pop(it, t("shock.s2") - 0.05); G.count(G.$("#s2"), 0, 7.41, t("shock.s2"), 0.8, 2);
    G.shake(it, t("shock.s2") + 0.8);

    const b1 = G.bar(S, G.CX, 1240, 900, "#ff5a6a", "Tiền lãi", "7,41 tỷ");
    const b2 = G.bar(S, G.CX, 1360, 900, "#4da3ff", "Giá căn nhà", "5,25 tỷ");
    G.fade(b1, t("shock.s3") - 0.2); G.fade(b2, t("shock.s3") - 0.2);
    b1.grow(t("shock.s3"), 1); b2.grow(t("shock.s3"), 5.25 / 7.41);
  }

  // ------------------------------------------------------------ RENT
  {
    const s = sc("rent"), S = G.scene("rent");
    header(S, "Bước 3 · Phe thuê", "Thuê rồi đem tiền đi gửi", s.start);

    const r1 = G.card(S, 290, 680, 440, 330, "green",
      `${G.icon("key", 64, "#3be38f")}<div class="label" style="margin-top:8px">Tiền thuê</div>${G.num("r1", "tr", "mid grad")}`);
    const r2 = G.card(S, 790, 680, 440, 330, "",
      `${G.icon("chart", 64, "#7fd4ff")}<div class="label" style="margin-top:8px">/năm so với giá nhà</div>${G.num("r2", "%", "mid grad")}`);
    G.pop(r1, t("rent.r1") - 0.1); G.count(G.$("#r1"), 0, 14, t("rent.r1"), 0.7);
    G.pop(r2, t("rent.r2") - 0.1); G.count(G.$("#r2"), 0, 3.2, t("rent.r2"), 0.7, 1);

    const plan = G.card(S, G.CX, 980, 960, 160, "",
      `<div style="display:flex;align-items:center;gap:22px">${G.icon("piggy", 64, "#ffd166")}
       <span class="body">1,575 tỷ + chênh lệch → gửi <span class="c-yellow">6%/năm</span></span></div>`);
    G.slide(plan, t("rent.r3"), "up", { dist: 80 });

    const res = G.card(S, G.CX, 1240, 960, 280, "green",
      `<div class="label">Sau 25 năm bạn có</div><span class="big c-green"><span id="r4">0</span><span class="unit">tỷ</span></span>`);
    G.pop(res, t("rent.r4") - 0.1); G.count(G.$("#r4"), 0, 18.16, t("rent.r4"), 1.0, 1);
  }

  // ------------------------------------------------------------ TRAP
  {
    const s = sc("trap"), S = G.scene("trap");
    const h = header(S, "Nhưng khoan!", "Cái bẫy ở đâu?", t("trap.t0"));
    G.shake(h, t("trap.t0") + 0.4);

    const be = G.card(S, 290, 660, 440, 300, "",
      `<div class="label">Mua thắng khi nhà tăng</div>${G.num("t1", "%/năm", "mid grad")}`);
    G.pop(be, t("trap.t1") - 0.1); G.count(G.$("#t1"), 0, 5.1, t("trap.t1"), 0.7, 1);
    const real = G.card(S, 790, 660, 440, 300, "blue",
      `<div class="label">Chung cư mới HN 5 năm qua</div><span class="mid c-blue">+<span id="t2">0</span><span class="unit">%/năm</span></span>`);
    G.pop(real, t("trap.t2") - 0.1); G.count(G.$("#t2"), 0, 25, t("trap.t2"), 0.7);

    const disc = G.card(S, G.CX, 930, 0, 0, "pill green", `${G.icon("piggy", 44, "#3be38f")}<span class="body">Thuê chỉ thắng nếu cực kỳ kỷ luật</span>`);
    G.pop(disc, t("trap.t3"));

    const warn = G.card(S, G.CX, 1200, 960, 320, "red", `
      <div style="display:flex;align-items:center;gap:20px">${G.icon("warn", 64, "#ff5a6a")}<span class="body c-red">Trả góp > lương 2 người</span></div>
      <div style="display:flex;align-items:baseline;gap:40px;margin-top:18px">
        <span class="mid c-red">37,2<span class="unit">tr</span></span><span class="mid">&gt;</span><span class="mid grad">22,2<span class="unit">tr</span></span></div>`);
    G.pop(warn, t("trap.t4") - 0.1);
    G.shake(warn, t("trap.t4") + 0.5);
  }

  // ------------------------------------------------------------ POLL
  {
    const s = sc("poll"), S = G.scene("poll");
    header(S, "Bình luận ngay", "Bạn chọn bên nào?", s.start);

    const o1 = G.card(S, G.CX, 640, 900, 230, "green", `
      <div style="display:flex;align-items:center;gap:36px"><span class="big c-green" style="font-size:140px">1</span>
      <div style="text-align:left"><div class="title" style="font-size:60px">Thuê + đầu tư</div><div class="label">gõ 1 vào bình luận</div></div></div>`);
    const o2 = G.card(S, G.CX, 920, 900, 230, "red", `
      <div style="display:flex;align-items:center;gap:36px"><span class="big c-red" style="font-size:140px">2</span>
      <div style="text-align:left"><div class="title" style="font-size:60px">Quyết vay mua</div><div class="label">gõ 2 vào bình luận</div></div></div>`);
    G.slide(o1, t("poll.q1"), "left"); G.pulse(o1, t("poll.q1") + 0.5, 1.05);
    G.slide(o2, t("poll.q2"), "right"); G.pulse(o2, t("poll.q2") + 0.5, 1.05);

    const save = G.card(S, G.CX, 1140, 0, 0, "pill blue", `${G.icon("bell", 44, "#4da3ff")}<span class="body">Lưu video · Theo dõi kênh</span>`);
    G.pop(save, t("poll.q3"));

    const next = G.card(S, G.CX, 1320, 960, 150, "", `<div class="label">Tập sau</div><div class="body">Gửi tiết kiệm hay mua vàng?</div>`);
    G.slide(next, t("poll.q4"), "up", { dist: 80 });
  }

  // assumptions footnote, always visible
  const fn = G.text(G.root, G.CX, 1820, "note",
    "Giả định: lãi thả nổi 11,5%, thuê tăng 4%/năm, gửi 6%/năm. Không phải lời khuyên tài chính.", 960);
  G.fade(fn, 0.3);
  fn.style.zIndex = 40;

  G.subtitles({ y: 1500 });
  G.finish();
})();
```

### 11.9 `tools\voice_check.py` (kiểm tra chữ ký giọng — mục 6.5)
```python
"""Kiểm tra giọng đọc có đúng "chữ ký" chuẩn của series (Edge vi-VN-NamMinhNeural, +15%) hay không.

Dùng:
  python voice_check.py <slug>            # đo videos/<slug>/vo/*.mp3 (giọng sạch, không SFX)  -> dùng TRƯỚC khi render
  python voice_check.py path\to\file.mp4  # đo 1 video đã render (có lẫn SFX nên số hơi lệch)

Chỉ số đo (cùng cách rea-video dùng): F0 trung vị, p10/p90, f0_cv = std/median (độ "lên xuống" của giọng).
Chuẩn đo từ rent_vs_buy: median ~150 Hz, p10 ~110, p90 ~190, cv ~0.20, ~4.6 từ chữ/giây.
Giọng phẳng/đều (cv thấp, p10 cao) = KHÔNG phải NamMinh qua Edge (engine khác, đổi pitch, hoặc đã hậu xử lý).
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np

SR = 16000
ROOT = Path(__file__).resolve().parent.parent
RULES = [  # (tên, hàm lấy giá trị, min, max)
    ("F0 median (Hz)", lambda s: s["med"], 138, 165),
    ("F0 p10 (Hz)", lambda s: s["p10"], 100, 126),
    ("F0 p90 (Hz)", lambda s: s["p90"], 180, 205),
    ("f0_cv", lambda s: s["cv"], 0.16, 0.26),
]


def decode(path):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32)


def f0_track(x):
    fr, hop = 640, 320
    thr = 0.45 * np.sqrt((x ** 2).mean())
    lo, hi = SR // 300, SR // 70
    f = []
    for i in range(0, len(x) - fr, hop):
        s = x[i:i + fr]
        if np.sqrt((s ** 2).mean()) < thr:
            continue
        s = s - s.mean()
        ac = np.correlate(s, s, "full")[fr - 1:]
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.45 * ac[0]:
            f.append(SR / k)
    return np.array(f)


def stats(f):
    med = float(np.median(f))
    return {"med": med, "p10": float(np.percentile(f, 10)), "p90": float(np.percentile(f, 90)), "cv": float(f.std() / med)}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arg = Path(sys.argv[1])
    problems = []
    if arg.suffix.lower() in (".mp4", ".mp3", ".wav", ".m4a"):
        f = f0_track(decode(arg))
        print(f"Nguồn: {arg.name} (video đã render, có lẫn SFX)")
    else:
        vdir = ROOT / "videos" / sys.argv[1]
        script = json.loads((vdir / "script.json").read_text(encoding="utf-8"))
        v, r, p = script.get("voice"), script.get("rate"), script.get("pitch", "+0Hz")
        print(f"script.json: voice={v} rate={r} pitch={p}")
        if v != "vi-VN-NamMinhNeural": problems.append(f"voice phải là vi-VN-NamMinhNeural (đang: {v})")
        if r != "+15%": problems.append(f"rate phải là +15% (đang: {r})")
        if p not in (None, "+0Hz"): problems.append(f"không được đặt pitch (đang: {p})")
        mp3s = sorted((vdir / "vo").glob("*.mp3"))
        if not mp3s:
            sys.exit("Chưa có vo\\*.mp3 — chạy tts.py trước.")
        # Edge gộp số/ngày ("190", "Ngày 2 tháng 3 năm 2026") thành 1 token dù đọc nhiều âm tiết
        # -> chỉ đo trên token chữ (không chứa số), bỏ khoảng nghỉ > 0.6 s.
        words = dur = 0.0
        tracks = []
        for m in mp3s:
            tracks.append(f0_track(decode(m)))
            w = json.loads(m.with_suffix(".json").read_text(encoding="utf-8")).get("words", [])
            for a, b in zip(w, w[1:]):
                step = b["start"] - a["start"]
                if any(c.isdigit() for c in a["text"]) or step > 0.6:
                    continue
                words += 1
                dur += step
        f = np.concatenate(tracks)
        if dur:
            wps = words / dur
            print(f"Tốc độ: {wps:.2f} từ chữ/giây ({int(words)} từ, bỏ token chứa số)")
            if not 4.2 <= wps <= 5.3: problems.append(f"tốc độ {wps:.2f} từ chữ/s ngoài 4.2–5.3 (chuẩn ~4.6)")
        print(f"Nguồn: {len(mp3s)} file vo\\*.mp3")
    if len(f) < 50:
        sys.exit("Không đủ khung có giọng để đo.")
    s = stats(f)
    for name, get, lo, hi in RULES:
        val = get(s)
        ok = lo <= val <= hi
        print(f"  {'OK ' if ok else 'FAIL'} {name:15s} {val:7.3f}   (chuẩn {lo}–{hi})")
        if not ok: problems.append(f"{name} = {val:.3f} ngoài {lo}–{hi}")
    if problems:
        print("\nVOICE CHECK: FAIL — giọng KHÔNG khớp series. Tạo lại bằng tools\\tts.py nguyên bản (mục 6.5):")
        for p in problems: print("  -", p)
        sys.exit(1)
    print("\nVOICE CHECK: PASS")


if __name__ == "__main__":
    main()
```

---

## 12. Lỗi đã gặp & cách xử lý (ĐỌC KỸ)

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Tiếng Việt thành `?` khi chạy Python | PowerShell 5.1 pipe here-string vào `python -` | Luôn ghi script ra file `.py` (UTF-8) và đặt `$env:PYTHONIOENCODING='utf-8'` |
| Snapshot chỉ thấy nền, không có thẻ | Compiler HyperFrames đẩy `<script src>` lên trước `<body>` → `getElementById("root")` = null | scenes.js phải **inline bên trong root div** (build.py thay `{{SCENES}}`); engine tìm root bằng `[data-composition-id="glass"]` |
| `lint`: missing_timeline_registry | lint chỉ quét script inline | Giữ khối `window.__timelines["glass"] = G.tl` inline trong index.html |
| Chip/pill xuống dòng từng chữ ("Căn / hộ / 70") | width auto trong anchor rộng 0 | `G.card(..., 0, 0, "pill", ...)` → engine đặt `width:max-content; white-space:nowrap` |
| `check`: text_not_painted trên số `.grad` | Chữ gradient dùng `background-clip:text` → checker tưởng trong suốt | Báo nhầm. Xác nhận bằng snapshot |
| Render lỗi "Disk capture may need ~25 GB" | Frame tạm ghi vào TEMP ổ C (ít chỗ); `--low-memory-mode` **không** giải quyết | Đặt `$env:TEMP/$env:TMP` sang ổ D cho lệnh render, xóa `.tmp` sau khi xong |
| Số đếm nhảy/sai khi seek | Dùng `onUpdate` | Chỉ dùng `G.count` (nhiều `tl.set` rời rạc) |
| curl lỗi `CRYPT_E_NO_REVOCATION_CHECK` | Proxy công ty | `curl.exe --ssl-no-revoke` |
| PowerShell dừng vì stderr của node | `ErrorActionPreference=Stop` / NativeCommandError | `$ErrorActionPreference='Continue'` + `2>&1 \| ForEach-Object { "$_" }` |
| `unknown cue xxx` trong check | Tên cue trong scenes.js không có trong script.json | Sửa marker, chạy lại tts (nếu đổi lời) + build |
| Video ngắn hơn yêu cầu | +15% đọc rất nhanh (~3,3 từ/s) | Thêm từ (~200 từ/phút). KHÔNG đổi `rate` (mục 6.5) |
| Giọng nghe "đều đều/phẳng", khác tập 1 | Dùng engine/giọng khác, đổi pitch, tách câu, hoặc hậu xử lý audio | Làm đúng mục 6.5; `voice_check.py` phải PASS |
| `ClientConnectorSSLError` / proxy trả 400 khi gọi Edge | Máy agent bị chặn mạng tới Microsoft | Mục 6.6: gửi script.json cho người dùng chạy `make_vo.ps1`, nhận lại zip `vo\` |

---

## 13. Quy trình chuẩn khi người dùng gửi kịch bản mới (tóm tắt cho agent)

1. Đọc kịch bản → đếm từ → ước thời lượng → kiểm tra/tính lại số liệu.
2. Đề xuất: slug, bảng 6–8 cảnh (id · ý chính · bố cục theo mục 8.5 · các cue + SFX), file sẽ tạo, lệnh sẽ chạy. **Chờ duyệt.**
3. Tạo `script.json` (mục 6) + `scenes.js` khung rỗng → `tts.py` → **`voice_check.py` PASS** → `build.py` → đọc `timeline.js` lấy thời lượng thật.
4. Viết `scenes.js` đầy đủ, tận dụng helper `header()` và các mẫu ở mục 11.8.
5. `build.py` → `check` (0 runtime error) → `snapshot` ở cuối mỗi cảnh → xem ảnh → sửa bố cục → lặp.
6. Kiểm tra dung lượng đĩa → render (TEMP ở ổ D, `-q high -f 30 -w 2`) → `ffprobe` → xóa `.tmp`.
7. Báo: đường dẫn MP4, độ phân giải, thời lượng, dung lượng, những gì đã sửa, đề xuất chỉnh (≤100 từ).
8. Cập nhật bảng "Video đã làm" trong `README.md` (nếu được duyệt).

---

## 14. Prompt mẫu để paste vào session Muse mới

```
Bạn là video engineer. Đọc kỹ file D:\Learning\video\glass-studio\MUSE_GLASS_VIDEO_GUIDE.md
(nếu không truy cập được, nội dung guide được dán bên dưới). Tuân thủ mục 0 (lập kế hoạch, chờ tôi duyệt).

Kịch bản video mới:
- Tiêu đề: <...>
- Thời lượng mong muốn: <2 phút>
- Giọng: đúng mục 6.5 (edge-tts vi-VN-NamMinhNeural +15%, tools\tts.py nguyên văn, không hậu xử lý,
  voice_check.py phải PASS trước khi render)
- Nội dung / lời đọc:
<dán kịch bản>

Hãy: (1) kiểm tra số liệu, (2) đề xuất chia cảnh + bố cục + cue/SFX theo guide,
(3) chờ tôi duyệt rồi dựng, QA bằng snapshot và render ra renders\<slug>.mp4.
```
