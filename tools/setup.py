"""One-time setup: fetch DJGPP, CWSDPMI and the font source.

Everything lands in vendor/ and is gitignored. Safe to re-run: existing files
are skipped, so a half-finished download can be repaired by running it again.

    python tools/setup.py

Picks the right DJGPP build for the host: MinGW on Windows, linux64 elsewhere.
"""
import os
import platform
import sys
import tarfile
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "vendor")

BASE = "https://github.com/andrewwutw/build-djgpp/releases/download/v3.4/"
CWSDPMI_URL = "https://www.delorie.com/pub/djgpp/current/v2misc/csdpmi7b.zip"
UNIFONT_URL = ("https://unifoundry.com/pub/unifont/unifont-15.1.05/"
               "font-builds/unifont-15.1.05.hex.gz")


def djgpp_archive():
    if platform.system() == "Windows":
        return BASE + "djgpp-mingw-gcc1220-standalone.zip"
    if platform.system() == "Darwin":
        return BASE + "djgpp-osx-gcc1220.tar.bz2"
    return BASE + "djgpp-linux64-gcc1220.tar.bz2"


def fetch(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print("  have", os.path.basename(dest))
        return
    print("  downloading", url)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    urllib.request.urlretrieve(url, tmp)
    os.replace(tmp, dest)
    print("  got %d bytes" % os.path.getsize(dest))


def unpack(src, dest):
    marker = os.path.join(dest, ".done")
    if os.path.exists(marker):
        print("  have", os.path.basename(dest))
        return
    print("  extracting", os.path.basename(src))
    os.makedirs(dest, exist_ok=True)
    if src.endswith(".zip"):
        with zipfile.ZipFile(src) as z:
            z.extractall(dest)
    else:
        with tarfile.open(src, "r:bz2") as t:
            t.extractall(dest)
    open(marker, "w").close()


def main():
    os.makedirs(VENDOR, exist_ok=True)

    print("[1/3] DJGPP (%s)" % platform.system())
    url = djgpp_archive()
    arc = os.path.join(VENDOR, os.path.basename(url))
    fetch(url, arc)
    unpack(arc, os.path.join(VENDOR, "djgpp"))

    print("[2/3] CWSDPMI")
    arc = os.path.join(VENDOR, "csdpmi.zip")
    fetch(CWSDPMI_URL, arc)
    unpack(arc, os.path.join(VENDOR, "csdpmi"))

    print("[3/3] Unifont")
    fetch(UNIFONT_URL, os.path.join(VENDOR, "unifont.hex.gz"))

    print()
    print("setup done. next: python tools/build.py dos")


if __name__ == "__main__":
    main()
