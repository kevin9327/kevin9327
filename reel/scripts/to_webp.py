"""Clean half-size render -> the README's animated WebP.

    npx remotion render src/index.ts ProfileReel out/reel_clean.mp4 --props='{"clean":true}' --scale 0.5 --crf 12
    python scripts/to_webp.py out/reel_clean.mp4 ../assets/reel.webp

12 fps, "on twos" like the cartoons it borrows from. A keyframe every second: without one, the lossy
encoder keeps any pixel that changed by only a few levels, and faint ghosts of old frames pile up in the dark scenes.
"""
import glob, os, shutil, subprocess, sys, tempfile
from PIL import Image

FPS = 12
src, out = sys.argv[1], sys.argv[2]
ffmpeg = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", src, "-vf", f"fps={FPS}", f"{tmp}/%04d.png"], check=True)
    frames = [Image.open(f).convert("RGB") for f in sorted(glob.glob(f"{tmp}/*.png"))]
frames[0].save(out, save_all=True, append_images=frames[1:], duration=round(1000 / FPS), loop=0,
               quality=72, method=6, kmin=FPS - 1, kmax=FPS, lossless=False)
print(out, len(frames), "frames", os.path.getsize(out), "bytes")
