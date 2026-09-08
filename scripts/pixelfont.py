"""
pixelfont.py -- a 5x7 bitmap font compiled to SVG paths.

An <img>-loaded SVG cannot fetch a webfont, so every glyph on these assets is geometry: one path per
glyph in <defs>, vertical runs merged so a letter stem is one subpath, one <use> per character.
Pixel-identical on every OS, and readable far below the size a system font mushes at.
"""

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
    "J": "..### ...#. ...#. ...#. ...#. #..#. .##..",
    "K": "#...# #..#. #.#.. ##... #.#.. #..#. #...#",
    "L": "#.... #.... #.... #.... #.... #.... #####",
    "M": "#...# ##.## #.#.# #.#.# #...# #...# #...#",
    "N": "#...# ##..# #.#.# #..## #...# #...# #...#",
    "O": ".###. #...# #...# #...# #...# #...# .###.",
    "P": "####. #...# #...# ####. #.... #.... #....",
    "Q": ".###. #...# #...# #...# #.#.# #..#. .##.#",
    "R": "####. #...# #...# ####. #.#.. #..#. #...#",
    "S": ".#### #.... #.... .###. ....# ....# ####.",
    "T": "##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..",
    "U": "#...# #...# #...# #...# #...# #...# .###.",
    "V": "#...# #...# #...# #...# #...# .#.#. ..#..",
    "W": "#...# #...# #...# #.#.# #.#.# ##.## #...#",
    "X": "#...# #...# .#.#. ..#.. .#.#. #...# #...#",
    "Y": "#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..",
    "Z": "##### ....# ...#. ..#.. .#... #.... #####",
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
    ",": "..... ..... ..... ..... .##.. .##.. .#...",
    "/": "....# ....# ...#. ..#.. .#... #.... #....",
    "%": "##..# ##.#. ...#. ..#.. .#... .#.## #..##",
    "^": "..#.. ..#.. .#.#. .#.#. #...# #...# #####",   # delta
}
_PUNCT = {"(": "clp", ")": "crp", ".": "cdot", ",": "ccom", "-": "cdash", ":": "ccol", "/": "csl", "%": "cpct", "^": "cdel"}
GID = {c: (f"c{c}" if c.isalnum() else _PUNCT[c]) for c in FONT}
ADV = 6   # 5 columns + 1 gap, in glyph units


def rows_of(ch):
    return FONT[ch].split()


def glyph_path(rows):
    rows = rows.split() if isinstance(rows, str) else rows
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


def defs(chars=None):
    """the glyph <path> defs for the given characters (default: the whole font)"""
    return "".join(f'<path id="{GID[ch]}" d="{glyph_path(FONT[ch])}"/>' for ch in (chars or FONT) if ch in FONT)


def _q(v):
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


def width(s, scale=1):
    return (len(s) * ADV - 1) * scale


def text(s, x, y, scale, fill, extra="", anchor="start"):
    """one <use> per glyph; anchor start|middle|end; (x, y) is the top-left / top-centre / top-right"""
    w = width(s, scale)
    if anchor == "middle":
        x -= w / 2
    elif anchor == "end":
        x -= w
    out = [f'<g transform="translate({_q(x)} {_q(y)}) scale({scale})" fill="{fill}"{extra}>']
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        out.append(f'<use href="#{GID[ch]}" xlink:href="#{GID[ch]}" x="{i * ADV}"/>')
    out.append("</g>")
    return "".join(out)


def raster(lines, cols, rows, gap=3):
    """render lines of text into a cols x rows bitmap (list of lists of 0/1), centred"""
    grid = [[0] * cols for _ in range(rows)]
    total_h = len(lines) * 7 + (len(lines) - 1) * gap
    y0 = (rows - total_h) // 2
    for li, s in enumerate(lines):
        w = len(s) * ADV - 1
        x0 = (cols - w) // 2
        for ci, ch in enumerate(s):
            if ch == " ":
                continue
            for r, row in enumerate(rows_of(ch)):
                for c, bit in enumerate(row):
                    if bit == "#":
                        grid[y0 + li * (7 + gap) + r][x0 + ci * ADV + c] = 1
    return grid
