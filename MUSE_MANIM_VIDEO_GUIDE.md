# Manim Explainer Video Production Guide (for an AI agent)

> **How to use this file:** paste the whole document into a fresh agent session (Muse, Muse Code, or any
> coding agent with a Linux shell). It contains everything needed to set up the toolchain and produce a
> 3Blue1Brown-style programming explainer video with a local AI voiceover that is synchronized with the
> animation — at the same quality as the reference video *"Stack vs Heap & Smart Pointers in C++"*
> (2:04, 1920x1080 @ 60 fps, 8.2 MB, 9 scenes, word-level voice sync).

---

## 0. Instructions to the agent (read first)

You are a **video director + Manim engineer**. Your job is to turn a topic into a finished MP4.

Rules:

1. **Plan before you build.** Before writing code, show the user: the narration script (full text), the
   storyboard table (scene → narration → visuals), target length, and the commands you will run.
   Wait for explicit approval ("ok", "go", "approve") before creating files or installing anything.
2. **Never skip the visual QA loop** (Section 7). Render a low-quality draft first, extract frames,
   *look at them*, fix overlaps/clipping/tiny text, then render the final in high quality.
3. **Narration drives timing.** Every scene is wrapped in `with self.voiceover(...)`; animation is
   synced to words with `<bookmark mark='x'/>` + `self.wait_until_bookmark("x")`.
4. **Only free, local tools** unless the user approves a paid API: Manim Community Edition, Kokoro TTS
   (local ONNX), Whisper (local, CPU) for word timing, TeX Live for math, ffmpeg.
5. Do not delete or overwrite the user's existing files without asking. Do not `git push`.
6. Deliver: the final MP4 path, its duration/resolution/size, the `.srt` subtitle path, and a short
   list of what you checked.

---

## 1. What the toolchain is and why

| Component | Role | Notes |
|---|---|---|
| **Manim Community Edition** (`manim`, v0.19+; reference used 0.22.1) | Renders vector animations to MP4 | Python. `from manim import *`. **Not** ManimGL (`manimlib`) — APIs differ. |
| **manim-voiceover** | Adds narration; scene waits for audio; bookmarks | `VoiceoverScene`, `self.voiceover(text)`, `tracker.duration`, `wait_until_bookmark` |
| **Kokoro TTS via `kokoro-onnx`** | Free, local, natural English voice | 82M-param model, ~330 MB files. Voices: `am_michael` (male, used), `am_adam`, `af_heart`, `af_bella`, `bm_george`, `bf_emma`. English only for good quality (no Vietnamese). |
| **Whisper via `stable-ts`** (`manim-voiceover[transcribe]`) | Transcribes generated audio → word timestamps so bookmarks fire on the exact word | CPU is fine; model `base` (~140 MB). |
| **TeX Live** | `MathTex`/`Tex` (formulas, `\checkmark`, `\neq`) | Not needed for `Text`/`Code`, but recommended. |
| **ffmpeg** | Encoding, frame extraction for QA | Required. |
| **Cairo / Pango** | Manim's renderer + text shaping | System libs on Linux. |

Reference repositories (read when you need API details):

- https://github.com/ManimCommunity/manim — engine + docs: https://docs.manim.community/
- https://github.com/ManimCommunity/manim-voiceover — voiceover plugin (look at `manim_voiceover/services/base.py` and `gtts.py` to understand the `SpeechService` contract)
- https://github.com/adithya-s-k/manim_skill — agent best-practice rules for Manim CE (`skills/manimce-best-practices/rules/*.md`: animations, text, mobjects, colors, scenes). **Clone it and read the relevant rule files before coding.**
- https://github.com/thewh1teagle/kokoro-onnx — Kokoro ONNX runtime; model files in its GitHub release `model-files-v1.0`
- https://github.com/jianfch/stable-ts — Whisper word-timestamp wrapper used by manim-voiceover

---

## 2. Environment setup (Ubuntu / Debian — Muse Secure VM, WSL2, or any Linux)

### 2.1 System packages

```bash
sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-dev build-essential pkg-config git curl \
  ffmpeg \
  libcairo2-dev libpango1.0-dev \
  espeak-ng \
  fonts-dejavu fonts-jetbrains-mono \
  texlive texlive-latex-extra texlive-fonts-extra texlive-science dvisvgm
```

- If `sudo` is not available but you are root, drop `sudo`.
- If `fonts-jetbrains-mono` is missing in the distro, skip it and use `DejaVu Sans Mono` (see 4.3).
- If disk/network is limited, the minimal LaTeX set is `texlive texlive-latex-extra dvisvgm`.

### 2.2 Project + Python virtual environment

```bash
mkdir -p ~/manim-studio && cd ~/manim-studio
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel

# CPU-only torch first (keeps the install ~1 GB smaller than the CUDA build)
pip install torch --index-url https://download.pytorch.org/whl/cpu

pip install manim "manim-voiceover[transcribe]" kokoro-onnx soundfile
```

(`uv` works too: `uv venv .venv && uv pip install ...`.)

### 2.3 Kokoro model files (~330 MB, one-time)

```bash
mkdir -p ~/.cache/kokoro
cd ~/.cache/kokoro
curl -L -o kokoro-v1.0.onnx  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -L -o voices-v1.0.bin   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd ~/manim-studio
```

### 2.4 Reference skill repo

```bash
git clone --depth 1 https://github.com/adithya-s-k/manim_skill ~/manim_skill
```

### 2.5 Verify (all must pass before going further)

```bash
cd ~/manim-studio && source .venv/bin/activate
manim --version                       # Manim Community v0.19+ 
ffmpeg -version | head -1
latex --version | head -1             # only if TeX installed
python -c "import manim_voiceover, kokoro_onnx, stable_whisper, soundfile; print('python deps ok')"
ls -lh ~/.cache/kokoro                # both model files present, ~310 MB + ~27 MB
fc-list | grep -i -E "jetbrains|dejavu sans mono" | head -3
```

Harmless warnings you will see and can ignore:

- `SoX could not be found!` — SoX is only needed for recording your own microphone.
- `FP16 is not supported on CPU; using FP32 instead` — Whisper on CPU.
- `words count mismatch` — from stable-ts alignment; bookmarks still work.
- `Some options were not used: {'shortest': ...}` — ffmpeg muxing note.

### 2.6 If the network is restricted (Muse "Sentinel" egress filter, corporate proxy)

Try in this order and tell the user which fallback you used:

| Blocked download | Fallback |
|---|---|
| Kokoro model files (GitHub releases) | Ask the user to upload the two files into `~/.cache/kokoro/`. Or use `pip install "manim-voiceover[gtts]"` and `GTTSService(lang="en")` (needs Google access, lower quality). Last resort offline: `espeak-ng` via `pyttsx3` (`manim-voiceover[pyttsx3]`, robotic voice). |
| Whisper model (`base`) | Remove `transcription_model="base"`; **do not use bookmarks**. Instead split narration into several short `self.voiceover(...)` blocks (one sentence each) and pace animations with `tracker.duration` (see 5.3). |
| PyTorch index | `pip install torch` from default PyPI (bigger). |
| TeX Live | Replace every `MathTex/Tex` with `Text` (e.g. `"≠"`, `"✓"` need a font that has the glyphs — DejaVu does). |

---

## 3. Files to create

```
~/manim-studio/
├── .venv/
├── kokoro_service.py      # Section 3.1 — local TTS adapter (copy verbatim)
├── <topic>.py             # your scene file (template in 3.2, full reference in Appendix A)
└── media/                 # created by manim: videos/, voiceovers/ (audio cache), Tex/, texts/
```

### 3.1 `kokoro_service.py` (copy verbatim)

```python
"""Local Kokoro TTS service for manim-voiceover (offline, free)."""
import os
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro
from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import (
    PathLike,
    SpeechService,
    initialize_speech_service,
    path_to_string,
)

MODEL_DIR = Path(os.environ.get("KOKORO_DIR", Path.home() / ".cache" / "kokoro"))
MODEL_PATH = MODEL_DIR / "kokoro-v1.0.onnx"
VOICES_PATH = MODEL_DIR / "voices-v1.0.bin"


class KokoroService(SpeechService):
    """Voices: am_michael, am_adam, af_heart, af_bella, bm_george, bf_emma, ..."""

    def __init__(self, voice: str = "am_michael", speed: float = 1.0, lang: str = "en-us", **kwargs):
        initialize_speech_service(self, kwargs)
        self.voice = voice
        self.speed = speed
        self.lang = lang
        self._kokoro = None

    def _engine(self) -> Kokoro:
        if self._kokoro is None:
            self._kokoro = Kokoro(str(MODEL_PATH), str(VOICES_PATH))
        return self._kokoro

    def generate_from_text(self, text: str, cache_dir: PathLike | None = None, path: PathLike | None = None, **kwargs):
        if cache_dir is None:
            cache_dir = self.cache_dir

        input_text = remove_bookmarks(text)
        input_data = {
            "input_text": input_text,
            "service": "kokoro",
            "voice": self.voice,
            "speed": self.speed,
            "lang": self.lang,
        }
        cached = self.get_cached_result(input_data, cache_dir)
        if cached is not None:
            return cached

        audio_path = self.get_audio_basename(input_data) + ".wav" if path is None else path_to_string(path)
        samples, sr = self._engine().create(input_text, voice=self.voice, speed=self.speed, lang=self.lang)
        sf.write(str(Path(cache_dir) / audio_path), samples, sr)

        return {"input_text": text, "input_data": input_data, "original_audio": audio_path}
```

Why it works: manim-voiceover calls `generate_from_text`, caches results in
`media/voiceovers/cache.json` keyed by `input_data`, then (if `transcription_model` is set) runs Whisper on
the audio to produce `word_boundaries`, which is what `wait_until_bookmark` uses. **Audio is cached**:
re-renders after visual-only edits do not regenerate speech; editing a sentence regenerates only that clip.

Quick TTS smoke test (≈5 s):

```bash
python - <<'PY'
from kokoro_onnx import Kokoro; import soundfile as sf, os
d=os.path.expanduser("~/.cache/kokoro")
k=Kokoro(f"{d}/kokoro-v1.0.onnx", f"{d}/voices-v1.0.bin")
s,sr=k.create("Hello, this is a voice test.", voice="am_michael", speed=1.0, lang="en-us")
sf.write("tts_test.wav", s, sr); print("seconds:", len(s)/sr)
PY
```

Expect ~2 s of audio. If you get ~0.5 s or only the first word, the text argument is being split — pass
the whole sentence as one Python string.

### 3.2 Scene template (start every new video from this)

```python
from manim import *
from manim_voiceover import VoiceoverScene

from kokoro_service import KokoroService

MONO = "JetBrains Mono"          # or "DejaVu Sans Mono" if JetBrains is not installed
CODE_POS = UP * 2.1               # code window sits under the header
ACCENT, GOOD, BAD = YELLOW, GREEN_C, RED


def code(src: str, language: str = "cpp") -> Code:
    c = Code(
        code_string=src,
        language=language,
        background="window",
        formatter_style="monokai",
        add_line_numbers=False,
        paragraph_config={"font": MONO},
    )
    # readable size: ~0.42 units per line, capped
    c.scale_to_fit_height(min(2.0, 0.5 + 0.42 * (src.count("\n") + 1)))
    if c.width > 10:
        c.scale_to_fit_width(10)
    return c.move_to(CODE_POS)


class MyVideo(VoiceoverScene):
    def construct(self):
        self.set_speech_service(KokoroService(voice="am_michael", transcription_model="base"))
        self.code_mob = None
        self.intro()
        # self.scene_2() ... one method per storyboard row
        self.recap()

    def show_code(self, src: str):
        new = code(src)
        if self.code_mob is None:
            self.play(FadeIn(new, shift=DOWN * 0.3))
        else:
            self.play(FadeTransform(self.code_mob, new))
        self.code_mob = new

    def intro(self):
        title = Text("Big Title", font_size=72, weight=BOLD)
        sub = Text("subtitle", font_size=40, color=GREY_B).next_to(title, DOWN)
        with self.voiceover(
            "Hook sentence. <bookmark mark='a'/> Second sentence that reveals the main diagram."
        ):
            self.play(Write(title), FadeIn(sub, shift=UP * 0.3))
            self.wait_until_bookmark("a")
            header = Text("Big Title", font_size=34, weight=BOLD).to_edge(UP, buff=0.25)
            self.play(FadeOut(sub), Transform(title, header))
        self.header = title

    def recap(self):
        items = ["Point one", "Point two", "Point three"]
        rows = VGroup(*[
            VGroup(MathTex(r"\checkmark", color=GOOD, font_size=56), Text(t, font_size=34)).arrange(RIGHT, buff=0.35)
            for t in items
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        with self.voiceover(
            "To recap: <bookmark mark='r1'/> one, <bookmark mark='r2'/> two, <bookmark mark='r3'/> and three."
        ):
            leftovers = [m for m in self.mobjects if m is not self.header]
            recap_title = Text("Recap", font_size=34, weight=BOLD).to_edge(UP, buff=0.25)
            self.play(*[FadeOut(m) for m in leftovers], Transform(self.header, recap_title))
            for i, m in enumerate(("r1", "r2", "r3")):
                self.wait_until_bookmark(m)
                self.play(FadeIn(rows[i], shift=RIGHT * 0.4))
        self.wait(1.5)
```

---

## 4. Design system (what made the reference video look good)

### 4.1 Canvas & layout

- Manim frame = **14.22 × 8 units**, origin at center. x ∈ [-7.1, 7.1], y ∈ [-4, 4]. Keep a **0.3-unit safe margin**.
- Persistent **header** (topic name) at top: `font_size=34, weight=BOLD`, `to_edge(UP, buff=0.25)` → y ≈ 3.6.
- **Code window** directly under header, centered, y ≈ 2.1, height ≤ 2.0 units, width ≤ 10.
- **Diagram zone** y ∈ [-3.4, 0.9]. Reference layout used two columns: STACK at x = -4.3 (box 3.2 × 3.7),
  HEAP at x = 3.9 (dashed rounded box 4.6 × 3.7), labels at y = 0.75, captions just below boxes.
- Keep the middle (x ∈ [-2.5, 1.5]) free for arrows between columns.
- Stack-like items: fixed slots, `y = base + slot * 0.72`, height 0.6 → never overlap.

### 4.2 Color semantics (consistent across the whole video)

| Meaning | Color |
|---|---|
| Primary concept A (e.g. stack, thread 1) | `BLUE_C` |
| Primary concept B (e.g. heap, shared data) | `YELLOW` |
| Correct / safe / modern solution | `GREEN_C` |
| Bug / danger / leak / UB | `RED` |
| Inactive / empty / freed | `GREY` |
| Secondary text | `GREY_B` |

Background stays Manim's default near-black. Code uses `formatter_style="monokai"` + `background="window"` (macOS-style dots).

### 4.3 Typography

- Titles: `Text(..., font_size=72, weight=BOLD)`; header 34; body labels 24–34; never below 22 at 1080p.
- Monospace for code/identifiers: `JetBrains Mono` → fallback `DejaVu Sans Mono`. (Windows used `Consolas`; not on Linux.)
- Math & symbols: `MathTex(r"\text{ref count} =")`, `MathTex(r"\checkmark")`, `MathTex(r"\neq")`.
- Numbers that change: `Integer(3)` + `count.animate.set_value(2)`.

### 4.4 Motion vocabulary (use these, keep it calm)

| Purpose | Animation |
|---|---|
| Title in | `Write(title)` + `FadeIn(sub, shift=UP*0.3)` |
| Title → header | `Transform(title, header)` |
| New object appears | `FadeIn(x, shift=DOWN*0.5)` (stack push), `GrowFromCenter(block)` |
| Pointer / relation | `GrowArrow(Arrow(a.get_right(), b.get_left(), buff=0.1))` |
| Remove (pop) | `FadeOut(x, shift=UP*0.5)` |
| Destroyed / freed | `ShrinkToCenter(x)` |
| Emphasis | `Indicate(x, color=...)`, `Circumscribe(x)`, `Flash(x)`, `Wiggle(arrow)` |
| Swap code | `FadeTransform(old_code, new_code)` |
| Forbidden | `Create(Cross(mob, stroke_color=RED, stroke_width=8))` |
| Freed memory ghost | `ReplacementTransform(square, DashedVMobject(Square(...), num_dashes=16))` |
| Lists | `LaggedStart(*[FadeIn(i) for i in items], lag_ratio=0.3)` |
| Cycle | two `CurvedArrow(..., angle=-PI/2)` between nodes |

Clean up at the end of each scene: `self.play(FadeOut(VGroup(...)))` everything except the persistent
header/columns, otherwise objects accumulate and overlap later scenes.

---

## 5. Narration & sync

### 5.1 Script length

- Kokoro `am_michael` at speed 1.0 ≈ **145 words/minute** (+ ~1 s gap per voiceover block).
- 2-minute video ≈ **280–300 words**, 8–10 scenes, 2–4 sentences per scene.
- The first draft of the reference was 92 s; adding ~5 sentences brought it to 124 s. Measure, then adjust.

### 5.2 Write for TTS (important)

- Spell symbols as spoken words: `C++` → "C plus plus", `counter++` → "counter plus plus",
  `std::move` → "move", `unique_ptr` → "unique pointer", `!=` → "is not equal to".
- Acronyms read letter by letter: write `R.A.I.I.`; acronyms read as words stay as is (`RAM`).
- Never put code, `<`, `>`, `::`, or emoji in narration text. Code goes on screen, not in the voice.
- Short sentences, commas for breathing. One idea per sentence.
- The on-screen text may use real symbols (`C++`, `std::unique_ptr<int>`).

### 5.3 Sync patterns

**A. Bookmarks (preferred, needs Whisper):**

```python
with self.voiceover("Each call pushes a frame, <bookmark mark='pop'/> and returning pops it."):
    self.play(FadeIn(frame))           # plays at start of sentence
    self.wait_until_bookmark("pop")    # waits until the word "and" is spoken
    self.play(FadeOut(frame))
```

- Put the bookmark **right before** the word the visual should land on.
- Bookmark names must be unique inside one voiceover block.
- If all animations finish early, the block automatically waits for the audio to end.
- If animations are longer than the audio, the video just continues (no cut) — keep animations short (default `run_time=1`).

**B. Duration-based (fallback without Whisper):**

```python
with self.voiceover("One sentence.") as tracker:
    self.play(Create(diagram), run_time=tracker.duration * 0.6)
```

Use one sentence per `voiceover` block so pacing stays tight.

### 5.4 Subtitles

Manim writes `<Scene>.srt` next to the MP4 automatically (from the voiceover text). Deliver it for YouTube.
To burn subtitles in (optional):
`ffmpeg -i Video.mp4 -vf "subtitles=Video.srt:force_style='FontSize=20'" -c:a copy Video_subbed.mp4`

---

## 6. Production workflow (follow in order)

1. **Topic brief** — audience, length (default 2 min, English), key takeaways (3), tone.
2. **Script** — full narration text, ≈145 wpm, TTS-friendly (5.2). Show it to the user.
3. **Storyboard** — table: `# | scene name | narration | visuals | bookmarks`. Show it, get approval.
4. **Code** — one method per storyboard row inside one `VoiceoverScene` class. Constants for layout at the top. Helpers for repeated shapes (`frame()`, `block()`, `pointer()`, `code()`).
5. **Draft render (480p15, fast):**
   ```bash
   cd ~/manim-studio && source .venv/bin/activate
   manim -ql topic.py SceneName 2>&1 | tee render_ql.log
   ```
   First run is slow (TTS + Whisper per block; ~5–10 min for 2 min of video on CPU). Later runs reuse the audio cache.
6. **Visual QA** (Section 7) — duration check + frame contact sheets + fix.
7. **Iterate** steps 5–6 until clean (usually 1–3 passes).
8. **Final render (1080p60):**
   ```bash
   manim -qh topic.py SceneName 2>&1 | tee render_qh.log
   ```
   ~8–15 min for a 2-min video on a desktop-class CPU. Use `-qk` for 4K only if asked.
   Output: `media/videos/topic/1080p60/SceneName.mp4` + `SceneName.srt`.
9. **Deliver** — path, `ffprobe` stats, what was checked. Offer: GIF/thumbnail, burned subtitles, tweaks.

Useful flags: `-s` (save last frame as PNG only), `-n 3,5` (render only animations 3–5),
`--disable_caching`, `-p` (preview; not useful on headless VMs).

---

## 7. Visual QA loop (mandatory)

### 7.1 Check duration and streams

```bash
V=media/videos/topic/480p15/SceneName.mp4
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of csv=p=0 "$V"
grep -E "Traceback|Error" render_ql.log || echo "no errors"
```

Must have both `video` and `audio` streams. Duration within ±10 % of target, otherwise edit the script.

### 7.2 Find good timestamps from the subtitles

```bash
grep -- "-->" media/videos/topic/480p15/SceneName.srt
```

Sample frames near the **end** of each subtitle line (animations finished, objects at rest).
Frames sampled mid-transition look messy — that is normal; re-sample 1 s later before "fixing".

### 7.3 Contact sheet (8 frames in one image)

```bash
mkdir -p qa && rm -f qa/*.png
i=0; for t in 8 20 32 46 58 75 98 110; do
  ffmpeg -v error -y -ss $t -i "$V" -frames:v 1 qa/f$i.png; i=$((i+1)); done
ffmpeg -v error -y -i qa/f0.png -i qa/f1.png -i qa/f2.png -i qa/f3.png \
  -i qa/f4.png -i qa/f5.png -i qa/f6.png -i qa/f7.png \
  -filter_complex "[0][1][2][3]hstack=4[t];[4][5][6][7]hstack=4[b];[t][b]vstack" qa/grid.png
```

Open/view `qa/grid.png` and check every item:

- [ ] No text overlaps another object or label (most common bug).
- [ ] Nothing clipped at frame edges; 0.3-unit margin respected.
- [ ] Code is readable (≥ ~22 px line height at 1080p; in the 480p draft, code text must be clearly legible).
- [ ] Previous scene's objects are gone (no leftovers stacking up).
- [ ] Colors follow the semantics table (red = bad, green = fix).
- [ ] Recap/end frame looks intentional, not empty.
- [ ] Math renders (no raw `\text{...}` showing).

After the final render, extract 1–2 frames at full 1080p to confirm sharpness.

### 7.4 Fix → re-render

Visual-only edits re-use cached audio, so the re-render is quicker. Changing narration text regenerates only the changed clips.

---

## 8. Known pitfalls & fixes (learned in production)

| Symptom | Cause | Fix |
|---|---|---|
| Code window tiny / unreadable | `Code(...).scale(0.6)` on default size | Use `scale_to_fit_height(0.5 + 0.42*lines)` capped at 2.0 (see `code()` helper) |
| Label overlaps a neighbour block | Placed with `next_to(..., UP)` near other objects | Put labels on the free side (`DOWN`), or reposition blocks; re-check contact sheet |
| Video much shorter than planned | Script too short (≈145 wpm) | Add explanatory sentences with their own bookmark + small visual (caption/label) |
| Bookmark fires at wrong time / not at all | Whisper not installed or narration contains symbols | Install `manim-voiceover[transcribe]`; spell symbols as words; bookmark before a plain word |
| `Code.__init__() got unexpected keyword` | Old tutorials use `code=`, `font=`, `style=` | Manim ≥0.19: `Code(code_string=..., language=..., formatter_style=..., background="window", paragraph_config={"font": ...})` |
| LaTeX error / missing `.sty` | Minimal TeX install | `apt install texlive-latex-extra texlive-fonts-extra`; or replace `MathTex` with `Text` |
| Font silently falls back to serif | Font not installed (`Consolas` on Linux) | `fc-list | grep -i mono`; use `JetBrains Mono` / `DejaVu Sans Mono` |
| `Indicate` on a `Transform`ed title behaves oddly | `Transform` keeps the original object | Keep reference to the *original* mobject (`self.header = title`) |
| Objects from earlier scenes reappear in recap | Not faded out | Track persistent mobjects as attributes; `FadeOut` them explicitly |
| TTS speaks only the first word | Text split by a shell/CLI wrapper | Call Kokoro via Python (`kokoro_service.py`), never via shell args |
| `SoX could not be found` | Recorder dependency | Ignore |
| Very slow first render | TTS + Whisper per block on CPU | Normal; subsequent renders use `media/voiceovers` cache |

---

## 9. Quality bar (definition of done)

- 1920×1080, 60 fps, H.264 + AAC, duration within ±10 % of target.
- Every scene has narration; visuals land on the spoken keyword (bookmarks).
- Consistent header, color semantics, readable code, no overlaps/clipping (QA sheet clean).
- Intro hook in the first 5 s; recap at the end with 3 check-marked takeaways.
- `.srt` delivered alongside the MP4.

---

## 10. Copy-paste prompt for a new session

> Read the attached guide fully. Set up the environment exactly as in Section 2 and verify with 2.5.
> Then make a ~2-minute English explainer video about **<TOPIC>** for **<AUDIENCE>**, in the same style
> as the reference (Appendix A). First show me the full narration script and the storyboard table and
> wait for my approval. After approval, implement, run the draft render, do the visual QA loop from
> Section 7 (show me the contact sheet), fix issues, then render 1080p60 and give me the MP4 + SRT.

Topic ideas that fit this style: CPU cache & false sharing; Big-O visualized; quicksort vs mergesort;
CAN bus frame & arbitration; Android Binder IPC; virtual memory & page tables; move semantics in C++;
TCP handshake & congestion control.

---

## Appendix A — Full reference scene: `cpp_memory.py` ("Stack vs Heap & Smart Pointers", 2:04)

This is the exact scene that produced the reference video (only the font constant changed for Linux).
Render: `manim -qh cpp_memory.py CppMemory`.

Storyboard of this file:

| # | Method | Narration gist | Visuals |
|---|---|---|---|
| 1 | `intro` | Every variable lives in memory; stack or heap | Title → header; STACK/HEAP columns draw in |
| 2 | `stack` | Calls push/pop frames; small, fast, automatic | `main()`, `f()`, `g()` frames push & pop; "~1-8 MB, fast" |
| 3 | `heap` | `new` allocates; you keep a pointer | Block "42" on heap, arrow from stack frame; "large, manual" |
| 4 | `leak` | Forget delete → leak; piles up in long-running systems | Frame & arrow vanish, block turns red "leaked!", more red blocks |
| 5 | `dangling` | Delete then use → undefined behavior | Block becomes dashed ghost, red wiggling arrow |
| 6 | `raii` | Smart pointer on stack owns heap memory | Green `unique_ptr` frame + block; scope end → both vanish |
| 7 | `unique` | One owner, move not copy | Arrow moves p→q, p becomes `nullptr`, copy code crossed out |
| 8 | `shared` | Ref count; zero frees; beware cycles | 3 owners, `ref count = 3→2→1→0`, block shrinks; A⇄B cycle |
| 9 | `recap` | Stack for locals, smart pointers for heap, no raw new | 3 rows with green check marks |

```python
from manim import *
from manim_voiceover import VoiceoverScene

from kokoro_service import KokoroService

MONO = "JetBrains Mono"  # "Consolas" on Windows, "DejaVu Sans Mono" as fallback

STACK_X = -4.3
STACK_BASE_Y = -3.05
FRAME_H = 0.6
FRAME_GAP = 0.72
HEAP_CENTER = np.array([3.9, -1.5, 0])
CODE_POS = UP * 2.1

STACK_COLOR = BLUE_C
HEAP_COLOR = YELLOW
SMART_COLOR = GREEN_C
BAD_COLOR = RED


def code(src: str) -> Code:
    c = Code(
        code_string=src,
        language="cpp",
        background="window",
        formatter_style="monokai",
        add_line_numbers=False,
        paragraph_config={"font": MONO},
    )
    c.scale_to_fit_height(min(2.0, 0.5 + 0.42 * src.count("\n") + 0.42))
    if c.width > 10:
        c.scale_to_fit_width(10)
    return c.move_to(CODE_POS)


def frame(label: str, slot: int, color=STACK_COLOR) -> VGroup:
    rect = Rectangle(width=2.8, height=FRAME_H, color=color, fill_opacity=0.18)
    text = Text(label, font=MONO, font_size=22, color=color).move_to(rect)
    return VGroup(rect, text).move_to([STACK_X, STACK_BASE_Y + slot * FRAME_GAP, 0])


def block(value: str, pos=HEAP_CENTER, color=HEAP_COLOR) -> VGroup:
    sq = Square(side_length=0.9, color=color, fill_opacity=0.15)
    text = Text(value, font=MONO, font_size=30, color=color).move_to(sq)
    return VGroup(sq, text).move_to(pos)


def pointer(src: VGroup, dst: VGroup, color=WHITE) -> Arrow:
    return Arrow(src.get_right(), dst.get_left(), buff=0.1, color=color, stroke_width=4)


class CppMemory(VoiceoverScene):
    def construct(self):
        self.set_speech_service(KokoroService(voice="am_michael", transcription_model="base"))
        self.intro()
        self.stack()
        self.heap()
        self.leak()
        self.dangling()
        self.raii()
        self.unique()
        self.shared()
        self.recap()

    # ---------- layout ----------
    def build_columns(self) -> VGroup:
        stack_lbl = Text("STACK", font_size=30, weight=BOLD, color=STACK_COLOR).move_to([STACK_X, 0.75, 0])
        stack_box = Rectangle(width=3.2, height=3.7, color=STACK_COLOR, stroke_opacity=0.5).move_to(
            [STACK_X, -1.55, 0]
        )
        heap_lbl = Text("HEAP", font_size=30, weight=BOLD, color=HEAP_COLOR).move_to([3.9, 0.75, 0])
        heap_box = DashedVMobject(
            RoundedRectangle(corner_radius=0.3, width=4.6, height=3.7, color=HEAP_COLOR), num_dashes=60
        ).move_to([3.9, -1.55, 0])
        return VGroup(stack_lbl, stack_box, heap_lbl, heap_box)

    def show_code(self, src: str):
        new = code(src)
        if getattr(self, "code_mob", None) is None:
            self.play(FadeIn(new, shift=DOWN * 0.3))
        else:
            self.play(FadeTransform(self.code_mob, new))
        self.code_mob = new

    # ---------- scenes ----------
    def intro(self):
        title = Text("Stack vs Heap", font_size=72, weight=BOLD)
        sub = Text("& Smart Pointers in C++", font_size=40, color=GREY_B).next_to(title, DOWN)
        self.columns = self.build_columns()
        self.code_mob = None

        with self.voiceover(
            "Every variable in C plus plus lives somewhere in memory. "
            "<bookmark mark='cols'/> Usually on the stack, or on the heap. "
            "Get it wrong, and you leak memory, or crash. "
            "<bookmark mark='next'/> In the next two minutes, let's see how each one works, "
            "and how smart pointers keep you safe."
        ):
            self.play(Write(title), FadeIn(sub, shift=UP * 0.3))
            self.wait_until_bookmark("cols")
            header = Text("Stack vs Heap", font_size=34, weight=BOLD).to_edge(UP, buff=0.25)
            self.play(FadeOut(sub), Transform(title, header))
            self.play(Create(self.columns), run_time=1.5)
            self.wait_until_bookmark("next")
            self.play(Indicate(self.columns[0], color=STACK_COLOR), Indicate(self.columns[2], color=HEAP_COLOR))
        self.header = title

    def stack(self):
        with self.voiceover(
            "Local variables live on the stack. <bookmark mark='push'/> Each function call pushes a frame, "
            "<bookmark mark='pop'/> and when the function returns, the frame is popped. "
            "Fast, and completely automatic. <bookmark mark='small'/> But the stack is small, "
            "usually just a few megabytes, and everything on it dies with its function."
        ):
            self.show_code("void f() {\n    int x = 5;\n}")
            self.main_frame = frame("main()", 0)
            self.play(FadeIn(self.main_frame, shift=DOWN * 0.5))
            self.wait_until_bookmark("push")
            f = frame("f(): x = 5", 1)
            g = frame("g()", 2)
            self.play(FadeIn(f, shift=DOWN * 0.5))
            self.play(FadeIn(g, shift=DOWN * 0.5))
            self.wait_until_bookmark("pop")
            self.play(FadeOut(g, shift=UP * 0.5))
            self.play(FadeOut(f, shift=UP * 0.5))
            self.play(Indicate(self.main_frame, color=STACK_COLOR))
            self.wait_until_bookmark("small")
            size = Text("~1-8 MB, fast", font_size=24, color=STACK_COLOR).next_to(self.columns[1], DOWN, buff=0.15)
            self.play(FadeIn(size, shift=UP * 0.2))
        self.stack_size = size

    def heap(self):
        with self.voiceover(
            "The heap is different. <bookmark mark='new'/> When you call new, the data is placed on the heap, "
            "<bookmark mark='ptr'/> and you only keep a pointer to it. "
            "It stays alive until you call delete. <bookmark mark='big'/> The heap is large and flexible, "
            "but slower, and cleaning it up is your job."
        ):
            self.show_code("void f() {\n    int* p = new int(42);\n}")
            self.f_frame = frame("f(): int* p", 1)
            self.play(FadeIn(self.f_frame, shift=DOWN * 0.5))
            self.wait_until_bookmark("new")
            self.blk = block("42")
            self.play(GrowFromCenter(self.blk))
            self.wait_until_bookmark("ptr")
            self.arrow = pointer(self.f_frame, self.blk)
            self.play(GrowArrow(self.arrow))
            self.wait_until_bookmark("big")
            size = Text("large, manual", font_size=24, color=HEAP_COLOR).next_to(self.columns[3], DOWN, buff=0.15)
            self.play(FadeIn(size, shift=UP * 0.2))
        self.heap_size = size

    def leak(self):
        with self.voiceover(
            "So what if you forget delete? <bookmark mark='ret'/> The function returns, and the pointer disappears. "
            "<bookmark mark='leak'/> But the memory stays behind, and nobody can free it. "
            "That is a memory leak. <bookmark mark='pile'/> In a long running system, like a server or a car's "
            "infotainment unit, leaks pile up until memory runs out."
        ):
            self.wait_until_bookmark("ret")
            self.play(FadeOut(self.f_frame, shift=UP * 0.5), FadeOut(self.arrow))
            self.wait_until_bookmark("leak")
            self.play(self.blk.animate.set_color(BAD_COLOR))
            tag = Text("leaked!", font_size=26, color=BAD_COLOR).next_to(self.blk, DOWN)
            self.play(FadeIn(tag, shift=UP * 0.2))
            self.wait_until_bookmark("pile")
            extras = VGroup(
                block("42", HEAP_CENTER + LEFT * 1.3 + DOWN * 1.2, BAD_COLOR),
                block("42", HEAP_CENTER + RIGHT * 1.3 + DOWN * 1.2, BAD_COLOR),
                block("42", HEAP_CENTER + RIGHT * 1.3 + UP * 0.9, BAD_COLOR),
            )
            self.play(LaggedStart(*[GrowFromCenter(e) for e in extras], lag_ratio=0.4))
        self.play(FadeOut(VGroup(self.blk, tag, extras)))

    def dangling(self):
        with self.voiceover(
            "The opposite mistake is just as bad. <bookmark mark='del'/> Delete the memory, "
            "<bookmark mark='use'/> then use the pointer again, and you get undefined behavior."
        ):
            self.show_code("int* p = new int(7);\ndelete p;\n*p = 3;  // !!")
            fr = frame("f(): int* p", 1)
            blk = block("7")
            arr = pointer(fr, blk)
            self.play(FadeIn(fr, shift=DOWN * 0.5), GrowFromCenter(blk), GrowArrow(arr))
            self.wait_until_bookmark("del")
            ghost = DashedVMobject(Square(side_length=0.9, color=GREY), num_dashes=16).move_to(blk)
            self.play(FadeOut(blk[1]), ReplacementTransform(blk[0], ghost))
            self.wait_until_bookmark("use")
            ub = Text("undefined behavior", font_size=28, color=BAD_COLOR).next_to(ghost, UP, buff=0.3)
            self.play(arr.animate.set_color(BAD_COLOR), FadeIn(ub))
            self.play(Wiggle(arr), Flash(ghost, color=BAD_COLOR))
        self.play(FadeOut(VGroup(fr, ghost, arr, ub)))

    def raii(self):
        with self.voiceover(
            "Modern C plus plus solves this with R.A.I.I. <bookmark mark='own'/> A smart pointer on the stack "
            "owns the heap memory. <bookmark mark='scope'/> When it goes out of scope, its destructor "
            "frees the memory automatically."
        ):
            self.show_code("void f() {\n    auto p = std::make_unique<int>(42);\n}")
            self.wait_until_bookmark("own")
            fr = frame("unique_ptr p", 1, SMART_COLOR)
            blk = block("42")
            arr = pointer(fr, blk, SMART_COLOR)
            self.play(FadeIn(fr, shift=DOWN * 0.5), GrowFromCenter(blk))
            self.play(GrowArrow(arr))
            self.wait_until_bookmark("scope")
            self.play(Indicate(fr, color=SMART_COLOR))
            self.play(FadeOut(fr, shift=UP * 0.5), FadeOut(arr), ShrinkToCenter(blk))
            ok = Text("freed automatically", font_size=28, color=SMART_COLOR).move_to(HEAP_CENTER)
            self.play(FadeIn(ok, scale=0.8))
        self.play(FadeOut(ok))

    def unique(self):
        with self.voiceover(
            "A unique pointer has exactly one owner. <bookmark mark='move'/> You can move ownership "
            "to another pointer, <bookmark mark='copy'/> but you can never copy it."
        ):
            self.show_code("auto p = std::make_unique<int>(42);\nauto q = std::move(p);")
            p = frame("unique_ptr p", 1, SMART_COLOR)
            q = frame("unique_ptr q", 2, SMART_COLOR)
            blk = block("42")
            arr = pointer(p, blk, SMART_COLOR)
            self.play(FadeIn(p, shift=DOWN * 0.5), FadeIn(q, shift=DOWN * 0.5), GrowFromCenter(blk), GrowArrow(arr))
            self.wait_until_bookmark("move")
            p_empty = frame("p: nullptr", 1, GREY)
            self.play(Transform(arr, pointer(q, blk, SMART_COLOR)), Transform(p, p_empty))
            self.wait_until_bookmark("copy")
            self.show_code("auto r = q;  // copy?")
            cross = Cross(self.code_mob, stroke_color=BAD_COLOR, stroke_width=8)
            self.play(Create(cross))
        self.play(FadeOut(VGroup(p, q, blk, arr, cross)))

    def shared(self):
        with self.voiceover(
            "A shared pointer allows many owners, and keeps a reference count. "
            "<bookmark mark='drop'/> Each time an owner goes away, the count goes down. "
            "<bookmark mark='zero'/> When it reaches zero, the memory is freed. "
            "<bookmark mark='cycle'/> Just watch out for cycles, where two shared pointers own each other, "
            "and the count never reaches zero."
        ):
            self.show_code("auto a = std::make_shared<int>(42);\nauto b = a;\nauto c = a;")
            owners = [frame(f"shared_ptr {n}", i + 1, SMART_COLOR) for i, n in enumerate("abc")]
            blk = block("42")
            arrows = [pointer(o, blk, SMART_COLOR) for o in owners]
            count = Integer(3, font_size=48, color=HEAP_COLOR)
            label = MathTex(r"\text{ref count} =", font_size=44, color=HEAP_COLOR)
            counter = VGroup(label, count).arrange(RIGHT, buff=0.2).next_to(blk, DOWN, buff=0.5)
            self.play(
                LaggedStart(*[FadeIn(o, shift=DOWN * 0.5) for o in owners], lag_ratio=0.3),
                GrowFromCenter(blk),
            )
            self.play(*[GrowArrow(a) for a in arrows], Write(counter))
            self.wait_until_bookmark("drop")
            for i in (2, 1):
                self.play(FadeOut(owners[i], shift=UP * 0.5), FadeOut(arrows[i]), count.animate.set_value(i))
            self.wait_until_bookmark("zero")
            self.play(FadeOut(owners[0], shift=UP * 0.5), FadeOut(arrows[0]), count.animate.set_value(0))
            self.play(ShrinkToCenter(blk), counter.animate.set_color(SMART_COLOR))
            self.wait_until_bookmark("cycle")
            self.play(FadeOut(counter))
            na = block("A", HEAP_CENTER + LEFT * 1.0, BAD_COLOR)
            nb = block("B", HEAP_CENTER + RIGHT * 1.0, BAD_COLOR)
            ab = CurvedArrow(na.get_top(), nb.get_top(), angle=-PI / 2, color=BAD_COLOR)
            ba = CurvedArrow(nb.get_bottom(), na.get_bottom(), angle=-PI / 2, color=BAD_COLOR)
            self.play(GrowFromCenter(na), GrowFromCenter(nb))
            self.play(Create(ab), Create(ba))
            cyc = Text("count stays 1", font_size=24, color=BAD_COLOR).next_to(ba, DOWN, buff=0.15)
            self.play(FadeIn(cyc))
        self.play(FadeOut(VGroup(na, nb, ab, ba, cyc)))

    def recap(self):
        items = [
            "Stack: local data, freed automatically",
            "Heap: use smart pointers",
            "Avoid raw new / delete",
        ]
        rows = VGroup(
            *[
                VGroup(MathTex(r"\checkmark", color=SMART_COLOR, font_size=56), Text(t, font_size=34)).arrange(
                    RIGHT, buff=0.35
                )
                for t in items
            ]
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.5)

        with self.voiceover(
            "To recap: <bookmark mark='r1'/> use the stack for local data, <bookmark mark='r2'/> smart pointers "
            "for the heap, <bookmark mark='r3'/> and you will rarely need a raw new or delete again."
        ):
            recap_title = Text("Recap", font_size=34, weight=BOLD).to_edge(UP, buff=0.25)
            self.play(
                FadeOut(VGroup(self.columns, self.main_frame, self.code_mob, self.stack_size, self.heap_size)),
                Transform(self.header, recap_title),
            )
            for i, mark in enumerate(("r1", "r2", "r3")):
                self.wait_until_bookmark(mark)
                self.play(FadeIn(rows[i], shift=RIGHT * 0.4))
        self.wait(1.5)
```

---

## Appendix B — Platform notes

**Muse (muse.ai, Meta personal agent):** runs on a persistent Ubuntu "Secure VM" with root inside its
runtime cell; files are visible in the app's Library/file explorer for download. Outbound traffic passes
through the "Sentinel" monitor — if a download is blocked, use Section 2.6 fallbacks or ask the user to
upload the model files. Renders are CPU-bound; prefer `-ql` drafts and only one `-qh` final render.
Share the final MP4 via the file explorer / "Download your agent data".

**Muse Code (terminal agent):** macOS/Linux only; on Windows use WSL2 (Ubuntu) and follow Section 2 inside
WSL. The default sandbox makes only the workspace writable — run everything inside the project folder,
put Kokoro files in `./models` and set `export KOKORO_DIR=$PWD/models`; `apt` installs may need user
approval or must be done by the user beforehand. Put this guide in the repo as `AGENTS.md` (or reference
it from `AGENTS.md`) so every session loads it automatically.

**Windows (native, for reference):** this pipeline was built on Windows 11 with Python 3.12 (uv venv),
MiKTeX (`[MPM]AutoInstall=1`), ffmpeg from winget, font `Consolas`. Kokoro files were at
`%USERPROFILE%\.cache\hyperframes\tts\{models,voices}`. Invoke `.venv\Scripts\manim.exe`. When running in an
elevated shell MiKTeX prints "security risk: running with elevated privileges" — harmless.
