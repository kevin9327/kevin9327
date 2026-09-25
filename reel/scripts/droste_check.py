"""QA gates for "535, All the Way Down" (the Droste banner). Module M5.

    python scripts/droste_check.py lint|seam|holds|spikes|legibility|numbers|all [options]
    python scripts/droste_check.py selftest      (checks that every gate reports a failure clearly)
    python scripts/droste_check.py readme        (writes out/README_snippet.md from the spec's alt text)
    python scripts/droste_check.py webp [--webp out/droste.webp]   (delivery check after the final encode)

Every gate prints PASS / FAIL / ERROR plus the numbers behind it. The process exits with 0 if everything passed,
1 if any gate failed, and 2 if a gate could not run (for example a render or bundle error).

  lint        npx tsc --noEmit -p . (skip it with --no-tsc), then esbuild bundles scripts/droste_lint.ts and node
              runs it. The last line must be 'LINT OK'.
  seam        COMP=DrosteSeam. Frame 0 is rendered alone in a fresh browser (cold fonts), then [200, 384] in a
              second run. The max abs diff between 0 and 384 must be 0. On a difference it also renders 384 alone
              in a cold browser: if cold 384 == cold 0, the loop contract holds and the difference is render-order
              dependent rasterisation. It also prints what survives the WebP path.
  holds       COMP=Droste frames 316 318 376 378. The pairs (316, 318) and (376, 378) must be pixel-identical.
              Both strict gates run at scale 1 (1200x500, the WebP's own resolution) unless --scale is given.
              Why: at --scale=2, Chrome/ANGLE rasterises glyphs of about 176 device px and up (text >= 88 u) with
              +-1..2 levels of AA jitter that depends on what the tab rendered before. That happens even for a static
              probe composition, so it is not caused by the loop. 'all' adds informational seam@2x / holds@2x passes:
              PASS if bit-exact, INFO if every difference stays within libwebp's lossy tolerance after the 1200 px
              downscale (so it cannot reach the WebP), and FAIL otherwise.
  spikes      npx remotion render ... Droste out/droste/half --sequence --scale=0.5 --gl=angle --concurrency=2,
              then mean abs diff between consecutive output (even) frames. Inside every dive segment (the landing
              frame f1 included), output frame o is flagged if diff(o) > 2.5 x max(median(diff[o-3..o+3] minus o),
              floor). The window wraps around the loop.
  legibility  Stills 0 94 198 258 316 376 go through the WebP path (LANCZOS to 1200) and then down to the README's
              880 px, into out/sheet_legibility.png (sheet.py --width 880). It also writes
              out/readme_mock_dark.png and out/readme_mock_light.png (frame 0 at 880 px on #0d1117 and on #ffffff)
              and asserts that frame 0's border ring is exactly night #0d1117.
  numbers     Uses the TypeScript AST of src/droste. JSX text, JSX children and text-like props must contain no
              digit run; any other string or template literal fails if it has a free-standing digit run and is not
              SVG path, number list, CSS or GLSL. Identity: no data.top owner handle, no e-mail, no @handle, no
              github.com/<other>, no OS user name, and no data.json import outside timeline.ts. The only identity
              string allowed is 'kevin9327'.
  all         lint, numbers, seam, holds, seam@2x, holds@2x (skip them with --no-2x), legibility and spikes,
              then a summary table.

Options:
  --props JSON   input props for every render (for example '{"zoomLines":false}' once a budget lever is applied)
  --scale S      render scale for seam / holds / legibility (defaults: seam and holds 1, legibility 2)
  --reuse        spikes: reuse the PNGs already in out/droste/half instead of re-rendering (warns if stale)
  --floor F      spikes: absolute floor for the median, in mean-abs-diff levels 0..255 (default 0.5)
  --no-tsc       lint: skip the tsc step
  --src DIR      numbers: scan DIR instead of src/droste
  --retries N    re-run a failed bundle/render N more times, waiting --retry-wait seconds between tries
                 (default 0 / 60). This is for parallel agents that briefly leave the project uncompilable.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
CHECK = OUT / "check"
STILLS = OUT / "stills"
TIMELINE = ROOT / "src" / "droste" / "timeline.ts"
NIGHT = (13, 17, 23)
T = 384
OUT_STEP = 2
N_OUT = T // OUT_STEP
DURS = [67, 67, 66]  # output frame durations, cycling (192 frames = exactly 12800 ms)

SEAM_FRAMES_A = [0]
SEAM_FRAMES_B = [200, 384]
HOLD_PAIRS = [(316, 318), (376, 378)]
LEGIBILITY_FRAMES = [0, 94, 198, 258, 316, 376]
README_W = 880
# libwebp WebPAnimEncoder (anim_encode.c QualityToMaxDiff): at q72 a per-channel change <= 6 counts as unchanged
LOSSY_TOL = round(31 * (1 - (72 / 100) ** 0.5) + (72 / 100) ** 0.5)

# numbers gate: exact literal texts that may contain a digit run, with the reason (keep this list short).
NUMBER_WHITELIST = {
    "every petal = 1 merged PR": "the spec's hand-written key (M4 KEY); the 1 defines the unit, it is not a data claim",
    "0123456789": "the digit alphabet of a rolling odometer column (M4 COUNTER), not a number",
}
IDENTITY = "kevin9327"


# ----------------------------------------------------------------------------------------------- utilities


class Result:
    def __init__(self, name: str, status: str, detail: str):
        self.name, self.status, self.detail = name, status, detail

    @property
    def ok(self) -> bool:
        return self.status == "PASS"


def banner(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * max(4, 70 - len(title))}", flush=True)


def verdict(name: str, ok: bool, detail: str) -> Result:
    st = "PASS" if ok else "FAIL"
    print(f"[{st}] {name}: {detail}", flush=True)
    return Result(name, st, detail)


def error(name: str, detail: str) -> Result:
    print(f"[ERROR] {name}: {detail}", flush=True)
    return Result(name, "ERROR", detail)


def npx() -> str:
    return shutil.which("npx") or "npx"


def node() -> str:
    return shutil.which("node") or "node"


ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
PROGRESS = re.compile(r"^(Rendered|Rendering|Encoded|Stitched|Bundling|Getting)\b.*\d+\s*/\s*\d+")


def run(cmd: list[str], env: dict | None = None, echo: str = "errors", tail: int = 12) -> tuple[int, list[str]]:
    """Run cmd in ROOT, stream the interesting lines, and return (returncode, last lines).

    echo: 'all' prints every line, 'errors' prints only warning/error lines while the command runs, and on failure
    the last lines are always printed."""
    print(f"$ {' '.join(os.path.basename(c) if i == 0 else c for i, c in enumerate(cmd))}", flush=True)
    t0 = time.time()
    p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines: deque[str] = deque(maxlen=400)
    assert p.stdout is not None
    for raw in p.stdout:
        seg = ANSI.sub("", raw.decode("utf-8", errors="replace")).rstrip("\r\n").split("\r")[-1].rstrip()
        if not seg:
            continue
        if lines and PROGRESS.match(seg) and PROGRESS.match(lines[-1]):
            lines.pop()  # keep only the latest progress line
        lines.append(seg)
        if echo == "all" or (echo == "errors" and re.search(r"error|Error|ERROR|failed|Failed|warn", seg)):
            print(f"  | {seg}", flush=True)
    rc = p.wait()
    dt = time.time() - t0
    last = list(lines)
    if rc != 0:
        print(f"  exit {rc} after {dt:.0f} s; last lines:", flush=True)
        for s in last[-40:]:
            print(f"  | {s}", flush=True)
    elif echo != "all":
        for s in last[-tail:]:
            print(f"  | {s}", flush=True)
        print(f"  ok in {dt:.0f} s", flush=True)
    return rc, last


def err_summary(lines: list[str]) -> str:
    """The most telling line of a failed command's output (the first 'Error' line, not a stack frame)."""
    for s in lines:
        t = s.strip()
        if re.search(r"\b\w*Error\b|Module not found|Cannot find|failed", t) and not t.startswith("at "):
            return t[:300]
    return " / ".join(x.strip() for x in lines[-3:])[:300]


def run_retry(cmd: list[str], args, env: dict | None = None, echo: str = "errors") -> tuple[int, list[str]]:
    tries = 1 + max(0, args.retries)
    rc, last = 1, []
    for i in range(tries):
        rc, last = run(cmd, env=env, echo=echo)
        if rc == 0:
            break
        if i + 1 < tries:
            print(f"  retry {i + 1}/{tries - 1} in {args.retry_wait} s (another agent may be mid-edit)", flush=True)
            time.sleep(args.retry_wait)
    return rc, last


def render_env(comp: str, scale: float, props: dict | None) -> dict:
    env = dict(os.environ)
    for k in ("ENTRY", "PROPS"):
        env.pop(k, None)
    env.update(COMP=comp, GL="angle", SCALE=str(scale))
    if props:
        env["PROPS"] = json.dumps(props)
    return env


def stills(prefix: str, frames: list[int], comp: str, scale: float, args) -> tuple[dict[int, Path] | None, str]:
    """Render frames with scripts/stills.mjs in ONE fresh browser. Returns ({frame: path}, '') or (None, error)."""
    paths = {f: STILLS / f"{prefix}_{f}.png" for f in frames}
    for p in paths.values():
        if p.exists():
            p.unlink()
    t0 = time.time() - 1
    rc, last = run_retry([node(), "scripts/stills.mjs", prefix, *map(str, frames)], args, env=render_env(comp, scale, args.props))
    if rc != 0:
        return None, f"stills.mjs {prefix} exited {rc}: {err_summary(last)}"
    missing = [f for f, p in paths.items() if not p.exists() or p.stat().st_mtime < t0]
    if missing:
        return None, f"stills.mjs did not write frames {missing}"
    return paths, ""


def load_rgba(p: Path) -> np.ndarray:
    with Image.open(p) as im:
        return np.asarray(im.convert("RGBA"), dtype=np.int16)


def compare(a: Path, b: Path, label: str) -> tuple[bool, str]:
    """Pixel compare (RGBA). Returns (identical, report). On a difference it writes out/check/<label>_diff.png."""
    A, B = load_rgba(a), load_rgba(b)
    if A.shape != B.shape:
        return False, f"{label}: size {A.shape[1]}x{A.shape[0]} vs {B.shape[1]}x{B.shape[0]}"
    D = np.abs(A - B)
    mx = int(D.max())
    if mx == 0:
        (CHECK / f"{label}_diff.png").unlink(missing_ok=True)  # no stale heatmap from an earlier failing run
        return True, f"{label}: max abs diff 0 ({A.shape[1]}x{A.shape[0]})"
    per = D.max(axis=2)
    ys, xs = np.nonzero(per)
    n = len(xs)
    CHECK.mkdir(parents=True, exist_ok=True)
    # visual: frame B dimmed to 30 %, every differing pixel as a 7x7 magenta mark (a diff of 1 stays visible)
    mark = np.zeros(per.shape, bool)
    h, w = per.shape
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            ys2, xs2 = np.clip(ys + dy, 0, h - 1), np.clip(xs + dx, 0, w - 1)
            mark[ys2, xs2] = True
    vis = (B[..., :3].astype(np.float32) * 0.3).astype(np.uint8)
    vis[mark] = (255, 0, 255)
    out = CHECK / f"{label}_diff.png"
    Image.fromarray(vis, "RGB").save(out)
    return False, (
        f"{label}: max abs diff {mx}, {n} px differ ({100 * n / per.size:.3f}%), mean {D.mean():.4f}, "
        f"bbox x {xs.min()}-{xs.max()} y {ys.min()}-{ys.max()} (image px); heatmap {out.relative_to(ROOT)}"
    )


def load_segs() -> list[tuple[str, int, int, float, float]]:
    src = TIMELINE.read_text(encoding="utf-8")
    segs = [
        (m.group(1), int(m.group(2)), int(m.group(3)), float(m.group(4)), float(m.group(5)))
        for m in re.finditer(r"\{n:\s*'(\w+)',\s*f0:\s*(\d+),\s*f1:\s*(\d+),\s*D0:\s*([\d.]+),\s*D1:\s*([\d.]+)\}", src)
    ]
    if not segs:
        raise RuntimeError("could not parse SEG from src/droste/timeline.ts")
    return segs


def frame_no(p: Path) -> int:
    nums = re.findall(r"\d+", p.name)
    return int(nums[-1]) if nums else -1


# -------------------------------------------------------------------------------------------------- (1) lint


def cmd_lint(args) -> list[Result]:
    banner("lint")
    res: list[Result] = []
    if not args.no_tsc:
        rc, last = run([npx(), "tsc", "--noEmit", "-p", "."], echo="all")
        res.append(verdict("tsc", rc == 0, "npx tsc --noEmit -p . clean" if rc == 0 else f"tsc exit {rc}, {sum('error TS' in x for x in last)} error(s); first: {next((x for x in last if 'error TS' in x), err_summary(last))}"))
    CHECK.mkdir(parents=True, exist_ok=True)
    bundle = CHECK / (Path(args.lint_script).stem + ".mjs")
    rc, last = run_retry(
        [npx(), "esbuild", args.lint_script, "--bundle", "--platform=node", "--format=esm",
         f"--outfile={bundle.relative_to(ROOT).as_posix()}", "--log-level=warning"],
        args,
    )
    if rc != 0:
        res.append(error("lint", f"esbuild could not bundle {args.lint_script} (exit {rc}): {err_summary(last)}"))
        return res
    rc, last = run([node(), str(bundle)], echo="all")
    tailline = next((s for s in reversed(last) if s.strip()), "")
    ok = rc == 0 and tailline.strip() == "LINT OK"
    fails = [s for s in last if s.startswith("FAIL ")]
    detail = "LINT OK" if ok else f"exit {rc}, last line '{tailline}'" + (f"; {len(fails)} FAIL lines, first: {fails[0]}" if fails else "")
    res.append(verdict("lint", ok, detail))
    return res


# -------------------------------------------------------------------------------------------------- (2) seam


def webp_effective(a: Path, b: Path) -> tuple[int, int]:
    """What survives the WebP path: both frames LANCZOS to 1200x500 (droste_webp.py), then (max abs diff, px whose
    per-channel diff exceeds LOSSY_TOL, the tolerance under which libwebp's lossy anim encoder treats a pixel as
    unchanged at q72)."""
    ims = []
    for p_ in (a, b):
        with Image.open(p_) as im:
            im = im.convert("RGB")
            ims.append(np.asarray(im if im.size == (1200, 500) else im.resize((1200, 500), Image.LANCZOS), dtype=np.int16))
    per = np.abs(ims[0] - ims[1]).max(axis=2)
    return int(per.max()), int((per > LOSSY_TOL).sum())


def graded(name: str, strict_ok: bool, rep: str, eff: tuple[int, int] | None, info: bool) -> Result:
    """Strict gates PASS only on max diff 0. Informational (shipping-scale) passes are PASS on 0, INFO when the only
    differences are below the WebP lossy tolerance, and FAIL when a difference would survive the encode."""
    if not info or strict_ok:
        return verdict(name, strict_ok, rep)
    mx, n = eff if eff else (999, 1)
    detail = f"{rep}; after the WebP path (LANCZOS 1200): max {mx}, {n} px > {LOSSY_TOL}"
    if n == 0:
        print(f"[INFO] {name}: {detail} -> not bit-exact at this scale, but below the encoder's tolerance", flush=True)
        return Result(name, "INFO", detail + " (not bit-exact, below the lossy encoder tolerance)")
    return verdict(name, False, detail)


def cmd_seam(args, scale: float | None = None, info: bool = False) -> list[Result]:
    scale = scale or args.scale or 1.0
    name = "seam" if not info else f"seam@{scale:g}x"
    banner(f"{name} (DrosteSeam, scale {scale:g})" + (" [informational: the final render's scale]" if info else ""))
    tag = f"s{scale:g}".replace(".", "p")
    print("run 1: frame 0 alone in a fresh browser (cold fonts)", flush=True)
    a, err = stills(f"chk_seam0_{tag}", SEAM_FRAMES_A, "DrosteSeam", scale, args)
    if a is None:
        return [error(name, err)]
    print("run 2: frames 200, 384 in a second fresh browser", flush=True)
    b, err = stills(f"chk_seam1_{tag}", SEAM_FRAMES_B, "DrosteSeam", scale, args)
    if b is None:
        return [error(name, err)]
    same, rep = compare(a[0], b[384], f"seam_0_vs_384_{tag}")
    rep += " [frame 0 cold, frame 384 after 200]"
    eff = None
    if not same:
        # diagnosis: is the composition itself seam-exact? Render 384 alone in a cold browser, like frame 0.
        print("diagnosis run: frame 384 alone in a fresh browser", flush=True)
        c, err = stills(f"chk_seam2_{tag}", [384], "DrosteSeam", scale, args)
        if c is not None:
            cold_same, _ = compare(a[0], c[384], f"seam_cold_{tag}")
            rep += ("; cold 384 == cold 0 exactly, so the composition closes the loop and the difference is render-order"
                    " dependent rasterisation (large glyphs at this scale)" if cold_same else
                    "; cold 384 != cold 0 as well, so the loop contract itself is broken (see the heatmap)")
        eff = webp_effective(a[0], b[384])
    return [graded(name, same, rep, eff, info)]


# ------------------------------------------------------------------------------------------------- (3) holds


def cmd_holds(args, scale: float | None = None, info: bool = False) -> list[Result]:
    scale = scale or args.scale or 1.0
    name = "holds" if not info else f"holds@{scale:g}x"
    banner(f"{name} (Droste, scale {scale:g})" + (" [informational: the final render's scale]" if info else ""))
    frames = sorted({f for p_ in HOLD_PAIRS for f in p_})
    tag = f"s{scale:g}".replace(".", "p")
    s_, err = stills(f"chk_holds_{tag}", frames, "Droste", scale, args)
    if s_ is None:
        return [error(name, err)]
    reps, ok, effs = [], True, []
    for f0, f1 in HOLD_PAIRS:
        same, rep = compare(s_[f0], s_[f1], f"hold_{f0}_vs_{f1}_{tag}")
        print(("  same  " if same else "  DIFF  ") + rep, flush=True)
        ok &= same
        reps.append(rep)
        if not same:
            effs.append(webp_effective(s_[f0], s_[f1]))
    eff = (max(e[0] for e in effs), sum(e[1] for e in effs)) if effs else None
    return [graded(name, ok, "; ".join(reps), eff, info)]


# ------------------------------------------------------------------------------------------------ (4) spikes


def spike_table(diff: list[float], segs, floor: float) -> tuple[list[dict], list[dict]]:
    """Rows for every dive output frame (landing frame included) and the flagged subset."""
    n = len(diff)
    rows, flagged = [], []
    for name, f0, f1, d0, d1 in segs:
        if d0 == d1:
            continue
        for f in range(f0, f1 + 1, OUT_STEP):
            o = (f // OUT_STEP) % n
            neigh = [diff[(o + k) % n] for k in range(-3, 4) if k != 0]
            med = statistics.median(neigh)
            thr = 2.5 * max(med, floor)
            row = dict(seg=name, f=f % T, o=o, diff=diff[o], med=med, thr=thr, ratio=diff[o] / max(med, 1e-9), flag=diff[o] > thr)
            rows.append(row)
            if row["flag"]:
                flagged.append(row)
    return rows, flagged


def cmd_spikes(args) -> list[Result]:
    banner("spikes (half-scale sequence)")
    seq = OUT / "droste" / "half"
    seq.mkdir(parents=True, exist_ok=True)
    have = sorted(seq.glob("*.png"), key=frame_no)
    if args.reuse and len(have) >= T:
        newest_src = max(p.stat().st_mtime for p in (ROOT / "src").rglob("*") if p.is_file())
        oldest_png = min(p.stat().st_mtime for p in have)
        stale = newest_src > oldest_png
        print(f"reusing {len(have)} PNGs in out/droste/half" + ("  WARNING: src changed after this render (stale)" if stale else ""), flush=True)
    else:
        for p in have:
            p.unlink()
        cmd = [npx(), "remotion", "render", "src/index.ts", "Droste", "out/droste/half", "--sequence", "--image-format=png",
               "--scale=0.5", "--gl=angle", "--concurrency=2"]
        if args.props:
            CHECK.mkdir(parents=True, exist_ok=True)
            pf = CHECK / "props.json"
            pf.write_text(json.dumps(args.props), encoding="utf-8")
            cmd.append(f"--props={pf.relative_to(ROOT).as_posix()}")
        env = dict(os.environ)
        env.pop("PROPS", None)
        rc, last = run_retry(cmd, args, env=env)
        if rc != 0:
            return [error("spikes", f"half-scale render failed (exit {rc}): {err_summary(last)}")]
    files = {frame_no(p): p for p in seq.glob("*.png")}
    even = [f for f in range(0, T, OUT_STEP)]
    missing = [f for f in even if f not in files]
    if missing:
        return [error("spikes", f"out/droste/half is missing {len(missing)} even frames, e.g. {missing[:6]}")]
    t0 = time.time()
    prev = None
    first = None
    diff = [0.0] * N_OUT
    for o, f in enumerate(even):
        with Image.open(files[f]) as im:
            a = np.asarray(im.convert("RGB"), dtype=np.int16)
        if first is None:
            first = a
        if prev is not None:
            diff[o] = float(np.abs(a - prev).mean())
        prev = a
    diff[0] = float(np.abs(first - prev).mean())  # the seam: output 191 (f382) -> output 0 (f0)
    print(f"{N_OUT} output frames {prev.shape[1]}x{prev.shape[0]}, diffs in {time.time() - t0:.1f} s; floor {args.floor}", flush=True)

    segs = load_segs()
    rows, flagged = spike_table(diff, segs, args.floor)
    print(f"\n{'seg':8} {'f':>4} {'o':>4} {'diff':>8} {'median':>8} {'thresh':>8} {'ratio':>6}  flag")
    for r in rows:
        print(f"{r['seg']:8} {r['f']:>4} {r['o']:>4} {r['diff']:8.3f} {r['med']:8.3f} {r['thr']:8.3f} {r['ratio']:6.2f}  {'SPIKE' if r['flag'] else ''}")
    print(f"\n{'segment':8} {'out':>4} {'mean':>8} {'max':>8}  (all segments; diff = mean abs diff vs previous output frame, 0..255)")
    for name, f0, f1, d0, d1 in segs:
        ds = [diff[f // OUT_STEP] for f in range(f0, f1, OUT_STEP)]
        print(f"{name:8} {len(ds):>4} {statistics.mean(ds):8.3f} {max(ds):8.3f}")
    print(f"seam diff (f382 -> f0): {diff[0]:.4f}")
    if flagged:
        detail = f"{len(flagged)} spike(s): " + ", ".join(f"{r['seg']} f{r['f']} (diff {r['diff']:.2f} > {r['thr']:.2f})" for r in flagged)
    else:
        detail = f"0 spikes over {len(rows)} dive output frames (max ratio {max(r['ratio'] for r in rows):.2f} at " + \
            next(f"{r['seg']} f{r['f']}" for r in rows if r["ratio"] == max(x["ratio"] for x in rows)) + ")"
    return [verdict("spikes", not flagged, detail)]


# -------------------------------------------------------------------------------------------- (5) legibility


def readme_mock(frame: Image.Image, bg: str, border: str, fg: str, out: Path) -> None:
    """Frame 0 at 880 px inside a GitHub-like README box on the page background."""
    m, head = 32, 44
    W, H = README_W + 2 * m, frame.height + head + 2 * m
    page = Image.new("RGB", (W + 2 * m, H + 2 * m), bg)
    d = ImageDraw.Draw(page)
    d.rounded_rectangle([m, m, m + W - 1, m + H - 1], radius=6, outline=border, width=1)
    d.line([m, m + head, m + W - 1, m + head], fill=border, width=1)
    d.text((m + 16, m + 15), "README.md", fill=fg)
    page.paste(frame, (2 * m, m + head + m))
    page.save(out)


def cmd_legibility(args) -> list[Result]:
    scale = args.scale or 2.0
    banner(f"legibility (scale {scale:g} -> 1200 -> {README_W} px)")
    s, err = stills("chk_leg", LEGIBILITY_FRAMES, "Droste", scale, args)
    if s is None:
        return [error("legibility", err)]
    legdir = OUT / "legibility"
    legdir.mkdir(parents=True, exist_ok=True)
    h1200, h880 = 500, round(README_W * 5 / 12)
    files, notes, ok = [], [], True
    for f in LEGIBILITY_FRAMES:
        with Image.open(s[f]) as im:
            raw = im.convert("RGB")
        w1200 = raw if raw.size == (1200, h1200) else raw.resize((1200, h1200), Image.LANCZOS)  # droste_webp.py path
        small = w1200.resize((README_W, h880), Image.LANCZOS)  # the README's ~880 px display
        p = legdir / f"leg_{f}.png"
        small.save(p)
        files.append(p)
        if f == 0:
            for label, im in (("render", raw), ("1200", w1200), ("880", small)):
                a = np.asarray(im)
                ring = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
                bad = int((np.abs(ring.astype(np.int16) - np.array(NIGHT)).max(axis=1) > 0).sum())
                notes.append(f"f0 border @{label} {'exact #0d1117' if bad == 0 else f'{bad} px not night'}")
                ok &= bad == 0
            readme_mock(small, "#0d1117", "#30363d", "#8b949e", OUT / "readme_mock_dark.png")
            readme_mock(small, "#ffffff", "#d0d7de", "#59636e", OUT / "readme_mock_light.png")
    sheet = OUT / "sheet_legibility.png"
    rc, last = run([sys.executable, "scripts/sheet.py", "--width", str(README_W), str(sheet), *map(str, files)])
    if rc != 0 or not sheet.exists():
        return [error("legibility", f"sheet.py failed: {err_summary(last)}")]
    detail = (f"{len(files)} stills at {README_W}x{h880} -> {sheet.relative_to(ROOT)}, out/readme_mock_dark.png, "
              f"out/readme_mock_light.png; " + "; ".join(notes) + ". Readability itself is a visual call: LOOK at the sheet.")
    return [verdict("legibility", ok, detail)]


# ----------------------------------------------------------------------------------------------- (6) numbers

SCANNER_JS = r"""
// Generated by scripts/droste_check.py (numbers gate). Walks the TypeScript AST and prints every literal that can
// carry text, with the context it sits in. Usage: node scan.cjs <projectRoot> <file>...
const path = require('path');
const fs = require('fs');
const root = process.argv[2];
const ts = require(path.join(root, 'node_modules', 'typescript'));
const TEXT_ATTRS = new Set(['text', 'label', 'title', 'alt', 'aria-label', 'caption', 'content', 'children', 'placeholder']);
const TEXT_KEYS = new Set(['text', 'label', 'title', 'caption', 'alt', 'content', 'msg', 'message']);
const FORMAT_CALLS = new Set(['padStart', 'padEnd', 'split', 'join', 'replace', 'replaceAll']);
// diagnostics never reach the frame: guard/check/assert messages, console output, thrown errors, render handles
const DIAG_CALLS = new Set(['guard', 'check', 'assert', 'invariant', 'log', 'warn', 'error', 'info', 'debug', 'cancelRender', 'delayRender', 'continueRender']);
const out = [];
const isFn = (n) => ts.isArrowFunction(n) || ts.isFunctionExpression(n) || ts.isFunctionDeclaration(n) ||
  ts.isMethodDeclaration(n) || ts.isGetAccessorDeclaration(n) || ts.isSetAccessorDeclaration(n) || ts.isConstructorDeclaration(n);
const calleeName = (c) => ts.isPropertyAccessExpression(c.expression) ? c.expression.name.text : ts.isIdentifier(c.expression) ? c.expression.text : '';
function context(node) {
  let n = node, fn = false, fmt = '';
  while (n.parent) {
    const p = n.parent;
    if (ts.isCallExpression(p) && p.arguments.includes(n) && !fn && !fmt && FORMAT_CALLS.has(calleeName(p))) fmt = calleeName(p);
    if (ts.isCallExpression(p) && p.arguments.includes(n) && DIAG_CALLS.has(calleeName(p))) return {ctx: 'diagnostic', name: calleeName(p), fmt};
    if (ts.isThrowStatement(p) || (ts.isNewExpression(p) && /Error$/.test(p.expression.getText()))) return {ctx: 'diagnostic', name: 'throw', fmt};
    if (ts.isJsxAttribute(p)) {
      const name = p.name.getText();
      return {ctx: TEXT_ATTRS.has(name) ? (fn ? 'text-attr-fn' : 'text-attr') : 'attr', name, fmt};
    }
    if (ts.isJsxSpreadAttribute(p)) return {ctx: 'attr', name: '...', fmt};
    if (ts.isJsxExpression(p) && p.parent && (ts.isJsxElement(p.parent) || ts.isJsxFragment(p.parent)))
      return {ctx: fn ? 'jsx-child-fn' : 'jsx-child', name: '', fmt};
    if (ts.isPropertyAssignment(p) && p.initializer === n && !fn) {
      const key = p.name.getText().replace(/['"]/g, '');
      if (TEXT_KEYS.has(key)) return {ctx: 'text-prop', name: key, fmt};
    }
    if (ts.isImportDeclaration(p) || ts.isExportDeclaration(p) || ts.isImportTypeNode(p) || ts.isExternalModuleReference(p))
      return {ctx: 'import', name: '', fmt};
    if (ts.isLiteralTypeNode(p)) return {ctx: 'type', name: '', fmt};
    if (isFn(p)) fn = true;
    n = p;
  }
  return {ctx: 'code', name: '', fmt};
}
function templateText(t) {
  let s = t.head.text;
  for (const sp of t.templateSpans) {
    const e = sp.expression;
    if (ts.isNumericLiteral(e) || ts.isStringLiteral(e) || ts.isNoSubstitutionTemplateLiteral(e)) s += e.text;
    else s += '\u00a7';
    s += sp.literal.text;
  }
  return s;
}
for (const file of process.argv.slice(3)) {
  const text = fs.readFileSync(file, 'utf8');
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const rec = (node, kind, value, c) => {
    const lc = sf.getLineAndCharacterOfPosition(node.getStart(sf));
    // arr: the array literal a string sits in (so shader sources written as an array of lines are judged whole)
    const arr = node.parent && ts.isArrayLiteralExpression(node.parent) ? node.parent.getStart(sf) : -1;
    out.push({file, line: lc.line + 1, col: lc.character + 1, kind, text: value, ctx: c.ctx, name: c.name, fmt: c.fmt, arr});
  };
  const visit = (node) => {
    if (ts.isJsxText(node)) {
      if (!node.containsOnlyTriviaWhiteSpaces) rec(node, 'jsx-text', node.text.replace(/\s+/g, ' ').trim(), {ctx: 'jsx-text', name: '', fmt: ''});
    } else if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      const p = node.parent;
      const isKey = p && (ts.isPropertyAssignment(p) || ts.isPropertyDeclaration(p) || ts.isPropertySignature(p) || ts.isMethodDeclaration(p)) && p.name === node;
      if (!isKey) rec(node, ts.isStringLiteral(node) ? 'string' : 'template', node.text, context(node));
    } else if (ts.isTemplateExpression(node)) {
      rec(node, 'template', templateText(node), context(node));
    } else if (ts.isNumericLiteral(node)) {
      let e = node;
      if (e.parent && ts.isCallExpression(e.parent) && calleeName(e.parent) === 'String') e = e.parent;
      if (e.parent && ts.isJsxExpression(e.parent)) rec(node, 'number', node.text, context(e));
    } else if (ts.isPropertyAccessExpression(node)) {
      const nm = node.name.text;
      const obj = node.expression.getText(sf);
      if (nm === 'owner' || (nm === 'top' && /(^|\.)(data|DATA)$/.test(obj))) rec(node, 'access', obj + '.' + nm, {ctx: 'code', name: '', fmt: ''});
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
}
process.stdout.write(JSON.stringify(out));
"""

STRICT_CTX = {"jsx-text", "jsx-child", "text-attr", "text-prop"}
# A free-standing digit run: not glued to letters, digits, '_', '#', '$' or '.' (so ids like 'boil-L0-base',
# colours like '#0d1117', 'kevin9327' and '2x' do not count; '535', '×535', 'JUL 18', '= 1 merged' do).
DIGIT_RUN = re.compile(r"(?<![A-Za-z0-9_#$.])\d+(?:\.\d+)?(?![A-Za-z0-9_])")
SVG_PATH = re.compile(r"^[\s\u00a7MmLlHhVvCcSsQqTtAaZz0-9.,eE+-]*$")
NUM_LIST = re.compile(r"^[\s\u00a70-9.,eE+-]*$")
CODEISH = [
    (re.compile(r"\b(translate|rotate|scale|matrix|skew[XY]?|blur|url|rgba?|hsla?|drop-shadow|calc|var|brightness|contrast|saturate|cubic-bezier|steps)\s*\(", re.I), "css/svg function"),
    (re.compile(r"\d(px|em|rem|vh|vw|vmin|vmax|deg|rad|turn|ms)\b|\d%"), "css unit"),
    (re.compile(r"#version|precision\s+(high|medium|low)p|gl_Frag|void\s+main|\buniform\b|\bvec[234]\b|\bfloat\b|\bfwidth\b"), "glsl"),
]


def codeish(text: str) -> str:
    if SVG_PATH.match(text) and re.search(r"[MmLlHhVvCcSsQqTtAaZz]", text):
        return "svg path"
    if NUM_LIST.match(text):
        return "number list"
    for rx, why in CODEISH:
        if rx.search(text):
            return why
    return ""


GLSL = CODEISH[2][0]


def glsl_arrays(recs: list[dict]) -> set[tuple[str, int]]:
    """Array literals whose string elements, joined, read as GLSL source (for example ['#version 300 es', ...])."""
    groups: dict[tuple[str, int], list[str]] = {}
    for r in recs:
        if r.get("arr", -1) >= 0 and r["kind"] in ("string", "template"):
            groups.setdefault((r["file"], r["arr"]), []).append(r["text"])
    return {k for k, v in groups.items() if len(v) >= 3 and GLSL.search("\n".join(v))}


def classify(rec: dict, glsl: set[tuple[str, int]] | None = None) -> tuple[str, str]:
    """-> ('fail'|'ok'|'skip', reason) for one scanned literal."""
    text, ctx = rec["text"], rec["ctx"]
    if glsl and (rec["file"], rec.get("arr", -1)) in glsl and ctx not in STRICT_CTX:
        return "skip", "glsl (array of lines)"
    if ctx in ("attr", "import", "type", "diagnostic") or rec["kind"] == "access":
        return "skip", ctx
    if rec["fmt"] in ("padStart", "padEnd", "split", "join", "replace", "replaceAll"):
        return "skip", f"argument of {rec['fmt']}()"
    runs = DIGIT_RUN.findall(text) if rec["kind"] != "number" else [text]
    if not runs:
        return "ok", "no digit run"
    if text.strip() in NUMBER_WHITELIST:
        return "ok", "whitelisted: " + NUMBER_WHITELIST[text.strip()]
    if ctx in STRICT_CTX:
        return "fail", f"digit run {runs[0]!r} in displayed text ({ctx}{':' + rec['name'] if rec['name'] else ''})"
    why = codeish(text)
    if why:
        return "skip", why
    return "fail", f"digit run {runs[0]!r} in a {rec['kind']} literal that is not path/list/css/glsl ({ctx})"


def scan_files(files: list[Path]) -> list[dict]:
    CHECK.mkdir(parents=True, exist_ok=True)
    js = CHECK / "numbers_scan.cjs"
    js.write_text(SCANNER_JS, encoding="utf-8")
    p = subprocess.run([node(), str(js), str(ROOT), *map(str, files)], cwd=ROOT, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", "replace")[-800:])
    return json.loads(p.stdout.decode("utf-8"))


def identity_hits(files: list[Path], recs: list[dict], src_root: Path) -> list[str]:
    data = json.loads((ROOT / "src" / "data.json").read_text(encoding="utf-8"))
    owners = sorted({t.get("owner", "") for t in data.get("top", []) if t.get("owner")} - {IDENTITY}, key=str.lower)
    user = {os.environ.get("USERNAME", ""), os.environ.get("USER", ""), Path.home().name}
    user = {u for u in user if len(u) >= 4 and u.lower() != IDENTITY}
    hits: list[str] = []
    owner_rx = [(o, re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(o) + r"(?![A-Za-z0-9_-])", re.I)) for o in owners]
    user_rx = [(u, re.compile(r"(?<![A-Za-z0-9_])" + re.escape(u) + r"(?![A-Za-z0-9_])", re.I)) for u in user]
    email_rx = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
    gh_rx = re.compile(r"github\.com/([A-Za-z0-9-]+)", re.I)
    json_rx = re.compile(r"""(?:from\s+|require\(\s*|import\(\s*)['"][^'"]*data\.json['"]""")
    for f in files:
        rel = f.relative_to(src_root.parent) if src_root.parent in f.parents else f
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for o, rx in owner_rx:
                if rx.search(line):
                    hits.append(f"{rel}:{i}: repo owner handle '{o}' (from data.top)")
            for u, rx in user_rx:
                if rx.search(line):
                    hits.append(f"{rel}:{i}: local user name")
            for m in email_rx.finditer(line):
                hits.append(f"{rel}:{i}: e-mail address '{m.group(0)}'")
            for m in gh_rx.finditer(line):
                if m.group(1).lower() != IDENTITY:
                    hits.append(f"{rel}:{i}: github.com/{m.group(1)}")
            if json_rx.search(line) and f.name != "timeline.ts":
                hits.append(f"{rel}:{i}: imports data.json directly (only timeline.ts may; everything shown must pass the DATA guards)")
    for r in recs:
        rf = Path(r["file"])
        rel = rf.relative_to(src_root.parent) if src_root.parent in rf.parents else rf
        if r["kind"] == "access":
            hits.append(f"{rel}:{r['line']}: reads '{r['text']}' (owner handles must never reach the banner)")
            continue
        if r["ctx"] in ("import", "type"):
            continue
        for m in re.finditer(r"(?<![\w.])@([A-Za-z0-9][A-Za-z0-9-]*)", r["text"]):
            if m.group(1).lower() != IDENTITY:
                hits.append(f"{rel}:{r['line']}: @handle '@{m.group(1)}' in a {r['kind']} literal")
    return hits


def cmd_numbers(args) -> list[Result]:
    src_root = Path(args.src).resolve() if args.src else ROOT / "src" / "droste"
    banner(f"numbers + identity ({src_root})")
    files = sorted(p for p in src_root.rglob("*") if p.suffix in (".ts", ".tsx") and p.is_file())
    if not files:
        return [error("numbers", f"no .ts/.tsx files under {src_root}")]
    try:
        recs = scan_files(files)
    except Exception as e:  # noqa: BLE001
        return [error("numbers", f"AST scan failed: {e}")]
    fails, skipped, okd = [], {}, 0
    glsl = glsl_arrays(recs)
    for r in recs:
        st, why = classify(r, glsl)
        if st == "fail":
            fails.append(f"{Path(r['file']).relative_to(src_root.parent) if src_root.parent in Path(r['file']).parents else r['file']}:{r['line']}:{r['col']}  {why}:  {r['text'].replace(chr(0xa7), '${...}')[:90]!r}")
        elif st == "skip":
            skipped[why] = skipped.get(why, 0) + 1
        else:
            okd += 1
    wl = sorted({r["text"].strip() for r in recs if r["text"].strip() in NUMBER_WHITELIST})
    print(f"{len(files)} files, {len(recs)} text-bearing literals: {okd} clean, {len(fails)} FAIL, skipped by context: "
          + ", ".join(f"{k} {v}" for k, v in sorted(skipped.items())), flush=True)
    for w in wl:
        print(f"  whitelisted: {w!r} ({NUMBER_WHITELIST[w]})")
    for s in fails:
        print(f"  FAIL {s}")
    ids = identity_hits(files, recs, src_root)
    for s in ids:
        print(f"  FAIL identity {s}")
    res = [
        verdict("numbers", not fails, f"{len(fails)} hard-coded digit run(s) in shown text" + (f"; first: {fails[0]}" if fails else f" ({len(recs)} literals scanned in {len(files)} files)")),
        verdict("identity", not ids, f"{len(ids)} identity hit(s)" + (f"; first: {ids[0]}" if ids else f" (only '{IDENTITY}' present)")),
    ]
    return res


# ------------------------------------------------------------------------------------------------- extras


def cmd_readme(args) -> list[Result]:
    banner("readme snippet")
    spec = json.loads((ROOT / "spec_main.json").read_text(encoding="utf-8"))
    alt = spec["readme_alt_text"].replace("\ufffd\ufffd", "\u00b7").replace("\ufffd", "\u00b7").replace('"', "&quot;")
    snippet = f'<p align="center"><img src="assets/droste.webp" width="100%" alt="{alt}"></p>\n'
    out = OUT / "README_snippet.md"
    out.write_text(snippet, encoding="utf-8")
    ids = [w for w in re.findall(r"@[\w-]+|[\w.+-]+@[\w-]+\.\w+", alt)]
    data = json.loads((ROOT / "src" / "data.json").read_text(encoding="utf-8"))
    allowed = {str(data["total"]), str(data["repos"]), str(data["days"])}
    stray = sorted(set(re.findall(r"\d+", alt.replace(IDENTITY, ""))) - allowed)
    print(snippet.rstrip())
    ok = not ids and not stray
    return [verdict("readme", ok, f"wrote {out.relative_to(ROOT)} (place it ABOVE the assets/hero.webp header; publishing is the owner's call)"
                    + (f"; alt text numbers not in data.json: {stray}" if stray else f"; alt numbers match data.json {sorted(allowed)}")
                    + (f"; identity strings: {ids}" if ids else ""))]


def cmd_webp(args) -> list[Result]:
    """Delivery check of the encoded banner (integration runs it after droste_webp.py)."""
    path = Path(args.webp) if args.webp else OUT / "droste.webp"
    banner(f"webp ({path})")
    if not path.exists():
        return [error("webp", f"{path} does not exist (integration renders and encodes it)")]
    size = path.stat().st_size
    with Image.open(path) as im:
        n = getattr(im, "n_frames", 1)
        dims, loop = im.size, im.info.get("loop")
        durs = []
        for i in range(n):
            im.seek(i)
            im.load()
            durs.append(int(im.info.get("duration") or 0))
    grid, t = [], 0
    for i in range(N_OUT):
        grid.append(t)
        t += DURS[i % 3]
    starts, t = [], 0
    for d in durs:
        starts.append(t)
        t += d
    total = t
    off = [s for s in starts if s not in set(grid)]
    mb = size / 1024 / 1024
    checks = [
        (dims == (1200, 500), f"{dims[0]}x{dims[1]}"),
        (total == 12800, f"total {total} ms"),
        (loop == 0, f"loop={loop}"),
        (not off, "every frame starts on the 67/67/66 output grid" if not off else f"{len(off)} frame starts off the output grid, e.g. {off[:4]} ms"),
        (mb <= 4.0, f"{size} bytes = {mb:.3f} MB (hard limit 4.0, target 3.2{': OVER TARGET' if mb > 3.2 else ''})"),
    ]
    implied = sum(1 for g in grid if g < total) if total <= 12800 else N_OUT
    merged = implied - n
    for ok, msg in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {msg}")
    print(f"  {n} stored frames for {implied} output frames: libwebp folds each run of consecutive frames it sees as unchanged"
          f" (within its lossy tolerance) into one longer frame ({merged} folded). The timing still sits on the 15 fps grid.")
    ok = all(c[0] for c in checks)
    return [verdict("webp", ok, "; ".join(m for _, m in checks) + f"; {n} stored frames ({merged} folded)")]


def cmd_selftest(args) -> list[Result]:
    """Feed every gate a known-bad input and check that it reports FAIL with the right numbers."""
    banner("selftest (failure paths)")
    res: list[Result] = []
    tmp = Path(tempfile.mkdtemp(prefix="droste_check_"))
    try:
        # compare(): identical and different images
        a = Image.new("RGBA", (40, 20), NIGHT + (255,))
        b = a.copy()
        b.putpixel((7, 5), (13, 17, 24, 255))
        b.putpixel((30, 12), (200, 17, 23, 255))
        a.save(tmp / "a.png"), b.save(tmp / "b.png"), a.save(tmp / "c.png")
        same, rep = compare(tmp / "a.png", tmp / "c.png", "selftest_same")
        diff_ok, rep2 = compare(tmp / "a.png", tmp / "b.png", "selftest_diff")
        good = same and not diff_ok and "max abs diff 187" in rep2 and "2 px differ" in rep2 and "x 7-30 y 5-12" in rep2
        print(f"  {rep}\n  {rep2}")
        res.append(verdict("selftest compare", good, "identical -> diff 0; 2 changed px -> max 187, bbox reported"))
        (CHECK / "selftest_diff_diff.png").unlink(missing_ok=True)

        # spike detector: smooth dive with one pop, plus a hold of zeros around it
        segs = [("hold", 0, 20, 0, 0), ("dive", 20, 60, 0, 1), ("hold2", 60, T, 1, 1)]
        diff = [0.0] * N_OUT
        for f in range(20, 61, 2):
            u = (f - 20) / 40
            diff[f // 2] = 12 * (1 - abs(2 * u - 1)) + 0.05
        diff[20] *= 3.5  # f40: a pop
        rows, flagged = spike_table(diff, segs, 0.5)
        good = [r["f"] for r in flagged] == [40]
        res.append(verdict("selftest spikes", good, f"planted pop at f40 -> flagged {[r['f'] for r in flagged]} of {len(rows)} dive frames"))

        # numbers + identity: a fixture with every kind of violation, and a clean twin
        owner = next((t["owner"] for t in json.loads((ROOT / "src" / "data.json").read_text(encoding="utf-8"))["top"]), "someowner")
        bad = tmp / "bad" / "droste"
        bad.mkdir(parents=True)
        (bad / "Bad.tsx").write_text(
            "import React from 'react';\n"
            "const TOKS = [['// merged \u00d7535', 'gray']];\n"
            "const who = '" + owner + "';\n"
            "export const Bad = ({n}: {n: number}) => (\n"
            "  <g>\n"
            "    <text>535 MERGED</text>\n"
            "    <text>{`${n} of 32 repos`}</text>\n"
            "    <text>{535}</text>\n"
            "    <Pop text=\"Top 10\" />\n"
            "    <text>{'@someone'}</text>\n"
            "    <path d={`M 0 0 L ${n} 10`} transform={`rotate(-60)`} />\n"
            "  </g>\n"
            ");\n",
            encoding="utf-8",
        )
        (bad / "Clean.tsx").write_text(
            "import React from 'react';\nimport {DATA} from './timeline';\n"
            "const d = `M 0 0 Q 3.2 ${-0.45} 0 0`;\nconst font = `700 104px Mono`;\n"
            "const FS = ['#version 300 es', 'precision highp float;', 'void main() {', '  if (a <= 0.0) discard;', '}'].join('\\n');\n"
            "export const Clean = () => (<g><text>{String(DATA.total)} MERGED</text><text>{`merged \u00b7 ${DATA.repos} repos`}</text>"
            "<Hand text=\"every petal = 1 merged PR\" /><path d={d} /><text>{String(0).padStart(3, '0')}</text></g>);\n",
            encoding="utf-8",
        )
        ns = argparse.Namespace(**{**vars(args), "src": str(bad)})
        r = cmd_numbers(ns)
        num, ident = r[0], r[1]
        n_fail = int(num.detail.split()[0])
        good = (not num.ok) and n_fail == 5 and (not ident.ok) and int(ident.detail.split()[0]) == 2
        res.append(verdict("selftest numbers", good, f"planted 5 digit runs + 2 identity strings -> numbers '{num.detail[:60]}...', identity '{ident.detail[:60]}...'"))
        (bad / "Bad.tsx").unlink()
        r = cmd_numbers(ns)
        res.append(verdict("selftest numbers clean", r[0].ok and r[1].ok, "clean fixture (DATA numbers, path data, CSS font, whitelisted key, padStart) passes"))

        # lint: a lint that prints FAIL lines and 'LINT FAIL' must come back as FAIL with the first FAIL line
        fake = tmp / "fake_lint.ts"
        fake.write_text("console.log('FAIL l0Pose(371) != SLEEP_L0');\nconsole.log('LINT FAIL');\nprocess.exit(1);\n", encoding="utf-8")
        ns = argparse.Namespace(**{**vars(args), "no_tsc": True, "lint_script": str(fake)})
        r = cmd_lint(ns)
        good = len(r) == 1 and r[0].status == "FAIL" and "l0Pose(371)" in r[0].detail
        res.append(verdict("selftest lint", good, f"fake failing lint -> {r[0].status}: {r[0].detail}"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


# ---------------------------------------------------------------------------------------------------- main

GATES = {
    "lint": cmd_lint,
    "numbers": cmd_numbers,
    "seam": cmd_seam,
    "holds": cmd_holds,
    "legibility": cmd_legibility,
    "spikes": cmd_spikes,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=[*GATES, "all", "selftest", "readme", "webp"])
    ap.add_argument("--webp", default=None, help="webp: the file to check (default out/droste.webp)")
    ap.add_argument("--props", type=json.loads, default=None, help="JSON input props for every render")
    ap.add_argument("--scale", type=float, default=None)
    ap.add_argument("--no-2x", action="store_true")
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--floor", type=float, default=0.5)
    ap.add_argument("--no-tsc", action="store_true")
    ap.add_argument("--src", default=None)
    ap.add_argument("--retries", type=int, default=0)
    ap.add_argument("--retry-wait", type=int, default=60)
    ap.add_argument("--lint-script", default="scripts/droste_lint.ts", help=argparse.SUPPRESS)
    args = ap.parse_args()

    t0 = time.time()
    if args.cmd == "all":
        todo = [cmd_lint, cmd_numbers, cmd_seam, cmd_holds]
        if not args.no_2x and not args.scale:
            todo += [lambda a: cmd_seam(a, 2.0, info=True), lambda a: cmd_holds(a, 2.0, info=True)]
        todo += [cmd_legibility, cmd_spikes]
    elif args.cmd == "selftest":
        todo = [cmd_selftest]
    elif args.cmd == "readme":
        todo = [cmd_readme]
    elif args.cmd == "webp":
        todo = [cmd_webp]
    else:
        todo = [GATES[args.cmd]]
    results: list[Result] = []
    for fn in todo:
        try:
            results += fn(args)
        except Exception as e:  # noqa: BLE001
            results.append(error(getattr(fn, "__name__", "gate").replace("cmd_", ""), f"{type(e).__name__}: {e}"))

    banner(f"summary ({time.time() - t0:.0f} s)" + (f" props={json.dumps(args.props)}" if args.props else ""))
    for r in results:
        print(f"  {r.status:5}  {r.name:22} {r.detail}")
    if any(r.status == "ERROR" for r in results):
        print("RESULT: ERROR (a gate could not run)")
        return 2
    if all(r.ok or r.status == "INFO" for r in results):
        print("RESULT: ALL PASS" + (" (INFO lines are informational)" if any(r.status == "INFO" for r in results) else ""))
        return 0
    print("RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
