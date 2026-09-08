"""Lay the game HUD over the boss-fight frames from render_boss.py and write the looping WebP.

Reads boss_hits.json from the frames folder (written by the renderer): the frame and screen position
of every hit, the frame of the last one, and the end of the film.

    top left       KNIGHT and a full green bar
    top centre     PRODUCTION BUG and its health, 34% at the start, chipped by every hit, gone on the last
    every hit      the bar flashes white and a damage number rises from where the blade landed
    after the last BUG SLAIN / PR MERGED
    the loop       fades to black over the last frames and in over the first

Usage:
    py -3.11 scripts/assemble_boss.py <frames_dir> <out.webp> [fps=12] [quality=66] [width=1000]
"""
import glob
import json
import os
import sys

from PIL import Image, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixelfont import rows_of  # noqa: E402

SRC = sys.argv[1]
OUT = sys.argv[2]
FPS = int(sys.argv[3]) if len(sys.argv) > 3 else 12
QUALITY = int(sys.argv[4]) if len(sys.argv) > 4 else 66
WIDTH = int(sys.argv[5]) if len(sys.argv) > 5 else 1000
PINK, YELLOW, GREEN, MUTE, INK, WHITE = (236, 72, 153), (250, 204, 21), (63, 185, 80), (139, 148, 158), (13, 17, 23), (255, 255, 255)

with open(os.path.join(SRC, "boss_hits.json")) as fh:
    meta = json.load(fh)
HITS = meta["hits"]
T_HIT, END = meta["t_hit"], meta["end"]
HP = [0.34, 0.22, 0.10, 0.0]                      # before the first hit, then after each
DAMAGE = ["-1024", "-1536", "-4096"]


def pixel_text(im, s, x, y, scale, color, shadow=None):
    px = im.load()
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        for r, row in enumerate(rows_of(ch)):
            for c, bit in enumerate(row):
                if bit != "#":
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        X, Y = x + (i * 6 + c) * scale + dx, y + r * scale + dy
                        if shadow and 0 <= X + 2 < im.width and 0 <= Y + 2 < im.height:
                            px[X + 2, Y + 2] = shadow
                        if 0 <= X < im.width and 0 <= Y < im.height:
                            px[X, Y] = color


def text_width(s, scale):
    return (len(s) * 6 - 1) * scale


def bar(im, x, y, w, h, frac, color, track=(42, 36, 49), seg=14):
    px = im.load()
    for X in range(x, x + w):
        for Y in range(y, y + h):
            on = (X - x) < frac * w and (X - x) % seg not in (seg - 1, seg - 2)
            px[X, Y] = color if on else track


def scale_color(c, k):
    return tuple(int(v * k) for v in c)


frames = []
files = sorted(glob.glob(os.path.join(SRC, "F_*.png")))
fnums = [int(os.path.basename(p)[2:6]) for p in files]
last = fnums[-1]
for p, f in zip(files, fnums):
    im = Image.open(p).convert("RGB")
    W, H = im.size
    pixel_text(im, "KNIGHT", 28, 18, 2, (230, 237, 243), shadow=INK)
    bar(im, 28, 36, 170, 9, 1.0, GREEN)
    name = "PRODUCTION BUG"
    bx, bw = W // 2 - 220, 440
    pixel_text(im, name, W // 2 - text_width(name, 2) // 2, 18, 2, PINK, shadow=INK)
    landed = sum(1 for h in HITS if f >= h["frame"])
    flashing = any(h["frame"] <= f < h["frame"] + 4 for h in HITS)
    bar(im, bx, 36, bw, 11, HP[min(landed, len(HP) - 1)] if not flashing else HP[landed - 1], WHITE if flashing else PINK)
    for i, h in enumerate(HITS):
        age = f - h["frame"]
        if 0 <= age < 26:
            k = 1.0 if age < 14 else 1 - (age - 14) / 12
            x, y = h["x"] - 70, h["y"] - 60 - age * 2
            crit = i == len(HITS) - 1
            if crit:
                pixel_text(im, "CRIT", x + 6, y - 22, 2, scale_color(YELLOW, k))
            pixel_text(im, DAMAGE[min(i, len(DAMAGE) - 1)], x, y, 5 if crit else 4, scale_color(YELLOW if crit else WHITE, k),
                       shadow=scale_color(INK, k))
    if f >= T_HIT + 24:
        k = min((f - T_HIT - 24) / 6, 1.0)
        s = "BUG SLAIN"
        pixel_text(im, s, W // 2 - text_width(s, 7) // 2, 132, 7, scale_color(YELLOW, k), shadow=INK)
        s2 = "PR MERGED"
        pixel_text(im, s2, W // 2 - text_width(s2, 3) // 2, 190, 3, scale_color(MUTE, k))
    fade = 1.0
    if f <= 6:
        fade = f / 6
    if f >= last - 8:
        fade = (last - f) / 8
    if fade < 1.0:
        im = ImageChops.multiply(im, Image.new("RGB", im.size, (int(255 * fade),) * 3))
    frames.append(im)

if frames[0].width != WIDTH:
    h = round(frames[0].height * WIDTH / frames[0].width)
    frames = [im.resize((WIDTH, h), Image.LANCZOS) for im in frames]
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=round(1000 / FPS), loop=0, quality=QUALITY, method=6)
poster = min(range(len(fnums)), key=lambda i: abs(fnums[i] - (T_HIT + 6)))
frames[poster].save(OUT.rsplit(".", 1)[0] + "-poster.png")
print(f"{OUT}: {len(frames)} frames at {FPS} fps, hits at {[h['frame'] for h in HITS]}, {os.path.getsize(OUT) / 1e6:.2f} MB")
