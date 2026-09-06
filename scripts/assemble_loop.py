"""Stitch a folder of rendered frames into one looping animated WebP plus a
still PNG poster. Generic sibling of assemble_hero.py for the other loops.

Usage: python scripts/assemble_loop.py <frames_dir> <out.webp> [fps] [quality] [width]
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

frames_dir = Path(sys.argv[1])
out = Path(sys.argv[2])
fps = float(sys.argv[3]) if len(sys.argv) > 3 else 18.0
quality = int(sys.argv[4]) if len(sys.argv) > 4 else 82
width = int(sys.argv[5]) if len(sys.argv) > 5 else 0
out.parent.mkdir(parents=True, exist_ok=True)

paths = sorted(frames_dir.glob("frame_*.png"))
if not paths:
    raise SystemExit(f"no frames in {frames_dir}")
frames = [Image.open(p).convert("RGB") for p in paths]
if width and frames[0].width != width:
    frames = [f.resize((width, round(f.height * width / f.width)), Image.LANCZOS) for f in frames]
dur = int(round(1000 / fps))
print(f"{len(frames)} frames, {frames[0].size}, {dur} ms each")

frames[0].save(out, save_all=True, append_images=frames[1:], duration=dur, loop=0,
               quality=quality, method=6, minimize_size=True)
print(f"webp: {out} {out.stat().st_size / 1024 / 1024:.2f} MB")

poster = out.with_name(out.stem + "-poster.png")
frames[0].save(poster, optimize=True)
print(f"png : {poster} {poster.stat().st_size / 1024:.0f} KB")
