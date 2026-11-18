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
