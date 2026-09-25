"""Encode a Droste PNG sequence to an animated WebP, with an optional per-segment size report.

python scripts/droste_webp.py IN_DIR OUT.webp [--step 2] [--width 1200] [--q 72] [--kmin 14] [--kmax 15]
                              [--mixed] [--frames f0:f1] [--report]

- Reads IN_DIR/*.png sorted by the (last) integer in the file name = the COMPOSITION frame number, and keeps
  frames with f % step == 0 (and f0 <= f < f1 with --frames).
- Pillow LANCZOS resize to width x round(width*5/12).
- save_all, loop=0, durations cycling [67, 67, 66] (192 frames = exactly 12800 ms), quality q, method 6,
  minimize_size False (it would disable keyframe insertion), kmin/kmax, allow_mixed per --mixed.
- --report encodes each SEG range (parsed from src/droste/timeline.ts) that has frames on its own and prints
  KB and KB per output frame; flags dives > 30 KB/frame and holds > 12 KB/frame; prints the totals.
"""
import argparse
import io
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TIMELINE = os.path.join(HERE, "..", "src", "droste", "timeline.ts")
DURS = [67, 67, 66]


def load_segs():
    src = open(TIMELINE, encoding="utf-8").read()
    segs = []
    for m in re.finditer(r"\{n:\s*'(\w+)',\s*f0:\s*(\d+),\s*f1:\s*(\d+),\s*D0:\s*([\d.]+),\s*D1:\s*([\d.]+)\}", src):
        segs.append((m.group(1), int(m.group(2)), int(m.group(3)), float(m.group(4)), float(m.group(5))))
    if not segs:
        sys.exit("could not parse SEG from timeline.ts")
    return segs


def frame_no(fn):
    nums = re.findall(r"\d+", os.path.basename(fn))
    return int(nums[-1]) if nums else -1


def list_frames(in_dir, step, rng):
    files = [os.path.join(in_dir, f) for f in os.listdir(in_dir) if f.lower().endswith(".png")]
    files.sort(key=frame_no)
    out = []
    for fn in files:
        f = frame_no(fn)
        if f % step:
            continue
        if rng and not (rng[0] <= f < rng[1]):
            continue
        out.append((f, fn))
    return out


def load(frames, width):
    h = round(width * 5 / 12)
    ims = []
    for _, fn in frames:
        with Image.open(fn) as im:
            im = im.convert("RGB")
            ims.append(im if im.size == (width, h) else im.resize((width, h), Image.LANCZOS))
    return ims


def encode(ims, args, first_out_index=0):
    """Encode frames; durations follow the global output-frame index so a segment gets its real durations."""
    durs = [DURS[(first_out_index + i) % 3] for i in range(len(ims))]
    buf = io.BytesIO()
    kw = dict(
        format="WEBP",
        save_all=True,
        append_images=ims[1:],
        duration=durs if len(ims) > 1 else durs[0],
        loop=0,
        quality=args.q,
        method=6,
        minimize_size=False,
        kmin=args.kmin,
        kmax=args.kmax,
        allow_mixed=args.mixed,
        lossless=False,
    )
    ims[0].save(buf, **kw)
    return buf.getvalue(), sum(durs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("in_dir")
    ap.add_argument("out")
    ap.add_argument("--step", type=int, default=2)
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--q", type=int, default=72)
    ap.add_argument("--kmin", type=int, default=14)
    ap.add_argument("--kmax", type=int, default=15)
    ap.add_argument("--mixed", action="store_true")
    ap.add_argument("--frames", default=None, help="f0:f1 composition-frame range (f1 exclusive)")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    rng = None
    if args.frames:
        a, b = args.frames.split(":")
        rng = (int(a), int(b))
    frames = list_frames(args.in_dir, args.step, rng)
    if not frames:
        sys.exit(f"no frames in {args.in_dir}")
    ims = load(frames, args.width)
    first_out = frames[0][0] // args.step
    data, total_ms = encode(ims, args, first_out)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as fh:
        fh.write(data)
    n = len(ims)
    print(
        f"{args.out}: {n} frames {ims[0].size[0]}x{ims[0].size[1]} {total_ms} ms  {len(data)/1024:.1f} KB"
        f"  ({len(data)/1024/n:.2f} KB/frame)  q{args.q} k{args.kmin}/{args.kmax} mixed={args.mixed}"
    )

    if args.report:
        segs = load_segs()
        print(f"\n{'segment':10} {'comp f':>9} {'out':>4} {'KB':>8} {'KB/frame':>9}  flag")
        tot_kb = 0.0
        tot_n = 0
        flagged = 0
        for name, f0, f1, d0, d1 in segs:
            idx = [i for i, (f, _) in enumerate(frames) if f0 <= f < f1]
            if not idx:
                continue
            sub = [ims[i] for i in idx]
            b, _ = encode(sub, args, frames[idx[0]][0] // args.step)
            kb = len(b) / 1024
            per = kb / len(sub)
            dive = d0 != d1
            lim = 30 if dive else 12
            flag = f"OVER {lim}" if per > lim else ""
            flagged += bool(flag)
            tot_kb += kb
            tot_n += len(sub)
            print(f"{name:10} {f'{f0}-{f1}':>9} {len(sub):>4} {kb:8.1f} {per:9.2f}  {flag}")
        print(f"{'sum':10} {'':>9} {tot_n:>4} {tot_kb:8.1f} {tot_kb/max(1,tot_n):9.2f}  (segments encoded separately)")
        print(f"{'file':10} {'':>9} {n:>4} {len(data)/1024:8.1f} {len(data)/1024/n:9.2f}  ({len(data)/1024/1024:.3f} MB)")
        if flagged:
            print(f"{flagged} segment(s) over budget")


if __name__ == "__main__":
    main()
