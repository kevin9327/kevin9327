"""Contact sheet: python sheet.py out.png a.png b.png ... (2 columns, 960 px wide cells)."""
import sys
from PIL import Image, ImageDraw

out, files = sys.argv[1], sys.argv[2:]
cw, ch, cols = 960, 540, 2
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cw * cols, (ch + 28) * rows), "white")
d = ImageDraw.Draw(sheet)
for i, fn in enumerate(files):
    im = Image.open(fn).convert("RGB").resize((cw, ch))
    x, y = (i % cols) * cw, (i // cols) * (ch + 28)
    sheet.paste(im, (x, y + 28))
    d.text((x + 8, y + 6), fn.replace("\\", "/").split("/")[-1], fill="black")
sheet.save(out)
