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
