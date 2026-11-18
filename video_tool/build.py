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
