"""Render every screen of the game to a contact sheet.

Uses the host build with a script that walks the state machine:
title -> intro -> play -> death -> level done -> win.

  python tools/screens.py
"""
import os
import platform
import subprocess
import sys
import glob
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = os.path.join(ROOT, "build", "frames")
OUT = os.path.join(ROOT, "tools", "screens.png")
HOST = os.path.join(ROOT, "build",
                    "dosya_host.exe" if platform.system() == "Windows"
                    else "dosya_host")

SPACE, ENTER, ESC, P = 0x39, 0x1C, 0x01, 0x19
LEFT, RIGHT = 0x4B, 0x4D


def write_script(path):
    ev = []
    # title -> intro
    ev.append((4, SPACE))
    ev.append((6, SPACE | 0x80))
    # intro: wait, then start
    ev.append((140, SPACE))
    ev.append((142, SPACE | 0x80))
    # play: pause for a beat to grab the pause screen
    ev.append((300, P))
    ev.append((302, P | 0x80))
    ev.append((380, P))
    ev.append((382, P | 0x80))
    # walk into the first hole on purpose to capture the death screen
    ev.append((420, RIGHT))
    ev.sort()
    with open(path, "w", encoding="ascii") as f:
        for fr, k in ev:
            f.write("%d %02x\n" % (fr, k))


def main():
    os.makedirs(FRAMES, exist_ok=True)
    for f in glob.glob(os.path.join(FRAMES, "*.ppm")):
        os.remove(f)

    script = os.path.join(ROOT, "build", "screens.txt")
    write_script(script)

    env = dict(os.environ)
    env["DOSYA_SCRIPT"] = script
    env["DOSYA_DUMP_EVERY"] = "20"
    env["DOSYA_MAX_FRAMES"] = "900"
    exe = HOST
    subprocess.run([exe], env=env, cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    files = sorted(glob.glob(os.path.join(FRAMES, "*.ppm")))
    picks = [files[i] for i in (0, 6, 12, 15, 24, 30) if i < len(files)]
    if not picks:
        print("no frames")
        return
    cols = 3
    w, h = 320, 200
    rows = (len(picks) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h))
    for i, f in enumerate(picks):
        sheet.paste(Image.open(f), ((i % cols) * w, (i // cols) * h))
    sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
    sheet.save(OUT)
    print("wrote", OUT, "from", len(files), "frames")


if __name__ == "__main__":
    main()
