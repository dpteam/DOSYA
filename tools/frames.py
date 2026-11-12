"""Convert dumped PPM frames to a contact sheet PNG for eyeballing."""
import os
import sys
import glob
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = os.path.join(ROOT, "build", "frames")


def main(pattern="f*.ppm", out="tools/prev_frames.png", cols=4, scale=1, limit=16):
    files = sorted(glob.glob(os.path.join(FRAMES, pattern)))[:limit]
    if not files:
        print("no frames")
        return
    ims = [Image.open(f) for f in files]
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    if scale != 1:
        sheet = sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)
    sheet.save(os.path.join(ROOT, out))
    print("wrote", out, sheet.size, "from", len(files), "frames")


if __name__ == "__main__":
    a = sys.argv[1:]
    pat = a[0] if len(a) > 0 else "f*.ppm"
    out = a[1] if len(a) > 1 else "tools/prev_frames.png"
    cols = int(a[2]) if len(a) > 2 else 4
    scale = int(a[3]) if len(a) > 3 else 1
    limit = int(a[4]) if len(a) > 4 else 16
    main(pat, out, cols, scale, limit)
