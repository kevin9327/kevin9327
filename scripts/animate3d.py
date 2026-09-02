#!/usr/bin/env python3
"""Give the generated 3D contribution graphs continuous motion.

github-profile-3d-contrib draws each day as an isometric bar: a
<g transform="translate(x y)"> holding a top face and two side faces, and
plays a one-shot growth animation on load. Everything after that is still.
This pass reads the generated files and writes *-live.svg siblings with:

  * a wave rolling along the weeks axis -- every bar bobs, phased by its x
  * a gloss highlight on each top face that rides the crest of that wave
  * a slow camera breathe on the root viewBox
  * twinkling stars behind dark backgrounds

The originals are never modified, so re-running is idempotent and the output
is deterministic (seeded) so CI does not churn commits.
"""
from __future__ import annotations

import random
import re
import sys
from pathlib import Path

DIR = Path("profile-3d-contrib")
JOBS = [  # (source file, dark background?)
    ("profile-night-rainbow.svg", True),
    ("profile-season-animate.svg", False),
    ("profile-green-animate.svg", False),
]

WAVE_DUR = 2.8      # seconds per bob
WAVE_AMP = 14       # px a bar rises at the crest
WAVE_SPREAD = 0.85  # fraction of WAVE_DUR the crest takes to cross the weeks
GLOSS = 0.42        # peak opacity of the highlight
BREATHE_DUR = 12    # seconds for one camera breath
BREATHE = 0.012     # fraction of the viewBox the camera zooms out
STARS = 70

EASE = 'calcMode="spline" keySplines="0.42 0 0.58 1;0.42 0 0.58 1"'

# a bar: its group open tag, then (optionally) the growth animation the action
# added, then the isometric top face
BAR_RE = re.compile(
    r'<g transform="translate\((?P<x>[\d.]+) (?P<y>[\d.]+)\)">'
    r'(?:<animateTransform[^>]*>(?:</animateTransform>)?)?'
    r'<rect(?P<attrs>[^>]*transform="(?P<tf>skewY\(-30\) skewX\(40\.89\)[^"]*)"[^>]*?)'
    r'(?:/>|>.*?</rect>)',
    re.S,
)
SVG_RE = re.compile(r'<svg[^>]*viewBox="0 0 (?P<w>[\d.]+) (?P<h>[\d.]+)"[^>]*>')
BG_RE = re.compile(r'<rect x="0" y="0" width="[\d.]+" height="[\d.]+" fill="[^"]+">(?:</rect>)?')


def size_of(attrs: str) -> tuple[str, str]:
    w = re.search(r'width="([\d.]+)"', attrs)
    h = re.search(r'height="([\d.]+)"', attrs)
    return (w.group(1) if w else "18", h.group(1) if h else "18")


def animate(src: Path, dark: bool) -> tuple[int, Path]:
    svg = src.read_text(encoding="utf-8")
    bars = list(BAR_RE.finditer(svg))
    if not bars:
        raise SystemExit(f"{src}: found no isometric bars; the generator's markup changed")

    xs = [float(m.group("x")) for m in bars]
    ys = [float(m.group("y")) for m in bars]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)

    out = svg
    # insert from the end so earlier offsets stay valid
    for m in reversed(bars):
        x, y = float(m.group("x")), float(m.group("y"))
        tx = (x - x0) / (x1 - x0) if x1 > x0 else 0.0
        ty = (y - y0) / (y1 - y0) if y1 > y0 else 0.0
        phase = tx * WAVE_DUR * WAVE_SPREAD + ty * 0.25
        w, h = size_of(m.group("attrs"))
        end = out.find("</g>", m.end())
        if end < 0:
            continue
        extra = (
            f'<animateTransform attributeName="transform" type="translate" additive="sum" '
            f'values="0 0;0 -{WAVE_AMP};0 0" keyTimes="0;0.5;1" {EASE} '
            f'dur="{WAVE_DUR}s" begin="{phase:.2f}s" repeatCount="indefinite"/>'
            f'<rect x="0" y="0" width="{w}" height="{h}" transform="{m.group("tf")}" '
            f'fill="#ffffff" opacity="0" pointer-events="none">'
            f'<animate attributeName="opacity" values="0;{GLOSS};0" keyTimes="0;0.5;1" {EASE} '
            f'dur="{WAVE_DUR}s" begin="{phase:.2f}s" repeatCount="indefinite"/></rect>'
        )
        out = out[:end] + extra + out[end:]

    # camera breathe
    root = SVG_RE.search(out)
    if root:
        w, h = float(root.group("w")), float(root.group("h"))
        dx, dy = w * BREATHE, h * BREATHE
        breathe = (
            f'<animate attributeName="viewBox" values="0 0 {w:g} {h:g};'
            f'{-dx:.1f} {-dy:.1f} {w + 2 * dx:.1f} {h + 2 * dy:.1f};0 0 {w:g} {h:g}" '
            f'keyTimes="0;0.5;1" {EASE} dur="{BREATHE_DUR}s" repeatCount="indefinite"/>'
        )
        out = out[: root.end()] + breathe + out[root.end():]

    # stars, only over a dark sky
    if dark:
        bg = BG_RE.search(out)
        if bg and root:
            rng = random.Random(9327)
            w, h = float(root.group("w")), float(root.group("h"))
            stars = []
            for _ in range(STARS):
                sx, sy = rng.uniform(0, w), rng.uniform(0, h)
                r = rng.uniform(0.8, 2.2)
                dur = rng.uniform(1.6, 4.5)
                begin = rng.uniform(0, 4)
                peak = rng.uniform(0.35, 0.9)
                stars.append(
                    f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r:.1f}" fill="#ffffff" opacity="0">'
                    f'<animate attributeName="opacity" values="0;{peak:.2f};0" dur="{dur:.1f}s" '
                    f'begin="{begin:.1f}s" repeatCount="indefinite"/></circle>'
                )
            out = out[: bg.end()] + "".join(stars) + out[bg.end():]

    dst = src.with_name(src.stem + "-live.svg")
    dst.write_text(out, encoding="utf-8", newline="\n")
    return len(bars), dst


def main() -> int:
    if not DIR.is_dir():
        print(f"{DIR}/ is missing; run the generator first", file=sys.stderr)
        return 1
    done = 0
    for name, dark in JOBS:
        src = DIR / name
        if not src.exists():
            print(f"skip {name}: not generated")
            continue
        n, dst = animate(src, dark)
        print(f"{dst}: {n} bars set in motion ({dst.stat().st_size // 1024} KB)")
        done += 1
    return 0 if done else 1


if __name__ == "__main__":
    raise SystemExit(main())
