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
