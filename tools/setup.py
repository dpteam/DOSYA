"""One-time setup: fetch DJGPP, CWSDPMI and the font source.

Everything lands in vendor/ and is gitignored. Safe to re-run: existing files
are skipped, so a half-finished download can be repaired by running it again.

    python tools/setup.py            # everything (needs ~120 MB for DJGPP)
    python tools/setup.py --font     # just GNU Unifont (~1 MB)

`--font` exists for CI and for anyone who only wants the host build: the DOS
toolchain is not needed to run the tests.

Picks the right DJGPP build for the host: MinGW on Windows, linux64 elsewhere.
"""
import os
import platform
import sys
import tarfile
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "vendor")

BASE = "https://github.com/andrewwutw/build-djgpp/releases/download/v3.4/"
CWSDPMI_URL = "https://www.delorie.com/pub/djgpp/current/v2misc/csdpmi7b.zip"


def djgpp_archive():
    if platform.system() == "Windows":
        return BASE + "djgpp-mingw-gcc1220-standalone.zip"
    if platform.system() == "Darwin":
        return BASE + "djgpp-osx-gcc1220.tar.bz2"
    return BASE + "djgpp-linux64-gcc1220.tar.bz2"


def fetch_archive(url, dest):
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


def setup_toolchain():
    print("[1/2] DJGPP (%s)" % platform.system())
    url = djgpp_archive()
    arc = os.path.join(VENDOR, os.path.basename(url))
    fetch_archive(url, arc)
    unpack(arc, os.path.join(VENDOR, "djgpp"))

    print("[2/2] CWSDPMI")
    arc = os.path.join(VENDOR, "csdpmi.zip")
    fetch_archive(CWSDPMI_URL, arc)
    unpack(arc, os.path.join(VENDOR, "csdpmi"))


def setup_font():
    print("[font] GNU Unifont")
    fetch.ensure_unifont()


def main(argv):
    os.makedirs(VENDOR, exist_ok=True)

    if "--font" in argv or "--font-only" in argv:
        setup_font()
        print()
        print("font ready. next: python tools/build.py host")
        return 0

    setup_toolchain()
    setup_font()
    print()
    print("setup done. next: python tools/build.py dos")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
