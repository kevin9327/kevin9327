#!/usr/bin/env python3
"""
render_stairs.py -- REPRO STEPS: a staircase that ascends on every step and still closes on itself,
                    until the camera moves.

Emits assets/stairs.svg. Pure SMIL: no script, no filter, no font, no external reference, so it
plays inside the <img> GitHub uses for a profile README.

The object is real. Blocks walk a rectangular circuit -- a tread block per step, a square landing at
each corner -- every step up, and no two blocks intersect. The walk does NOT close in space: it ends
|g| treads away from where it began. But g is parallel to the view axis at (45 deg, 60 deg), so under
orthographic projection the end lands exactly on the beginning. That is asserted to machine
precision below, not drawn.

Orthographic projection is linear, so every block of a kind is the same projected polygon, merely
translated: the whole rotating solid is nine morphing face paths, instanced once per block. SVG has
no depth buffer and document order cannot animate, so the solid is emitted once per legal painter
order. At the magic angle the painter's order is the one the *loop* implies (the first block is
drawn in front of the last landing, as its next step would be); the instant the camera opens a
gap, the order becomes the true one and the illusion visibly breaks. The orders are switched at
the interpolated instant where the incoming one becomes legal.

Pure stdlib. Runs in about a second.
"""
import collections
import math
import os
import xml.dom.minidom

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "assets", "stairs.svg"))

# ---------------------------------------------------------------- parameters
LEGS = [(1, 0, 7), (0, 1, 7), (-1, 0, 3), (0, -1, 3)]   # (dir x, dir y, tread blocks); a square landing follows each
T = 1.0                                               # tread advance per step
PW = 3.0 * T                                          # flight width; landings are PW x PW
THETA0, PHI0 = math.radians(45.0), math.radians(60.0)  # the one angle from which the loop closes
THETA1, PHI1 = math.radians(82.0), math.radians(14.0)  # where the camera goes to break it
NPOSE = 24                                            # baked camera poses between the two
W, H = 1000, 460
BAND = (30, 14, 970, 392)                             # the object is fitted into this box at every pose

LAP, LAPS, CATCH, SWEEP, HOLD, BACK, SNAP = 2.20, 3, 0.22, 1.30, 0.60, 0.90, 0.18
TL = LAPS * LAP + CATCH + SWEEP + HOLD + BACK + SNAP
T_CATCH = LAPS * LAP
T_SWEEP = T_CATCH + CATCH
T_HOLD = T_SWEEP + SWEEP
T_BACK = T_HOLD + HOLD
T_SNAP = T_BACK + BACK

PINK, ORANGE, YELLOW, INK, MUTE = "#ec4899", "#f97316", "#facc15", "#0d1117", "#8b949e"
SEAM_PX = 8.0        # while the ends are closer than this on screen, draw the loop's order, not the truth


def hexlerp(a, b, s):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * s):02x}" for x, y in zip(ca, cb))


def ramp(s):
    """pink -> orange -> yellow -> orange -> pink around the loop: periodic, so the last block meets the
    first in the same colour and the eye can follow the stairs across the seam without a break"""
    t = 1 - abs(2 * (s % 1.0) - 1)
    return hexlerp(PINK, ORANGE, t * 2) if t < 0.5 else hexlerp(ORANGE, YELLOW, (t - 0.5) * 2)


# ---------------------------------------------------------------- geometry
def walk(h):
    """lay the blocks along the circuit with riser h; returns blocks, the comet's path, and where the
    path ends relative to where it began"""
    blocks, ridge, tread_idx = [], [], []

    def point(p):
        if not ridge or max(abs(p[k] - ridge[-1][k]) for k in range(3)) > 1e-9:
            ridge.append(p)
        return len(ridge) - 1

    x = y = z = 0.0
    for li, (dx, dy, n) in enumerate(LEGS):
        for _ in range(n):
            z += h
            i0 = point((x, y, z))                       # at the top of the riser, entering the tread
            blocks.append(dict(c=(x + 0.5 * dx, y + 0.5 * dy, z), kind="X" if dx else "Y"))
            x, y = x + dx, y + dy
            i1 = point((x, y, z))                       # leaving the tread
            point((x, y, z + h))                        # up the next riser
            tread_idx.append((i0, i1))
        ndx, ndy, _ = LEGS[(li + 1) % len(LEGS)]
        z += h
        i0 = point((x, y, z))
        cx, cy = x + PW / 2 * dx, y + PW / 2 * dy
        point((cx, cy, z))                              # across the landing, turning the corner
        blocks.append(dict(c=(cx, cy, z), kind="C"))
        x, y = cx + PW / 2 * ndx, cy + PW / 2 * ndy
        i1 = point((x, y, z))
        point((x, y, z + h))
        tread_idx.append((i0, i1))
    return blocks, ridge, tread_idx, (x, y, z)


_, _, _, g_plan = walk(1.0)
N = len(walk(1.0)[0])
assert abs(math.atan2(g_plan[1], g_plan[0]) - THETA0) < 1e-9, "the walk's plan displacement must point along the magic azimuth"
RISE = math.hypot(g_plan[0], g_plan[1]) * math.tan(PHI0)   # derived from the closure condition, never chosen
h = RISE / N                                                # riser
TH = 2.2 * h + 0.2                                          # block thickness: a flight reads solid from the side
blocks, ridge, tread_idx, g = walk(h)
SEAM = ridge[0]
END = (SEAM[0] + g[0], SEAM[1] + g[1], SEAM[2] + g[2])
assert max(abs(a - b) for a, b in zip(ridge[-1], END)) < 1e-9
SIZE = {"X": (T, PW), "Y": (PW, T), "C": (PW, PW)}


def basis(theta, phi):
    """view axis f (towards the camera), screen right r, screen up u"""
    f = (math.cos(phi) * math.cos(theta), math.cos(phi) * math.sin(theta), math.sin(phi))
    r = (math.sin(theta), -math.cos(theta), 0.0)
    u = (-math.cos(theta) * math.sin(phi), -math.sin(theta) * math.sin(phi), math.cos(phi))
    return f, r, u


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


f0, r0, u0 = basis(THETA0, PHI0)
cross = (g[1] * f0[2] - g[2] * f0[1], g[2] * f0[0] - g[0] * f0[2], g[0] * f0[1] - g[1] * f0[0])
PAR = math.sqrt(sum(c * c for c in cross))
GAP0 = (dot(g, r0), -dot(g, u0))
assert PAR < 1e-9 and abs(GAP0[0]) < 1e-9 and abs(GAP0[1]) < 1e-9, "the loop does not close at the magic angle"


def faces(kind):
    """local coordinates, block top-centre at the origin; the three faces the camera sees"""
    sx, sy = SIZE[kind]
    return {
        "top": [(-sx / 2, -sy / 2, 0), (sx / 2, -sy / 2, 0), (sx / 2, sy / 2, 0), (-sx / 2, sy / 2, 0)],
        "sx": [(sx / 2, -sy / 2, 0), (sx / 2, sy / 2, 0), (sx / 2, sy / 2, -TH), (sx / 2, -sy / 2, -TH)],
        "sy": [(-sx / 2, sy / 2, 0), (sx / 2, sy / 2, 0), (sx / 2, sy / 2, -TH), (-sx / 2, sy / 2, -TH)],
    }


def corners(b):
    sx, sy = SIZE[b["kind"]]
    cx, cy, cz = b["c"]
    return [(cx + ex * sx / 2, cy + ey * sy / 2, cz + ez) for ez in (0, -TH) for ex, ey in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def box(b, shift=(0, 0, 0)):
    sx, sy = SIZE[b["kind"]]
    cx, cy, cz = (b["c"][i] + shift[i] for i in range(3))
    return ((cx - sx / 2, cx + sx / 2), (cy - sy / 2, cy + sy / 2), (cz - TH, cz))


for a in range(N):   # the blocks touch; they never intersect, which is what makes a painter's order exist
    for b_ in range(a + 1, N):
        A, B = box(blocks[a]), box(blocks[b_])
        assert any(A[k][1] <= B[k][0] + 1e-9 or B[k][1] <= A[k][0] + 1e-9 for k in range(3)), f"blocks {a} and {b_} intersect"


# ---------------------------------------------------------------- camera
def ease(s):   # smootherstep: the sweep has a beat at both ends
    return s * s * s * (s * (s * 6 - 15) + 10)


poses = []
for k in range(NPOSE):
    s = ease(k / (NPOSE - 1))
    th, ph = THETA0 + (THETA1 - THETA0) * s, PHI0 + (PHI1 - PHI0) * s
    fv, rv, uv = basis(th, ph)
    pts = [(dot(p, rv), -dot(p, uv)) for b in blocks for p in corners(b)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    poses.append(dict(f=fv, r=rv, u=uv, bb=(min(xs), min(ys), max(xs), max(ys))))

bw, bh = BAND[2] - BAND[0], BAND[3] - BAND[1]
raw = [min(bw / (p["bb"][2] - p["bb"][0]), bh / (p["bb"][3] - p["bb"][1])) for p in poses]
for i, p in enumerate(poses):   # smooth the fit so the zoom does not jitter as the silhouette's corner changes
    lo, hi = max(0, i - 4), min(NPOSE, i + 5)
    p["s"] = min(raw[i], sum(raw[lo:hi]) / (hi - lo))
    x0, y0, x1, y1 = p["bb"]
    p["tx"] = (BAND[0] + BAND[2]) / 2 - p["s"] * (x0 + x1) / 2
    p["ty"] = (BAND[1] + BAND[3]) / 2 - p["s"] * (y0 + y1) / 2


def proj(p, pt):
    return (p["s"] * dot(pt, p["r"]) + p["tx"], -p["s"] * dot(pt, p["u"]) + p["ty"])


def proj0(p, pt):   # without the translation: the instanced prototype
    return (p["s"] * dot(pt, p["r"]), -p["s"] * dot(pt, p["u"]))


def lerp(a, b, s):
    return a + (b - a) * s


def q(v):
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


def qt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s or "0"


# ---------------------------------------------------------------- painter order
def hull(pts):
    pts = sorted(set(pts))

    def half(ps):
        o = []
        for p_ in ps:
            while len(o) >= 2 and (o[-1][0] - o[-2][0]) * (p_[1] - o[-2][1]) - (o[-1][1] - o[-2][1]) * (p_[0] - o[-2][0]) <= 0:
                o.pop()
            o.append(p_)
        return o
    return half(pts)[:-1] + half(pts[::-1])[:-1]


def overlap(A, B, eps=0.6):
    """true silhouette test, separating axis theorem on the two convex hulls"""
    for P in (A, B):
        for i in range(len(P)):
            x1, y1 = P[i]
            x2, y2 = P[(i + 1) % len(P)]
            nx, ny = -(y2 - y1), (x2 - x1)
            L = math.hypot(nx, ny)
            if L < 1e-9:
                continue
            nx, ny = nx / L, ny / L
            a = [nx * p[0] + ny * p[1] for p in A]
            b = [nx * p[0] + ny * p[1] for p in B]
            if min(a) > max(b) - eps or min(b) > max(a) - eps:
                return False
    return True


def nearer(a, b, seam):
    """which of two non-intersecting boxes is nearer the camera, by the plane that separates them. A
    separating plane gives the same answer at every pose of this sweep (every component of the view
    axis stays positive), so the painter's order only changes when silhouettes start or stop
    overlapping -- or at the seam. With `seam`, an early block is compared as if it stood one loop
    further along the walk: that is the order the closed loop implies, and it is what the eye must
    see at the magic angle."""
    K = 4
    A = box(blocks[a], g if (seam and a < K and b >= N - K) else (0, 0, 0))
    B = box(blocks[b], g if (seam and b < K and a >= N - K) else (0, 0, 0))
    verdicts = set()
    for k in range(3):
        if A[k][1] <= B[k][0] + 1e-9:
            verdicts.add(b)        # B lies on the +axis side, and the camera is on the + side of every axis
        elif B[k][1] <= A[k][0] + 1e-9:
            verdicts.add(a)
    if len(verdicts) != 1:        # not separated (impossible) or separated two ways (cannot overlap on screen)
        return None
    return verdicts.pop()


CORNERS = [[[proj(p, c) for c in corners(b)] for b in blocks] for p in poses]


def corners_at(s):
    k = min(int(s), NPOSE - 2)
    u = s - k
    if u < 1e-12:
        return CORNERS[k]
    return [[(lerp(a[0], b[0], u), lerp(a[1], b[1], u)) for a, b in zip(ca, cb)] for ca, cb in zip(CORNERS[k], CORNERS[k + 1])]


def gap_at_pose(s):
    k = min(int(s), NPOSE - 2)
    u = s - k
    S = [lerp(a, b, u) for a, b in zip(proj(poses[k], SEAM), proj(poses[k + 1], SEAM))]
    E = [lerp(a, b, u) for a, b in zip(proj(poses[k], END), proj(poses[k + 1], END))]
    return math.dist(S, E)


def constraints_at(s):
    """set of (a, b): block a must be drawn before block b, at fractional pose s. The browser
    interpolates the projected geometry linearly between baked poses, so the interpolated
    silhouettes are exactly what it draws."""
    corn = corners_at(s)
    seam = gap_at_pose(s) < SEAM_PX
    sil = [hull(c) for c in corn]
    bb = [(min(x for x, _ in c), min(y for _, y in c), max(x for x, _ in c), max(y for _, y in c)) for c in sil]
    E = set()
    for i in range(N):
        for j in range(i + 1, N):
            a, b = bb[i], bb[j]
            if min(a[2], b[2]) <= max(a[0], b[0]) or min(a[3], b[3]) <= max(a[1], b[1]):
                continue
            if not overlap(sil[i], sil[j]):
                continue
            n = nearer(i, j, seam)
            if n is not None:
                E.add((j, i) if n == i else (i, j))
    return E


def topo(E, key):
    gr = collections.defaultdict(set)
    indeg = collections.Counter()
    for a, b in E:
        if b not in gr[a]:
            gr[a].add(b)
            indeg[b] += 1
    ready = sorted([i for i in range(N) if indeg[i] == 0], key=key)
    out = []
    while ready:
        n = ready.pop(0)
        out.append(n)
        add = []
        for m in sorted(gr[n]):
            indeg[m] -= 1
            if indeg[m] == 0:
                add.append(m)
        ready = sorted(ready + add, key=key)
    return out if len(out) == N else None


def violations(order, E):
    rk = {b: k for k, b in enumerate(order)}
    return sum(1 for a, b in E if rk[a] > rk[b])


def depth_key(s):
    k = min(int(s), NPOSE - 2)
    u = s - k
    fa, fb = poses[k]["f"], poses[k + 1]["f"]
    return lambda i: lerp(dot(blocks[i]["c"], fa), dot(blocks[i]["c"], fb), u)


# painter order on a grid finer than the poses, because pairs start overlapping between poses too
SUB = 6
GRID = [k + j / SUB for k in range(NPOSE - 1) for j in range(SUB)] + [NPOSE - 1.0]
CONS = [constraints_at(s) for s in GRID]

passes = []          # (first grid index, last grid index, order)
k = 0
while k < len(GRID):
    acc, j, best = set(), k, None
    while j < len(GRID):
        o = topo(acc | CONS[j], key=depth_key(GRID[j]))
        if o is None:
            break
        acc |= CONS[j]
        best = o
        j += 1
    assert best is not None, f"no painter's order exists at grid pose {GRID[k]:.2f}: the occlusion graph has a cycle"
    passes.append((k, j - 1, best))
    k = j

# the switch between consecutive passes: the instant the incoming order becomes legal
switches = []        # fractional pose index at which pass p gives way to pass p+1
for p in range(len(passes) - 1):
    b = passes[p][1]
    s0, s1 = GRID[b], GRID[b + 1]
    out_o, in_o = passes[p][2], passes[p + 1][2]
    best, both = None, []
    for j in range(1, 25):
        u = j / 24
        E = constraints_at(lerp(s0, s1, u))
        vo, vi = violations(out_o, E), violations(in_o, E)
        if vo == 0 and vi == 0:
            both.append(u)
        if vi == 0 and (best is None or best[0] > 0):
            best = (0, u, vo, vi)
        elif best is None:
            best = (vo + vi, u, vo, vi)
    u_star = both[len(both) // 2] if both else best[1]
    switches.append(lerp(s0, s1, u_star))
    print(f"  pass {p} -> {p + 1} at pose {switches[-1]:.3f} (gap {gap_at_pose(switches[-1]):.1f} px): "
          + (f"both orders legal on u in [{both[0]:.2f}, {both[-1]:.2f}]" if both else
             f"switching the instant the incoming order becomes legal (outgoing breaks {best[2]} pairs there)"))
print(f"painter order: {len(passes)} passes over {len(GRID)} grid poses; switches at "
      + ", ".join(f"{s:.2f}" for s in switches))
for p, (a, b, order) in enumerate(passes):
    for kk in range(a, b + 1):
        assert violations(order, CONS[kk]) == 0, f"pass {p} is not legal at grid pose {kk}"

NORM = {"top": (0, 0, 1), "sx": (1, 0, 0), "sy": (0, 1, 0)}
mind = min(dot(NORM[k_], p["f"]) for k_ in NORM for p in poses)
assert mind > 0, f"a drawn face turns its back on the camera during the sweep ({mind:.3f})"


# ---------------------------------------------------------------- timeline
POSE_T_OUT = [T_SWEEP + SWEEP * k / (NPOSE - 1) for k in range(NPOSE)]
POSE_T_BACK = [T_BACK + BACK * (NPOSE - 1 - k) / (NPOSE - 1) for k in range(NPOSE)]


def t_out(s):
    return T_SWEEP + SWEEP * s / (NPOSE - 1)


def t_back(s):
    return T_BACK + BACK * (NPOSE - 1 - s) / (NPOSE - 1)


def track(by_pose):
    """values keyed by pose -> (values, keyTimes) over the whole loop: hold, out, hold, back, hold"""
    seq = [(0.0, by_pose[0])]
    seq += [(POSE_T_OUT[k], by_pose[k]) for k in range(NPOSE)]
    seq += [(POSE_T_BACK[k], by_pose[k]) for k in range(NPOSE - 1, -1, -1)]
    seq += [(TL, by_pose[0])]
    return ";".join(v for _, v in seq), ";".join(qt(t / TL) for t, _ in seq)


def anim(attr, by_pose, extra=""):
    v, kt = track(by_pose)
    return (f'<animate attributeName="{attr}" dur="{TL}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{kt}" values="{v}"{extra}/>')


def times(*ts):
    return ";".join(qt(t / TL) for t in ts)


def discrete(attr, events, first, tag="animate", extra=""):
    """events: list of (t, value); the value at t=0 is `first`, held until the first event"""
    vals, kts = [first], [0.0]
    for t, v in events:
        vals.append(v)
        kts.append(t)
    if kts[-1] < TL:
        vals.append(vals[-1])
        kts.append(TL)
    return (f'<{tag} attributeName="{attr}" dur="{TL}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{";".join(qt(t / TL) for t in kts)}" values="{";".join(vals)}"{extra}/>')


# ---------------------------------------------------------------- bitmap font (5x7), compiled to paths
FONT = {
    "A": ".###. #...# #...# ##### #...# #...# #...#",
    "B": "####. #...# #...# ####. #...# #...# ####.",
    "C": ".###. #...# #.... #.... #.... #...# .###.",
    "D": "####. #...# #...# #...# #...# #...# ####.",
    "E": "##### #.... #.... ####. #.... #.... #####",
    "F": "##### #.... #.... ####. #.... #.... #....",
    "G": ".###. #...# #.... #.### #...# #...# .####",
    "H": "#...# #...# #...# ##### #...# #...# #...#",
    "I": "##### ..#.. ..#.. ..#.. ..#.. ..#.. #####",
    "K": "#...# #..#. #.#.. ##... #.#.. #..#. #...#",
    "L": "#.... #.... #.... #.... #.... #.... #####",
    "M": "#...# ##.## #.#.# #.#.# #...# #...# #...#",
    "N": "#...# ##..# #.#.# #..## #...# #...# #...#",
    "O": ".###. #...# #...# #...# #...# #...# .###.",
    "P": "####. #...# #...# ####. #.... #.... #....",
    "R": "####. #...# #...# ####. #.#.. #..#. #...#",
    "S": ".#### #.... #.... .###. ....# ....# ####.",
    "T": "##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..",
    "U": "#...# #...# #...# #...# #...# #...# .###.",
    "V": "#...# #...# #...# #...# #...# .#.#. ..#..",
    "W": "#...# #...# #...# #.#.# #.#.# ##.## #...#",
    "X": "#...# #...# .#.#. ..#.. .#.#. #...# #...#",
    "Y": "#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..",
    "0": ".###. #...# #..## #.#.# ##..# #...# .###.",
    "1": "..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.",
    "2": ".###. #...# ....# ...#. ..#.. .#... #####",
    "3": "##### ...#. ..#.. ...#. ....# #...# .###.",
    "4": "...#. ..##. .#.#. #..#. ##### ...#. ...#.",
    "5": "##### #.... ####. ....# ....# #...# .###.",
    "6": "..##. .#... #.... ####. #...# #...# .###.",
    "7": "##### ....# ...#. ..#.. .#... .#... .#...",
    "8": ".###. #...# #...# .###. #...# #...# .###.",
    "9": ".###. #...# #...# .#### ....# ...#. .##..",
    "(": "..#.. .#... #.... #.... #.... .#... ..#..",
    ")": "..#.. ...#. ....# ....# ....# ...#. ..#..",
    ".": "..... ..... ..... ..... ..... .##.. .##..",
    "-": "..... ..... ..... ##### ..... ..... .....",
    ":": "..... .##.. .##.. ..... .##.. .##.. .....",
    "^": "..#.. ..#.. .#.#. .#.#. #...# #...# #####",   # delta
}
GID = {c: (f"c{c}" if c.isalnum() else {"(": "clp", ")": "crp", ".": "cdot", "-": "cdash", ":": "ccol", "^": "cdel"}[c])
       for c in FONT}


def glyph_path(rows):
    rows = rows.split()
    d = []
    for x in range(5):
        y = 0
        while y < 7:
            if rows[y][x] == "#":
                y0 = y
                while y < 7 and rows[y][x] == "#":
                    y += 1
                d.append(f"M{x} {y0}h1v{y - y0}h-1z")   # merge vertical runs: a stem is one subpath
            else:
                y += 1
    return "".join(d)


ADV = 6   # 5 columns + 1 gap, in glyph units


def text(s, x, y, scale, fill, extra="", anchor="start"):
    """one <use> per glyph; anchor start|middle|end; (x, y) is the top-left / top-centre / top-right"""
    width = (len(s) * ADV - 1) * scale
    if anchor == "middle":
        x -= width / 2
    elif anchor == "end":
        x -= width
    out = [f'<g transform="translate({q(x)} {q(y)}) scale({scale})" fill="{fill}"{extra}>']
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        out.append(f'<use href="#{GID[ch]}" xlink:href="#{GID[ch]}" x="{i * ADV}"/>')
    out.append("</g>")
    return "".join(out)


# ---------------------------------------------------------------- bake
P0 = poses[0]
ridge_scr = [proj(P0, p) for p in ridge]
RIDGE_D = "M" + "L".join(f"{q(x)} {q(y)}" for x, y in ridge_scr)
ARC = [0.0]
for i in range(len(ridge_scr) - 1):
    ARC.append(ARC[-1] + math.dist(ridge_scr[i], ridge_scr[i + 1]))
RIDGE_LEN = ARC[-1]
seam_gap = math.dist(ridge_scr[0], ridge_scr[-1])
assert seam_gap < 1e-6, f"ridge does not close on screen ({seam_gap:.2e} px)"

face_vals = {kind: {name: [("M" + " ".join(f"{q(x)} {q(y)}" for x, y in [proj0(p, v) for v in verts]) + "Z") for p in poses]
                    for name, verts in faces(kind).items()} for kind in SIZE}
block_vals = [[f"{q(proj(p, b['c'])[0])} {q(proj(p, b['c'])[1])}" for p in poses] for b in blocks]
seam_vals = [f"{q(proj(p, SEAM)[0])} {q(proj(p, SEAM)[1])}" for p in poses]
end_vals = [f"{q(proj(p, END)[0])} {q(proj(p, END)[1])}" for p in poses]
link_vals = [f"M{q(proj(p, SEAM)[0])} {q(proj(p, SEAM)[1])}L{q(proj(p, END)[0])} {q(proj(p, END)[1])}" for p in poses]
gap_px = [math.dist(proj(p, SEAM), proj(p, END)) for p in poses]
print(f"blocks N={N} ({sum(1 for b in blocks if b['kind'] != 'C')} treads + 4 landings)  riser h={h:.4f}  "
      f"thickness {TH:.3f}  |g|={math.hypot(*g):.4f}")
print(f"|g x f0| = {PAR:.3e}   screen gap at magic angle = ({GAP0[0]:.2e}, {GAP0[1]:.2e})   ridge seam = {seam_gap:.2e} px")
print(f"projected gap at the reveal pose = {gap_px[-1]:.1f} px   ridge length = {RIDGE_LEN:.1f} px")
print(f"screen riser = {h * P0['s']:.1f} px  tread = {T * P0['s']:.1f} px  flight width = {PW * P0['s']:.0f} px  (at {W} wide)")


def pose_at(t):
    if t <= T_SWEEP:
        return 0.0
    if t <= T_HOLD:
        return (t - T_SWEEP) / SWEEP * (NPOSE - 1)
    if t <= T_BACK:
        return NPOSE - 1.0
    if t <= T_SNAP:
        return (NPOSE - 1) * (1 - (t - T_BACK) / BACK)
    return 0.0


def gap_at(t):
    return gap_at_pose(pose_at(t))


# ---------------------------------------------------------------- emit
out = []
A = out.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
  f'viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
A('<title>REPRO STEPS</title>')
A(f'<desc>A staircase of {N} blocks that ascends on every step and still closes on itself. '
  f'The walk really ends {math.hypot(*g):.2f} treads from where it started, along the view axis, so it projects '
  f'onto its own beginning; then the camera moves and the loop comes apart. Pure SMIL, generated by '
  f'scripts/render_stairs.py.</desc>')
A('<defs>')
# the instanced faces: the entire shape of every block at every pose lives in these nine paths
for kind in SIZE:
    for name in ("sy", "sx", "top"):
        A(f'<path id="f_{kind}_{name}" fill="currentColor" stroke="{INK}" stroke-width="0.8" stroke-linejoin="round">'
          f'{anim("d", face_vals[kind][name])}</path>')
    A(f'<g id="blk{kind}">'
      f'<use href="#f_{kind}_sy" xlink:href="#f_{kind}_sy"/><use href="#f_{kind}_sy" xlink:href="#f_{kind}_sy" fill="{INK}" opacity="0.62"/>'
      f'<use href="#f_{kind}_sx" xlink:href="#f_{kind}_sx"/><use href="#f_{kind}_sx" xlink:href="#f_{kind}_sx" fill="{INK}" opacity="0.44"/>'
      f'<use href="#f_{kind}_top" xlink:href="#f_{kind}_top"/>'
      f'</g>')
# one placed block each: colour by walk order, position baked per pose, a tread that lights up as the
# comet crosses it. Placed once, painted once per pass.
for i, b in enumerate(blocks):
    v, kt = track(block_vals[i])
    ta, tb = tread_idx[i]
    mid = (ARC[ta] + ARC[tb]) / 2 / RIDGE_LEN * LAP          # when the comet is on this tread, per lap
    kts, vals = [0.0], ["0"]
    for lap in range(LAPS):
        t = mid + lap * LAP
        kts += [max(0.001, t - 0.06), t, t + 0.32]           # block 0 lights up at the very start of the loop
        vals += ["0", "0.45", "0"]
    kts.append(TL)
    vals.append("0")
    A(f'<g id="p{i}"><g><animateTransform attributeName="transform" type="translate" dur="{TL}s" repeatCount="indefinite" '
      f'calcMode="linear" keyTimes="{kt}" values="{v}"/>'
      f'<use href="#blk{b["kind"]}" xlink:href="#blk{b["kind"]}" color="{ramp(i / N)}"/>'
      f'<use href="#f_{b["kind"]}_top" xlink:href="#f_{b["kind"]}_top" fill="#ffffff" stroke="none" opacity="0">'
      f'<animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" keyTimes="{";".join(qt(t / TL) for t in kts)}" '
      f'values="{";".join(vals)}"/></use></g></g>')
A(f'<path id="ridge" fill="none" d="{RIDGE_D}"/>')
for ch, rows in FONT.items():
    A(f'<path id="{GID[ch]}" d="{glyph_path(rows)}"/>')
A('<g id="odo">' + "".join(f'<use href="#c{d}" xlink:href="#c{d}" y="{8 * d}"/>' for d in range(10)) + '</g>')
A('<clipPath id="win"><rect x="-0.5" y="-0.5" width="6" height="8"/></clipPath>')
A('<path id="dia" d="M0 -7L7 0L0 7L-7 0Z"/>')
A('</defs>')

A(f'<rect width="{W}" height="{H}" fill="{INK}"/>')

# under-glow: one soft stroke of the ridge, beneath the solid, gone while the loop is open
vis_kt = times(0, T_SWEEP, T_SWEEP + 0.15, T_SNAP, T_SNAP + 0.10, TL)
A(f'<use href="#ridge" xlink:href="#ridge" stroke="{ORANGE}" stroke-width="22" stroke-linejoin="round" '
  f'stroke-linecap="round" opacity="0.12">'
  f'<animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" keyTimes="{vis_kt}" values="0.12;0.12;0;0;0.12;0.12"/></use>')

# the solid, once per painter order; a hidden pass is never rasterised
for p, (a, b, order) in enumerate(passes):
    ev = []
    if p == 0:
        first = "inline"
        if switches:
            ev = [(t_out(switches[0]), "none"), (t_back(switches[0]), "inline")]
    else:
        first = "none"
        ev = [(t_out(switches[p - 1]), "inline")]
        if p < len(passes) - 1:
            ev += [(t_out(switches[p]), "none"), (t_back(switches[p]), "inline")]
        ev += [(t_back(switches[p - 1]), "none")]
    A("<g>" + discrete("display", ev, first)
      + discrete("opacity", [(t, "1" if v == "inline" else "0") for t, v in ev], "1" if first == "inline" else "0")
      + "".join(f'<use href="#p{i}" xlink:href="#p{i}"/>' for i in order) + "</g>")

# the path itself, one unbroken line around the whole loop, so the eye can trace that it never ends
A(f'<path d="{RIDGE_D}" fill="none" stroke="#fde68a" stroke-width="1.6" stroke-linejoin="round" opacity="0.32">'
  f'<animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" keyTimes="{vis_kt}" values="0.32;0.32;0;0;0.32;0.32"/></path>')
# the comet: a dash running the ridge, lap after lap, then parked on the seam until the loop is whole again
L = RIDGE_LEN
for width, dash, back, col, op in ((13, 230, 204, ORANGE, 0.2), (7, 84, 58, YELLOW, 0.55), (4.4, 26, 0, "#fff7cc", 1)):
    A(f'<path d="{RIDGE_D}" fill="none" stroke="{col}" stroke-width="{width}" stroke-linecap="round" '
      f'stroke-linejoin="round" opacity="{op}" stroke-dasharray="{q(dash)} {q(L - dash)}">'
      f'<animate attributeName="stroke-dashoffset" dur="{TL}s" repeatCount="indefinite" '
      f'keyTimes="{times(0, T_CATCH, TL)}" values="{q(back)};{q(back - LAPS * L)};{q(back - LAPS * L)}"/>'
      f'<animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" keyTimes="{vis_kt}" '
      f'values="{op};{op};0;0;{op};{op}"/></path>')
# the snap: the whole ridge flashes white on the exact frame the loop closes again
A(f'<path d="{RIDGE_D}" fill="none" stroke="#ffffff" stroke-width="3" stroke-linejoin="round" opacity="0">'
  f'<animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" '
  f'keyTimes="{times(0, T_SNAP, T_SNAP + 0.06, T_SNAP + 0.14, TL)}" values="0;0;1;0;0"/></path>')
# the catch: a pulse out of the seam when the comet stops
sx0, sy0 = ridge_scr[0]
A(f'<circle cx="{q(sx0)}" cy="{q(sy0)}" r="6" fill="none" stroke="{PINK}" stroke-width="2.5" opacity="0">'
  f'<animate attributeName="r" dur="{TL}s" repeatCount="indefinite" keyTimes="{times(0, T_CATCH, T_SWEEP, TL)}" values="6;6;30;6"/>'
  f'<animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" keyTimes="{times(0, T_CATCH, T_CATCH, T_SWEEP, TL)}" values="0;0;1;0;0"/>'
  f'</circle>')

# the caliper: the two ends of the walk, and the distance between them
A(f'<path fill="none" stroke="{MUTE}" stroke-width="1.5" stroke-dasharray="5 5">{anim("d", link_vals)}</path>')
for vals, col in ((end_vals, YELLOW), (seam_vals, PINK)):
    v, kt = track(vals)
    A(f'<use href="#dia" xlink:href="#dia" fill="{col}"><animateTransform attributeName="transform" type="translate" '
      f'dur="{TL}s" repeatCount="indefinite" calcMode="linear" keyTimes="{kt}" values="{v}"/></use>')

# title, readout, captions
A(text("REPRO STEPS", 28, 22, 3, MUTE))
A(text(f"{N} BLOCKS  EVERY STEP UP", 28, 52, 2, "#484f58"))
# odometer: five columns, each a clipped stack of ten digits stepped by a discrete translate
rx, ry, rs = W - 28, 22, 3
A(text("^", rx - 9 * ADV * rs, ry, rs, YELLOW))
A(text("PX", rx - 2 * ADV * rs + rs, ry, rs, MUTE))
samples = [T_SWEEP + i / 60 for i in range(int((T_SNAP - T_SWEEP) * 60) + 1)]
for col in range(5):
    seq = []
    for t in samples:
        s = f"{gap_at(t):5.1f}"
        seq.append((t, s[col]))
    if col == 3:
        A(text(".", rx - (8 - col) * ADV * rs, ry, rs, MUTE))
        continue
    slot = lambda ch: "0 -80" if ch == " " else f"0 {-8 * int(ch)}"
    rest = f"{gap_at(0):5.1f}"[col]
    ev = []
    cur = rest
    for t, ch in seq:
        if ch != cur:
            ev.append((t, slot(ch)))
            cur = ch
    ev.append((T_SNAP, slot(rest)))
    ev = [e for i, e in enumerate(ev) if i == 0 or e[1] != ev[i - 1][1]]
    x = rx - (8 - col) * ADV * rs
    A(f'<g transform="translate({q(x)} {ry}) scale({rs})" fill="{YELLOW}"><g clip-path="url(#win)"><g transform="translate({slot(rest)})">'
      + discrete("transform", ev, slot(rest), tag="animateTransform", extra=' type="translate"')
      + '<use href="#odo" xlink:href="#odo"/></g></g></g>')

capA = "WHILE (TRUE)"
capB = "THE LOOP ONLY CLOSES FROM ONE ANGLE"
A(text(capA, W / 2, 404, 4, MUTE, anchor="middle",
       extra=f'><animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" '
             f'keyTimes="{times(0, T_SWEEP + 0.35, T_SWEEP + 0.65, T_SNAP, T_SNAP + 0.12, TL)}" values="1;1;0;0;1;1"/'))
A(text(capB, W / 2, 407, 3.2, PINK, anchor="middle",
       extra=f' opacity="0"><animate attributeName="opacity" dur="{TL}s" repeatCount="indefinite" '
             f'keyTimes="{times(0, T_SWEEP + 0.5, T_SWEEP + 0.8, T_BACK + 0.5, T_SNAP, TL)}" values="0;0;1;1;0;0"/'))

# the hairline: where you are in the loop, and where the turn is
A(f'<rect x="0" y="{H - 4}" width="{W}" height="4" fill="{MUTE}" opacity="0.12"/>')
A(f'<rect x="0" y="{H - 4}" width="0" height="4" fill="{ORANGE}"><animate attributeName="width" dur="{TL}s" '
  f'repeatCount="indefinite" keyTimes="0;1" values="0;{W}"/></rect>')
A(f'<rect x="{q(W * T_CATCH / TL - 1)}" y="{H - 9}" width="2" height="9" fill="{PINK}"/>')
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
        if e.hasAttribute("clip-path"):
            assert e.getAttribute("clip-path")[5:-1] in ids
    n = 0
    for tag in ("animate", "animateTransform"):
        for e in doc.getElementsByTagName(tag):
            vals = e.getAttribute("values").split(";")
            kts = [float(x) for x in e.getAttribute("keyTimes").split(";")]
            attr = e.getAttribute("attributeName")
            assert len(vals) == len(kts), f"{attr}: {len(vals)} values vs {len(kts)} keyTimes"
            assert kts[0] == 0 and kts[-1] == 1, f"{attr}: keyTimes must span 0..1 ({kts[0]}..{kts[-1]})"
            assert all(b >= a for a, b in zip(kts, kts[1:])), f"{attr}: keyTimes not monotonic"
            assert e.getAttribute("dur") == f"{TL}s", f"{attr}: every track shares one clock"
            if attr not in ("width", "stroke-dashoffset"):   # the playhead is a sawtooth; the comet is periodic in L
                assert vals[0] == vals[-1], f"{attr}: loop does not close ({vals[0]} -> {vals[-1]})"
            n += 1
    size = len(svg.encode("utf-8"))
    assert size < 400_000, f"{size} bytes"
    return n, size


n_tracks, size = selfcheck(svg)
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(svg)
print(f"wrote {OUT}  {size:,} bytes  ({n_tracks} animation tracks, {NPOSE} poses, {N} blocks, {len(passes)} passes, {TL:.2f} s loop)")
