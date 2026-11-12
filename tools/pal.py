"""DOSYA palette + tiny art toolkit.

Palette is built from named ramps so sprite code can say "the 4th green"
instead of hunting for a magic index. Output is 6-bit VGA DAC values.
"""
from PIL import Image

# --- ramp definitions: list of RGB stops (0..255), sampled to N entries -------

RAMPS = {
    # name        stops                                        count
    "void":      ([(8, 6, 14), (30, 22, 40), (52, 40, 64)], 10),
    "grey":      ([(20, 20, 24), (110, 110, 118), (245, 245, 245)], 16),
    "white":     ([(150, 148, 140), (250, 248, 236)], 10),
    "skin":      ([(120, 68, 52), (222, 160, 118), (255, 214, 178)], 12),
    "red":       ([(70, 10, 16), (168, 26, 32), (238, 82, 66)], 12),
    "blood":     ([(38, 4, 8), (96, 12, 16), (150, 28, 26)], 7),
    "orange":    ([(96, 44, 8), (216, 116, 24), (255, 186, 90)], 10),
    "wood":      ([(44, 26, 16), (108, 66, 36), (168, 118, 72)], 10),
    "dirt":      ([(34, 22, 16), (92, 62, 38), (150, 112, 74)], 10),
    "yellow":    ([(110, 82, 8), (226, 186, 30), (255, 244, 150)], 10),
    "hay":       ([(96, 74, 20), (186, 152, 52), (238, 214, 128)], 7),
    "green":     ([(16, 44, 18), (44, 108, 40), (126, 186, 70)], 12),
    "darkgreen": ([(6, 22, 12), (22, 58, 30), (46, 96, 50)], 7),
    "sky":       ([(24, 40, 96), (74, 128, 200), (168, 214, 250)], 12),
    "blue":      ([(10, 18, 60), (44, 78, 168), (110, 158, 236)], 10),
    "navy":      ([(6, 8, 26), (20, 28, 62), (40, 54, 104)], 7),
    "purple":    ([(30, 12, 44), (78, 34, 110), (140, 80, 178)], 8),
    "pink":      ([(110, 34, 66), (208, 96, 130), (255, 174, 196)], 8),
    "teal":      ([(8, 44, 48), (26, 108, 110), (76, 178, 172)], 8),
    "metal":     ([(28, 30, 34), (98, 104, 116), (188, 196, 208)], 8),
    "gold":      ([(96, 60, 6), (204, 148, 20), (255, 226, 120)], 7),
    "fire":      ([(120, 16, 8), (238, 116, 20), (255, 232, 150)], 8),
}

PAL = {}
ORDER = []


def _build():
    idx = 1  # 0 stays pure black / transparent
    for name, (stops, n) in RAMPS.items():
        for i in range(n):
            t = i / (n - 1) if n > 1 else 0.0
            seg = t * (len(stops) - 1)
            k = min(int(seg), len(stops) - 2)
            f = seg - k
            a, b = stops[k], stops[k + 1]
            rgb = tuple(int(round(a[c] + (b[c] - a[c]) * f)) for c in range(3))
            PAL["%s%d" % (name, i)] = idx
            ORDER.append((idx, rgb))
            idx += 1
    return idx


_used = _build()

# convenience aliases
BLACK = 0
TRANSPARENT = 0


def pal_rgb():
    """256*3 bytes of 6-bit DAC values."""
    out = bytearray(768)
    for i, (r, g, b) in ORDER:
        out[i * 3 + 0] = min(63, r >> 2)
        out[i * 3 + 1] = min(63, g >> 2)
        out[i * 3 + 2] = min(63, b >> 2)
    return out


def rgb24():
    """256*3 bytes, 8-bit, for previews."""
    out = bytearray(768)
    for i, (r, g, b) in ORDER:
        out[i * 3 + 0] = r
        out[i * 3 + 1] = g
        out[i * 3 + 2] = b
    return out


def C(name):
    return PAL[name]


# --- ramp introspection, used to build darker "background" copies of tiles ---

RAMP_INFO = {}      # palette index -> (ramp name, step, count)
for _name, (_stops, _n) in RAMPS.items():
    for _i in range(_n):
        RAMP_INFO[PAL["%s%d" % (_name, _i)]] = (_name, _i, _n)


def dim_index(idx, steps=3):
    """Step down a ramp, for background tiles. Index 0 stays transparent."""
    if idx == 0:
        return 0
    info = RAMP_INFO.get(idx)
    if not info:
        return idx
    name, i, n = info
    return PAL["%s%d" % (name, max(0, i - steps))]


class Canvas:
    """Indexed 8-bit canvas."""

    def __init__(self, w, h, fill=0):
        self.w, self.h = w, h
        self.px = bytearray([fill]) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y * self.w + x]
        return 0

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c)

    def hline(self, x0, x1, y, c):
        for x in range(x0, x1 + 1):
            self.set(x, y, c)

    def vline(self, x, y0, y1, c):
        for y in range(y0, y1 + 1):
            self.set(x, y, c)

    def blit(self, other, dx, dy, skip_zero=True):
        for y in range(other.h):
            for x in range(other.w):
                c = other.px[y * other.w + x]
                if skip_zero and c == 0:
                    continue
                self.set(dx + x, dy + y, c)

    def flip_h(self):
        out = Canvas(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                out.px[y * self.w + (self.w - 1 - x)] = self.px[y * self.w + x]
        return out

    def from_ascii(self, rows, legend):
        """legend: char -> palette key or raw index."""
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "." or ch == " ":
                    continue
                v = legend[ch]
                self.set(x, y, PAL[v] if isinstance(v, str) else v)
        return self

    def to_image(self):
        rgb = rgb24()
        im = Image.new("RGB", (self.w, self.h))
        px = im.load()
        for y in range(self.h):
            for x in range(self.w):
                c = self.px[y * self.w + x]
                px[x, y] = (rgb[c * 3], rgb[c * 3 + 1], rgb[c * 3 + 2])
        return im


def sheet(canvases, scale=4, cols=8, bg=(30, 30, 40)):
    """Contact sheet of canvases, scaled up for eyeballing."""
    if not canvases:
        return Image.new("RGB", (10, 10))
    cw = max(c.w for c in canvases) + 2
    ch = max(c.h for c in canvases) + 2
    cols = min(cols, len(canvases))
    rows = (len(canvases) + cols - 1) // cols
    out = Image.new("RGB", (cols * cw, rows * ch), bg)
    for i, c in enumerate(canvases):
        ox = (i % cols) * cw + 1
        oy = (i // cols) * ch + 1
        out.paste(c.to_image(), (ox, oy))
    return out.resize((out.width * scale, out.height * scale), Image.NEAREST)
