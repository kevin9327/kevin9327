#!/usr/bin/env python3
"""
render_fourier.py -- ONE LINE, N CIRCLES: a machine of nested circles draws a beetle in one stroke.

Emits assets/fourier.svg. Pure SMIL: no script, no filter, no font, no external reference, so it
plays inside the <img> GitHub uses for a profile README.

The beetle is one closed curve, drawn in a single stroke (legs, antennae and grooves are thin
out-and-back loops off the outline). Its discrete Fourier transform gives N complex coefficients;
each one is a circle: radius |c|, starting angle arg(c), and it turns exactly n whole times per
lap. Chain them end to end and the tip of the last circle traces the beetle. Nothing is baked per
frame: every circle is one <animateTransform type="rotate"> and the browser composes them. The
trace is the same curve, revealed by stroke-dashoffset in step with the pen.

Pure stdlib (PIL only for --preview). Runs in about a second.
"""
import cmath
import math
import os
import sys
import xml.dom.minidom

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pixelfont import defs as font_defs, text   # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, "..", "assets", "fourier.svg"))

# ---------------------------------------------------------------- parameters
K = 180                       # harmonics per side: 2K circles
M = 2048                      # samples along the curve
LAP = 9.0                     # seconds per lap of the pen; the loop is two laps
TL = 2 * LAP
W, H = 1000, 460
CX, CY, SCALE = 500, 232, 0.86   # where the beetle sits, and how big
PINK, ORANGE, YELLOW, INK, MUTE, DIM = "#ec4899", "#f97316", "#facc15", "#0d1117", "#8b949e", "#484f58"


# ---------------------------------------------------------------- the beetle, as one stroke
def bez(p0, p1, p2, p3, n=48):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def loop(pts, w):
    """a thin out-and-back loop along a polyline: out on one side, back on the other"""
    def offset(side):
        o = []
        for i, p in enumerate(pts):
            a = pts[max(i - 1, 0)]
            b = pts[min(i + 1, len(pts) - 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1
            nx, ny = -dy / L * side * w / 2, dx / L * side * w / 2
            o.append((p[0] + nx, p[1] + ny))
        return o
    out = offset(1)
    back = offset(-1)[::-1]
    return out + back[1:]


def smooth(pts, n=6):
    """resample a polyline through `pts` with n points per segment (piecewise linear)"""
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        for i in range(1, n + 1):
            t = i / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def mirror(pts):
    return [(-x, y) for x, y in pts]


def leg(root, knee, tip, w=5):
    return loop(smooth([root, knee, tip], 8), w)


def nearest(poly, y):
    return min(range(len(poly)), key=lambda i: abs(poly[i][1] - y))


def beetle():
    """returns the closed single-stroke polyline of a beetle, tail first, in a ~330 x 400 box"""
    # the left half, tail to head; the right half is its mirror, head to tail
    edge = bez((0, 150), (-105, 125), (-112, -45), (-42, -60), 140)         # left elytron, tail -> pronotum
    legs = {70: ((-70, 70), (-128, 122), (-150, 170)),                       # hind: back and down
            0: ((-84, 0), (-148, -12), (-172, 30)),                          # middle: straight out
            -66: ((-46, -66), (-104, -112), (-128, -66))}                    # front: forward and out
    left = []
    for i, p in enumerate(edge):
        left.append(p)
        for y, (root, knee, tip) in legs.items():
            if i == nearest(edge, y):
                left += leg(p, knee, tip)[1:] + [p]
    left += bez((-42, -60), (-54, -84), (-46, -104), (-34, -108), 24)[1:]    # pronotum, left edge
    head = bez((-34, -108), (-32, -130), (-16, -144), (0, -146), 30)         # head, left half
    for i, p in enumerate(head):
        left.append(p)
        if i == 12:                                                          # antenna
            left += loop(smooth([p, (-48, -160), (-78, -192), (-98, -196)], 8), 4)[1:] + [p]
        if i == 24:                                                          # mandible
            left += loop(smooth([p, (-16, -162), (-24, -176)], 6), 4)[1:] + [p]
    right = mirror(left)[::-1]
    pts = left + right[1:]
    # from the tail: the seam and two grooves, out and back
    seam = loop(smooth([(0, 150), (0, 40), (0, -58)], 10), 3)
    grooveL = loop(smooth([(0, 150), (-30, 110), (-38, 20), (-28, -48)], 10), 3)
    grooveR = mirror(grooveL)
    pts = pts + grooveL[1:] + seam[1:] + grooveR[1:]
    if pts[-1] != pts[0]:
        pts.append(pts[0])
    return pts


def resample(pts, m):
    """m points, evenly spaced by arc length, around the closed polyline"""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(seg)
    out, j, acc = [], 0, 0.0
    for i in range(m):
        s = total * i / m
        while j < len(seg) - 1 and acc + seg[j] < s:
            acc += seg[j]
            j += 1
        t = (s - acc) / seg[j] if seg[j] else 0
        a, b = pts[j], pts[j + 1]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out, total


design = beetle()
samples, design_len = resample(design, M)
z = [complex(CX + SCALE * x, CY + SCALE * y) for x, y in samples]

if "--preview" in sys.argv:
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(im)
    d.line([(p.real, p.imag) for p in z] + [(z[0].real, z[0].imag)], fill=(249, 115, 22), width=2)
    p = os.path.join(HERE, "..", "..", "poc", "beetle_design.png")
    im.save(p)
    print("preview", p)

# ---------------------------------------------------------------- the Fourier machine
coef = {}
for n in range(-K, K + 1):
    coef[n] = sum(z[k] * cmath.exp(-2j * math.pi * n * k / M) for k in range(M)) / M
origin = coef.pop(0)
links = sorted(coef.items(), key=lambda kv: -abs(kv[1]))          # biggest circle first
recon = [origin + sum(c * cmath.exp(2j * math.pi * n * k / M) for n, c in links) for k in range(M)]
err = max(abs(a - b) for a, b in zip(recon, z))
print(f"{2 * K} circles, {M} samples, largest radius {abs(links[0][1]):.1f} px, smallest {abs(links[-1][1]):.3f} px, "
      f"max reconstruction error {err:.2f} px")

# the pen path: the reconstruction itself, so the trace and the pen agree to the last term
path_pts = [(p.real, p.imag) for p in recon]
arc = [0.0]
for a, b in zip(path_pts, path_pts[1:] + path_pts[:1]):
    arc.append(arc[-1] + math.dist(a, b))
L = arc[-1]                                                        # closed length


def q(v):
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


def qt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s or "0"


def times(*ts):
    return ";".join(qt(t / TL) for t in ts)


PATH_D = "M" + "L".join(f"{q(x)} {q(y)}" for x, y in path_pts) + "Z"

# ---------------------------------------------------------------- emit
out = []
A = out.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
A('<title>ONE LINE, MANY CIRCLES</title>')
A(f'<desc>{2 * K} circles, each turning a whole number of times per lap, chained end to end. The tip of the last '
  f'one draws a beetle in a single stroke: the circles are the Fourier coefficients of the outline. Every '
  f'circle is one SMIL rotation; nothing is stored per frame. Generated by scripts/render_fourier.py.</desc>')
A('<defs>')
A(f'<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="{CX - 200}" y1="0" x2="{CX + 200}" y2="0">'
  f'<stop offset="0" stop-color="{PINK}"/><stop offset="0.5" stop-color="{ORANGE}"/><stop offset="1" stop-color="{YELLOW}"/></linearGradient>')
A(f'<linearGradient id="gf" gradientUnits="userSpaceOnUse" x1="0" y1="{CY - 180}" x2="0" y2="{CY + 180}">'
  f'<stop offset="0" stop-color="{YELLOW}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>')
A(f'<path id="trace" d="{PATH_D}" fill="none"/>')
A(font_defs())
A('<g id="odo">' + "".join(f'<use href="#c{d}" xlink:href="#c{d}" y="{8 * d}"/>' for d in range(10)) + '</g>')
A('<clipPath id="win"><rect x="-0.5" y="-0.5" width="6" height="8"/></clipPath>')
A('</defs>')
A(f'<rect width="{W}" height="{H}" fill="{INK}"/>')

# the finished beetle: solid and glowing during the second lap
fill_kt = times(0, LAP, LAP + 0.9, TL - 0.7, TL)
A(f'<use href="#trace" xlink:href="#trace" fill="url(#gf)" opacity="0">'
  f'<animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" keyTimes="{fill_kt}" values="0;0;0.28;0.28;0"/></use>')
A(f'<use href="#trace" xlink:href="#trace" stroke="url(#g)" stroke-width="14" stroke-linejoin="round" opacity="0">'
  f'<animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" keyTimes="{fill_kt}" values="0;0;0.22;0.22;0"/></use>')

# the trace: revealed exactly as far as the pen has travelled, then held through the second lap
D = 4                                                              # dash keyframes every D samples
reveal_kt = ";".join(qt(k / M * LAP / TL) for k in range(0, M, D)) + f";{qt(LAP / TL)};1"
reveal_v = ";".join(q(L - arc[k]) for k in range(0, M, D)) + ";0;0"
for width, op in ((7, 0.22), (2.2, 1)):
    A(f'<use href="#trace" xlink:href="#trace" stroke="url(#g)" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round" '
      f'opacity="{op}" stroke-dasharray="{q(L)} {q(L)}">'
      f'<animate attributeName="stroke-dashoffset" dur="{TL}s" repeatCount="indefinite" calcMode="linear" keyTimes="{reveal_kt}" values="{reveal_v}"/>'
      f'<animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" keyTimes="{times(0, TL - 0.6, TL)}" values="{op};{op};0"/></use>')
# the comet on the pen, both laps
comet_kt = ";".join(qt(k / M * LAP / TL) for k in range(0, M, D)) + ";" + ";".join(qt((LAP + k / M * LAP) / TL) for k in range(0, M, D)) + ";1"
comet_v = ";".join(q(46 - arc[k]) for k in range(0, M, D)) + ";" + ";".join(q(46 - arc[k]) for k in range(0, M, D)) + f";{q(46 - L)}"
A(f'<use href="#trace" xlink:href="#trace" stroke="#fff7cc" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" '
  f'opacity="0.9" stroke-dasharray="46 {q(L - 46)}">'
  f'<animate attributeName="stroke-dashoffset" dur="{TL}s" repeatCount="indefinite" calcMode="linear" keyTimes="{comet_kt}" values="{comet_v}"/></use>')

# the machine: nested rotations, biggest circle first, each link turning at the difference frequency
arms_kt = times(0, LAP, LAP + 0.9, TL - 0.7, TL)
A(f'<g transform="translate({q(origin.real)} {q(origin.imag)})" fill="none" stroke-linecap="round">'
  f'<animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" keyTimes="{arms_kt}" values="1;1;0.3;0.3;1"/>')
prev_f, prev_phi, depth = 0, 0.0, 0
for n, c in links:
    r, phi = abs(c), math.degrees(cmath.phase(c))
    a0 = phi - prev_phi
    a1 = a0 + 360 * (n - prev_f) * (TL / LAP)
    A(f'<g><animateTransform attributeName="transform" type="rotate" dur="{TL}s" repeatCount="indefinite" '
      f'calcMode="linear" keyTimes="0;1" values="{q(a0)};{q(a1)}"/>')
    if r >= 0.9:
        A(f'<circle r="{q(r)}" stroke="{MUTE}" stroke-width="0.8" opacity="{0.55 if r > 8 else 0.35}"/>'
          f'<line x2="{q(r)}" stroke="{YELLOW if r > 8 else MUTE}" stroke-width="{1.2 if r > 8 else 0.8}" opacity="0.6"/>')
    A(f'<g transform="translate({q(r)} 0)">')
    prev_f, prev_phi, depth = n, phi, depth + 1
# the pen
A(f'<circle r="9" fill="{YELLOW}" opacity="0.35"/><circle r="3.6" fill="#ffffff"/>')
A("</g></g>" * depth + "</g>")

# header and readouts
A(text(f"ONE LINE, {2 * K} CIRCLES", 28, 22, 3, MUTE))
A(text("A BUG AS A FOURIER SERIES  EACH CIRCLE TURNS A WHOLE NUMBER OF TIMES PER LAP", 28, 50, 2, DIM))
rx, ry, rs = W - 28, 20, 3
A(text("DRAWN", rx - 10 * 6 * rs, ry, rs, DIM))
A(text("%", rx - 1 * 6 * rs + rs, ry, rs, DIM))
# percentage odometer, three columns, counting the arc length drawn
samples_t = [i * LAP / 200 for i in range(201)]
for col in range(3):
    seq = []
    for t in samples_t:
        k = min(int(t / LAP * M), M - 1)
        seq.append((t, f"{round(100 * arc[k] / L):3d}"[col]))
    slot = lambda ch: "0 -80" if ch == " " else f"0 {-8 * int(ch)}"
    rest = f"{0:3d}"[col]
    ev, cur = [], rest
    for t, ch in seq:
        if ch != cur:
            ev.append((t, slot(ch)))
            cur = ch
    ev.append((LAP, slot(f"{100:3d}"[col])))
    ev.append((TL - 0.05, slot(rest)))
    ev = [e for i, e in enumerate(ev) if i == 0 or e[1] != ev[i - 1][1]]
    vals, kts = [slot(rest)], [0.0]
    for t, v in ev:
        vals.append(v)
        kts.append(t)
    vals.append(vals[-1])
    kts.append(TL)
    x = rx - (5 - col) * 6 * rs
    A(f'<g transform="translate({q(x)} {ry}) scale({rs})" fill="{YELLOW}"><g clip-path="url(#win)"><g transform="translate({slot(rest)})">'
      f'<animateTransform attributeName="transform" type="translate" dur="{TL}s" repeatCount="indefinite" calcMode="discrete" '
      f'keyTimes="{";".join(qt(t / TL) for t in kts)}" values="{";".join(vals)}"/>'
      f'<use href="#odo" xlink:href="#odo"/></g></g></g>')

# captions
capA, capB = f"IT TAKES {2 * K} CIRCLES TO DRAW A BUG", "AND ONE DIFF TO FIX IT"
A(text(capA, W / 2, 418, 2.6, MUTE, anchor="middle",
       extra=f'><animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" '
             f'keyTimes="{times(0, LAP, LAP + 0.5, TL - 0.6, TL)}" values="1;1;0;0;1"/'))
A(text(capB, W / 2, 418, 2.6, PINK, anchor="middle",
       extra=f' opacity="0"><animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" '
             f'keyTimes="{times(0, LAP + 0.5, LAP + 1.0, TL - 0.8, TL - 0.3, TL)}" values="0;0;1;1;0;0"/'))

# the hairline
A(f'<rect x="0" y="{H - 4}" width="{W}" height="4" fill="{MUTE}" opacity="0.12"/>')
A(f'<rect x="0" y="{H - 4}" width="0" height="4" fill="{ORANGE}"><animate attributeName="width" dur="{TL}s" '
  f'repeatCount="indefinite" keyTimes="0;1" values="0;{W}"/></rect>')
A(f'<rect x="{q(W * LAP / TL - 1)}" y="{H - 9}" width="2" height="9" fill="{PINK}"/>')
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
            if attr == "transform" and e.getAttribute("type") == "rotate":
                a, b = float(vals[0]), float(vals[-1])
                assert abs((b - a) / 360 - round((b - a) / 360)) < 1e-6, "a circle must turn whole times per loop"
            elif attr not in ("width", "stroke-dashoffset") and not (attr == "opacity" and e.parentNode.getAttribute("stroke-dasharray")):
                assert vals[0] == vals[-1], f"{attr}: loop does not close ({vals[0]} -> {vals[-1]})"
            n += 1
    size = len(svg.encode("utf-8"))
    assert size < 400_000, f"{size} bytes"
    return n, size


n_tracks, size = selfcheck(svg)
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(svg)
print(f"wrote {OUT}  {size:,} bytes  ({n_tracks} animation tracks, {2 * K} circles, {TL:.1f} s loop, path {L:.0f} px)")
