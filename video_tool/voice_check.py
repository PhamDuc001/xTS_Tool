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
