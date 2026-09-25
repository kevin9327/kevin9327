"""Contact sheet: python sheet.py [--width N] out.png a.png b.png ...

2 columns. Cells are 960 px wide by default (--width overrides, e.g. 880 for legibility sheets) and keep the
aspect ratio of the first image (16:9 stills -> 960x540 exactly as before; 1200x500 Droste stills -> 960x400).
"""
import sys
from PIL import Image, ImageDraw

args = sys.argv[1:]
cw = 960
if "--width" in args:
    i = args.index("--width")
    cw = int(args[i + 1])
    del args[i : i + 2]
out, files = args[0], args[1:]
cols = 2
with Image.open(files[0]) as im0:
    w0, h0 = im0.size
ch = round(cw * h0 / w0)
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cw * cols, (ch + 28) * rows), "white")
d = ImageDraw.Draw(sheet)
for i, fn in enumerate(files):
    im = Image.open(fn).convert("RGB").resize((cw, ch))
    x, y = (i % cols) * cw, (i // cols) * (ch + 28)
    sheet.paste(im, (x, y + 28))
    d.text((x + 8, y + 6), fn.replace("\\", "/").split("/")[-1], fill="black")
sheet.save(out)
