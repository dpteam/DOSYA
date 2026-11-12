"""On-demand downloads for things the build needs but should not commit.

The only thing here right now is GNU Unifont: 936 KB, needed by
tools/genfont.py, and far too big to put in git.

Why this module exists at all: the font used to be fetched only by
tools/setup.py, which also downloads the 120 MB DJGPP toolchain. That meant a
plain `build.py host` -- and the CI smoke job, which has no toolchain -- died
with FileNotFoundError on vendor/unifont.hex.gz. Now every entry point that
needs the font asks for it here and it fetches itself.
"""
import gzip
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "vendor")

UNIFONT_VERSION = "15.1.05"
UNIFONT_URL = ("https://unifoundry.com/pub/unifont/unifont-%s/"
               "font-builds/unifont-%s.hex.gz"
               % (UNIFONT_VERSION, UNIFONT_VERSION))


def download(url, dest, quiet=False):
    """Fetch url to dest atomically.

    Writes to dest + '.part' and renames, so an interrupted run can never
    leave a half-written file that looks valid to the next build.
    """
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    if not quiet:
        print("  downloading %s" % url)
    try:
        with urllib.request.urlopen(url, timeout=120) as r, \
                open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
    except (urllib.error.URLError, OSError) as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise SystemExit(
            "could not download %s\n  %s\n"
            "  If you are offline, put the file at:\n    %s"
            % (url, e, dest))
    os.replace(tmp, dest)
    if not quiet:
        print("  got %d bytes -> %s" % (os.path.getsize(dest),
                                        os.path.relpath(dest, ROOT)))
    return dest


def unifont_path():
    return os.path.join(VENDOR, "unifont.hex.gz")


def _unifont_is_valid(path):
    """A real Unifont hex dump has tens of thousands of '<hex>:<rows>' lines.

    Checking one is not enough: a truncated download can still decompress the
    first few lines and then fail halfway through font generation.
    """
    if not os.path.exists(path) or os.path.getsize(path) < 100_000:
        return False
    try:
        n = 0
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    n += 1
                    if n >= 50_000:
                        return True
        # Reaching here means we read the whole file without error.
        return n > 10_000
    except (OSError, EOFError, UnicodeDecodeError):
        return False


def ensure_unifont(quiet=False):
    """Return a path to a valid unifont.hex.gz, downloading it if needed."""
    path = unifont_path()
    if _unifont_is_valid(path):
        return path
    if os.path.exists(path):
        print("  vendor/unifont.hex.gz is corrupt or truncated, refetching")
        os.remove(path)
    if not quiet:
        print("[fetch] GNU Unifont %s (one time, ~1 MB)" % UNIFONT_VERSION)
    return download(UNIFONT_URL, path, quiet=quiet)


if __name__ == "__main__":
    p = ensure_unifont()
    print("unifont ready:", p)
    sys.exit(0)
