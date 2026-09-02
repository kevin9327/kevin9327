"""Stitch rendered frames into the looping hero: animated WebP (primary, true
colour, small) plus a GIF fallback and a still PNG poster.

Usage: python scripts/assemble_hero.py <frames_dir> <out_dir> [fps]
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

frames_dir = Path(sys.argv[1])
out = Path(sys.argv[2])
fps = float(sys.argv[3]) if len(sys.argv) > 3 else 18.0
out.mkdir(parents=True, exist_ok=True)

paths = sorted(frames_dir.glob("frame_*.png"))
if not paths:
    raise SystemExit(f"no frames in {frames_dir}")
frames = [Image.open(p).convert("RGB") for p in paths]
dur = int(round(1000 / fps))
print(f"{len(frames)} frames, {frames[0].size}, {dur} ms each")

webp = out / "hero.webp"
frames[0].save(webp, save_all=True, append_images=frames[1:], duration=dur, loop=0,
               quality=84, method=6, minimize_size=True)
print(f"webp: {webp.stat().st_size / 1024 / 1024:.2f} MB")

gif = out / "hero.gif"
pal = [f.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
       for f in frames]
pal[0].save(gif, save_all=True, append_images=pal[1:], duration=dur, loop=0, optimize=True, disposal=1)
print(f"gif : {gif.stat().st_size / 1024 / 1024:.2f} MB")

poster = out / "hero-poster.png"
frames[0].save(poster, optimize=True)
print(f"png : {poster.stat().st_size / 1024:.0f} KB")
