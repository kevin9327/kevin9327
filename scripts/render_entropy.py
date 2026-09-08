#!/usr/bin/env python3
"""
render_entropy.py -- RUN IT BACKWARDS: static that assembles itself into a sentence, then lets go.

Emits assets/entropy.svg. Pure SMIL: no script, no filter, no font, no external reference, so it
plays inside the <img> GitHub uses for a profile README.

The automaton is Critters (Margolus neighbourhood): every step, every 2x2 block of cells is
rewritten by one fixed table, and the block grid shifts by one cell between steps. The table is a
bijection on the 16 block states, so the rule is exactly reversible. The sentence is the target;
the seed is found by running the inverse table backwards for STEPS steps. What that lands on looks
like noise -- but it is the sentence, STEPS steps early, and the forward rule recovers it cell for
cell. That is asserted, not hoped. Then the film plays back to the seed, and loops.

Every shown frame is a real state of the automaton. Pure stdlib. Runs in about a second.
"""
import os
import sys
import xml.dom.minidom

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pixelfont import GID, defs as font_defs, raster, text, width as text_width   # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, "..", "assets", "entropy.svg"))

# ---------------------------------------------------------------- parameters
COLS, ROWS = 64, 22
LINES = ["NO BUG", "IS RANDOM"]
STEPS = 80                    # rule steps between the seed and the sentence
SHOW_EVERY = 2                # Critters complements the field every other step; show the even ones
DT = 0.10                     # seconds per shown frame
HOLD_SEED, HOLD_PIC = 0.5, 2.4
W, H = 1000, 430
GX, GY, CELL = 20, 64, 15     # the grid on the canvas
PINK, ORANGE, YELLOW, INK, MUTE, DIM = "#ec4899", "#f97316", "#facc15", "#0d1117", "#8b949e", "#484f58"

assert COLS % 2 == 0 and ROWS % 2 == 0 and STEPS % SHOW_EVERY == 0
NF = STEPS // SHOW_EVERY + 1                              # shown frames, seed .. sentence
A0 = HOLD_SEED                                            # assembly starts
D0 = A0 + (NF - 1) * DT + HOLD_PIC                        # dissolution starts
TL = D0 + (NF - 1) * DT + 0.4                             # the seed is held across the loop seam


# ---------------------------------------------------------------- the automaton
def critters():
    """the block table and its inverse. Bits: 1 = top-left, 2 = top-right, 4 = bottom-left, 8 = bottom-right"""
    table = {}
    for s in range(16):
        bits = [(s >> i) & 1 for i in range(4)]
        n = sum(bits)
        if n == 2:
            out = bits
        else:
            out = [1 - b for b in bits]
            if n == 3:
                out = [out[3], out[2], out[1], out[0]]       # rotate the block by 180 degrees
        table[s] = sum(v << i for i, v in enumerate(out))
    assert sorted(table.values()) == list(range(16)), "the block rule must be a bijection"
    return table, {v: k for k, v in table.items()}


FWD, INV = critters()


def step(grid, phase, table):
    new = [row[:] for row in grid]
    for by in range(0, ROWS, 2):
        for bx in range(0, COLS, 2):
            y0, x0 = (by + phase) % ROWS, (bx + phase) % COLS
            y1, x1 = (y0 + 1) % ROWS, (x0 + 1) % COLS
            s = grid[y0][x0] | grid[y0][x1] << 1 | grid[y1][x0] << 2 | grid[y1][x1] << 3
            o = table[s]
            new[y0][x0], new[y0][x1], new[y1][x0], new[y1][x1] = o & 1, (o >> 1) & 1, (o >> 2) & 1, (o >> 3) & 1
    return new


picture = raster(LINES, COLS, ROWS, gap=3)
states = [None] * (STEPS + 1)
states[STEPS] = picture
for t in range(STEPS - 1, -1, -1):                        # backwards from the answer
    states[t] = step(states[t + 1], t % 2, INV)
g = states[0]
for t in range(STEPS):                                    # and forwards again, to prove it
    g = step(g, t % 2, FWD)
    assert g == states[t + 1], f"the rule does not reproduce step {t + 1}"
assert g == picture, "the seed does not reassemble the sentence"
frames = [states[t] for t in range(0, STEPS + 1, SHOW_EVERY)]
assert len(frames) == NF


def live(grid):
    return [(x, y) for y, row in enumerate(grid) for x, v in enumerate(row) if v]


def order(grid):
    """fraction of live cells with at least two live orthogonal neighbours: strokes score high, static low"""
    cells = live(grid)
    if not cells:
        return 0.0
    n = 0
    for x, y in cells:
        k = grid[y][(x + 1) % COLS] + grid[y][(x - 1) % COLS] + grid[(y + 1) % ROWS][x] + grid[(y - 1) % ROWS][x]
        n += k >= 2
    return n / len(cells)


counts = [len(live(f)) for f in frames]
orders = [order(f) for f in frames]
print(f"grid {COLS}x{ROWS}, {STEPS} rule steps, {NF} shown frames; live cells {min(counts)}..{max(counts)} "
      f"(sentence {counts[-1]}), order {orders[0]:.2f} -> {orders[-1]:.2f}, loop {TL:.2f} s")


# ---------------------------------------------------------------- timeline helpers
def qt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s or "0"


def q(v):
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


def discrete(attr, events, first, tag="animate", extra=""):
    vals, kts = [first], [0.0]
    for t, v in events:
        vals.append(v)
        kts.append(t)
    if kts[-1] < TL:
        vals.append(vals[-1])
        kts.append(TL)
    return (f'<{tag} attributeName="{attr}" dur="{TL}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{";".join(qt(t / TL) for t in kts)}" values="{";".join(vals)}"{extra}/>')


def t_assemble(k):
    return A0 + k * DT


def t_dissolve(k):           # when frame k appears on the way back
    return D0 + (NF - 1 - k) * DT


def frame_events(k):
    """(first value, events) for frame k's visibility, as inline/none"""
    if k == 0:
        return "inline", [(t_assemble(1), "none"), (t_dissolve(0), "inline")]
    if k == NF - 1:
        return "none", [(t_assemble(k), "inline"), (D0, "none")]
    return "none", [(t_assemble(k), "inline"), (t_assemble(k + 1), "none"),
                    (t_dissolve(k), "inline"), (t_dissolve(k - 1), "none")]


def frame_path(grid):
    """one path: a zero-length dash per live cell, drawn with square caps of width .86 so every dash
    is a square. Coordinates are cell indices; the group carries the scale."""
    return "".join(f"M{x} {y}h.01" for x, y in live(grid))


# ---------------------------------------------------------------- emit
out = []
A = out.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
A('<title>RUN IT BACKWARDS</title>')
A(f'<desc>A {COLS} by {ROWS} field of a reversible cellular automaton (Critters). Its first frame looks like '
  f'static, but it is the sentence "{" / ".join(LINES)}" {STEPS} steps early: the same rule, applied forward, '
  f'reassembles the words cell for cell, holds them, and plays back to the static. Generated by '
  f'scripts/render_entropy.py.</desc>')
A('<defs>')
A(f'<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{COLS}" y2="0">'
  f'<stop offset="0" stop-color="{PINK}"/><stop offset="0.5" stop-color="{ORANGE}"/><stop offset="1" stop-color="{YELLOW}"/></linearGradient>')
A('<pattern id="dots" patternUnits="userSpaceOnUse" width="1" height="1">'
  '<rect x="0.38" y="0.38" width="0.24" height="0.24" fill="#ffffff" opacity="0.07"/></pattern>')
used = sorted({c for c in "RUN IT BACKWARDS A REVERSIBLE AUTOMATON STEPS BEFORE THE ANSWER T- ORDER THE FIRST FRAME IS THE LAST FRAME, EARLY 0123456789" if c != " "})
A(font_defs(used))
A('<g id="odo">' + "".join(f'<use href="#c{d}" xlink:href="#c{d}" y="{8 * d}"/>' for d in range(10)) + '</g>')
A('<clipPath id="win"><rect x="-0.5" y="-0.5" width="6" height="8"/></clipPath>')
A('</defs>')
A(f'<rect width="{W}" height="{H}" fill="{INK}"/>')

# header
A(text("RUN IT BACKWARDS", 28, 22, 3, MUTE))
A(text(f"A REVERSIBLE AUTOMATON  {STEPS} STEPS BEFORE THE ANSWER", 28, 50, 2, DIM))
# the countdown: T-40 .. T-0 .. T-40, two clipped digit columns
rx, ry, rs = W - 28, 20, 3
A(text("T-", rx - 4 * 6 * rs, ry, rs, YELLOW))
for col in range(2):
    slot = lambda ch: f"0 {-8 * int(ch)}"
    seq = []
    for k in range(NF):
        seq.append((t_assemble(k), f"{NF - 1 - k:02d}"[col]))
    for k in range(NF - 2, -1, -1):
        seq.append((t_dissolve(k), f"{NF - 1 - k:02d}"[col]))
    rest = f"{NF - 1:02d}"[col]
    ev, cur = [], rest
    for t, ch in seq:
        if ch != cur:
            ev.append((t, slot(ch)))
            cur = ch
    x = rx - (2 - col) * 6 * rs
    A(f'<g transform="translate({q(x)} {ry}) scale({rs})" fill="{YELLOW}"><g clip-path="url(#win)"><g transform="translate({slot(rest)})">'
      + discrete("transform", ev, slot(rest), tag="animateTransform", extra=' type="translate"')
      + '<use href="#odo" xlink:href="#odo"/></g></g></g>')
# the order meter: how much of the field is strokes rather than static
bx0, bx1, by, bh = W - 28 - 212, W - 28, 50, 8
A(text("ORDER", bx0 - 6 * 2 * 6 + 4, by - 3, 2, DIM))
A(f'<rect x="{bx0}" y="{by}" width="{bx1 - bx0}" height="{bh}" fill="{MUTE}" opacity="0.15"/>')
seq = [(0.0, orders[0])] + [(t_assemble(k), orders[k]) for k in range(NF)] + [(D0, orders[-1])] \
    + [(t_dissolve(k), orders[k]) for k in range(NF - 2, -1, -1)] + [(TL, orders[0])]
A(f'<rect x="{bx0}" y="{by}" width="{q((bx1 - bx0) * orders[0])}" height="{bh}" fill="{YELLOW}">'
  f'<animate attributeName="width" dur="{TL}s" repeatCount="indefinite" calcMode="linear" '
  f'keyTimes="{";".join(qt(t / TL) for t, _ in seq)}" values="{";".join(q((bx1 - bx0) * v) for _, v in seq)}"/></rect>')

# the field
A(f'<g transform="translate({GX} {GY}) scale({CELL})">')
A(f'<rect width="{COLS}" height="{ROWS}" fill="url(#dots)"/>')
A('<g fill="none" stroke="url(#g)" stroke-width="0.86" stroke-linecap="square" transform="translate(0.43 0.43)">')
for k, grid in enumerate(frames):
    first, ev = frame_events(k)
    d = frame_path(grid)
    glow = (f'<path d="{d}" stroke-width="1.7" opacity="0.28"/>' if k == NF - 1 else "")   # the sentence glows while it holds
    A("<g>" + discrete("display", ev, first)
      + discrete("opacity", [(t, "1" if v == "inline" else "0") for t, v in ev], "1" if first == "inline" else "0")
      + glow + f'<path d="{d}"/></g>')
A('</g></g>')

# footer
A(text(f"THE FIRST FRAME IS THE LAST FRAME, {STEPS} STEPS EARLY", 28, 402, 2, DIM))
A(f'<rect x="0" y="{H - 4}" width="{W}" height="4" fill="{MUTE}" opacity="0.12"/>')
A(f'<rect x="0" y="{H - 4}" width="0" height="4" fill="{ORANGE}"><animate attributeName="width" dur="{TL}s" '
  f'repeatCount="indefinite" keyTimes="0;1" values="0;{W}"/></rect>')
A(f'<rect x="{q(W * t_assemble(NF - 1) / TL - 1)}" y="{H - 9}" width="2" height="9" fill="{PINK}"/>')
A(f'<rect x="{q(W * D0 / TL - 1)}" y="{H - 9}" width="2" height="9" fill="{PINK}"/>')
A('</svg>')
svg = "".join(out)


# ---------------------------------------------------------------- self-check: refuse to write a dead file
def selfcheck(svg):
    doc = xml.dom.minidom.parseString(svg)
    ids = {e.getAttribute("id") for e in doc.getElementsByTagName("*") if e.getAttribute("id")}
    for e in doc.getElementsByTagName("*"):
        assert e.tagName not in ("script", "filter", "foreignObject", "image", "style"), e.tagName
        for attr in ("href", "xlink:href"):
            if e.hasAttribute(attr):
                ref = e.getAttribute(attr)
                assert ref.startswith("#") and ref[1:] in ids, f"dangling {attr}={ref}"
        for attr in ("clip-path", "fill", "stroke"):
            v = e.getAttribute(attr)
            if v.startswith("url("):
                assert v[5:-1] in ids, f"dangling {attr}={v}"
    n = 0
    for tag in ("animate", "animateTransform"):
        for e in doc.getElementsByTagName(tag):
            vals = e.getAttribute("values").split(";")
            kts = [float(x) for x in e.getAttribute("keyTimes").split(";")]
            attr = e.getAttribute("attributeName")
            assert len(vals) == len(kts), f"{attr}: {len(vals)} values vs {len(kts)} keyTimes"
            assert kts[0] == 0 and kts[-1] == 1, f"{attr}: keyTimes must span 0..1"
            assert all(b >= a for a, b in zip(kts, kts[1:])), f"{attr}: keyTimes not monotonic"
            assert e.getAttribute("dur") == f"{TL}s"
            if not (attr == "width" and vals[0] == "0"):      # the playhead is a sawtooth
                assert vals[0] == vals[-1], f"{attr}: loop does not close ({vals[0]} -> {vals[-1]})"
            n += 1
    size = len(svg.encode("utf-8"))
    assert size < 400_000, f"{size} bytes"
    return n, size


n_tracks, size = selfcheck(svg)
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(svg)
print(f"wrote {OUT}  {size:,} bytes  ({n_tracks} animation tracks, {NF} frames, {TL:.2f} s loop)")
