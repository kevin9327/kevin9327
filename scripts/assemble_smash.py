"""Sequence the three render sets of render_smash.py into one looping WebP.

    A[0..58]    forward: idle, the slice, the blast, the debris
    A x B       frames 46..54: cross-fade into the FIX debris field, played backwards
    B[127 - f]  frames 56..104: the debris gathers itself back into FIX
    H[106..146] FIX intact, the knight cheering
    rewind      the whole thing backwards at 3x, with a REW marker, so the loop closes on frame 0

Usage:
    py -3.11 scripts/assemble_smash.py <frames_dir> <out.webp> [fps=12] [quality=64] [width=1000]
"""
import os
import sys

from PIL import Image, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixelfont import rows_of  # noqa: E402

SRC = sys.argv[1]
OUT = sys.argv[2]
FPS = int(sys.argv[3]) if len(sys.argv) > 3 else 12
QUALITY = int(sys.argv[4]) if len(sys.argv) > 4 else 64
WIDTH = int(sys.argv[5]) if len(sys.argv) > 5 else 1000
FADE = (46, 54)
B_OFF = 127          # B frame shown at forward frame f is B_OFF - f
REW_STRIDE = 6


def frame(mode, f):
    p = os.path.join(SRC, f"{mode}_{f:04d}.png")
    return Image.open(p).convert("RGB")


def composed(f):
    if f <= FADE[0] - 2:
        return frame("A", f)
    if f <= FADE[1]:
        a = (f - FADE[0]) / (FADE[1] - FADE[0])
        return Image.blend(frame("A", f), frame("B", B_OFF - f), a)
    if f <= 104:
        return frame("B", B_OFF - f)
    return frame("H", f)


def pixel_text(im, s, x, y, scale, color):
    px = im.load()
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        for r, row in enumerate(rows_of(ch)):
            for c, bit in enumerate(row):
                if bit == "#":
                    for dy in range(scale):
                        for dx in range(scale):
                            X, Y = x + (i * 6 + c) * scale + dx, y + r * scale + dy
                            if 0 <= X < im.width and 0 <= Y < im.height:
                                px[X, Y] = color


forward = [composed(f) for f in range(0, 147, 2)]
rewind = []
for f in range(146, 0, -REW_STRIDE):
    im = composed(f).copy()
    # a rewinding tape: slightly dimmer, with the marker
    im = ImageChops.multiply(im, Image.new("RGB", im.size, (215, 215, 225)))
    pixel_text(im, "REW", im.width - 3 * 6 * 3 - 18, 18, 3, (250, 204, 21))
    pixel_text(im, "X3", im.width - 3 * 6 * 3 - 18, 48, 2, (139, 148, 158))
    rewind.append(im)
frames = forward + rewind
if frames[0].width != WIDTH:
    h = round(frames[0].height * WIDTH / frames[0].width)
    frames = [im.resize((WIDTH, h), Image.LANCZOS) for im in frames]
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=round(1000 / FPS), loop=0,
               quality=QUALITY, method=6)
frames[len(forward) // 2].save(OUT.rsplit(".", 1)[0] + "-poster.png")
print(f"{OUT}: {len(forward)} forward + {len(rewind)} rewind frames at {FPS} fps, "
      f"{os.path.getsize(OUT) / 1e6:.2f} MB")
