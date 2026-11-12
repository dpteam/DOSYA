"""Build DOSYA.

  python tools/build.py host   -> native binary, for tests and PPM frames
  python tools/build.py dos    -> real DJGPP .EXE for DOSBox
  python tools/build.py all    -> both

Generated sources live in build/gen and are regenerated on every build, because
stale generated assets are how you end up debugging a sprite you deleted.
"""
import os
import platform
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "build", "gen")
OBJ = os.path.join(ROOT, "build", "obj")
DIST = os.path.join(ROOT, "dist")
FRAMES = os.path.join(ROOT, "build", "frames")

SOURCES = ["video.c", "render.c", "sound.c", "game.c", "main.c"]
GEN_SOURCES = ["assets.c", "levels.c", "font.c"]

GEN_SCRIPTS = ["genpal.py", "art_all.py", "gen_tiles.py",
               "genfont.py", "genstrings.py", "genlevels.py"]

WINDOWS = platform.system() == "Windows"
EXE = ".exe" if WINDOWS else ""


def run(cmd, **kw):
    printable = " ".join(cmd) if isinstance(cmd, list) else cmd
    print("  " + printable)
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        raise SystemExit("build failed (%d): %s" % (r.returncode, printable))
    return r


def gen_assets():
    for script in GEN_SCRIPTS:
        print("[gen] " + script)
        run([sys.executable, os.path.join(ROOT, "tools", script)],
            cwd=ROOT, stdout=subprocess.DEVNULL)


def find_djgpp():
    """Locate the DJGPP root, whatever the archive layout was.

    The MinGW zip nests everything one level deeper (djgpp/djgpp/bin) than the
    Linux and macOS tarballs (djgpp/bin), so both are probed rather than
    assumed. Returns None if no toolchain is present.
    """
    candidates = [
        os.path.join(ROOT, "vendor", "djgpp", "djgpp"),
        os.path.join(ROOT, "vendor", "djgpp"),
    ]
    for root in candidates:
        cc = os.path.join(root, "bin", "i586-pc-msdosdjgpp-gcc" + EXE)
        if os.path.exists(cc):
            return root
    return None


def djgpp_env(root):
    env = dict(os.environ)
    sep = ";" if WINDOWS else ":"
    env["PATH"] = sep.join([
        os.path.join(root, "i586-pc-msdosdjgpp", "bin"),
        os.path.join(root, "bin"),
        env.get("PATH", ""),
    ])
    env["GCC_EXEC_PREFIX"] = os.path.join(root, "lib", "gcc") + os.sep
    env["DJDIR"] = os.path.join(root, "i586-pc-msdosdjgpp")
    return env


def build_host():
    os.makedirs(OBJ, exist_ok=True)
    os.makedirs(FRAMES, exist_ok=True)

    cc = ["gcc", "-O2", "-Wall", "-Wno-unused-parameter",
          "-DDOSYA_HOST", "-Isrc", "-I" + GEN]
    exe = os.path.join(ROOT, "build", "dosya_host" + EXE)

    objs = compile_all(cc, None, "host")
    run(cc + objs + ["-o", exe])
    print("built:", exe, os.path.getsize(exe), "bytes")
    return exe


def build_dos():
    root = find_djgpp()
    if root is None:
        raise SystemExit(
            "DJGPP not found in vendor/. Run: python tools/setup.py")

    os.makedirs(OBJ, exist_ok=True)
    os.makedirs(DIST, exist_ok=True)

    env = djgpp_env(root)
    cc = [os.path.join(root, "bin", "i586-pc-msdosdjgpp-gcc" + EXE),
          "-O2", "-Wall", "-Wno-unused-parameter", "-fno-strict-aliasing",
          "-Isrc", "-I" + GEN]
    exe = os.path.join(DIST, "DOSYA.EXE")

    objs = compile_all(cc, env, "dos")
    run(cc + objs + ["-o", exe], env=env)
    print("built:", exe, os.path.getsize(exe), "bytes")

    # CWSDPMI must sit next to the EXE: DOSBox and a bare DOS box have no DPMI
    # host of their own, and without it the game dies with
    # "no DPMI - Get csdpmi*b.zip" before drawing a single pixel.
    src = os.path.join(ROOT, "vendor", "csdpmi", "bin", "CWSDPMI.EXE")
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(DIST, "CWSDPMI.EXE"))
        print("copied CWSDPMI.EXE")
    else:
        print("WARNING: vendor/csdpmi/bin/CWSDPMI.EXE missing, "
              "run tools/setup.py")
    return exe


def compile_all(cc, env, kind):
    objs = []
    for src in SOURCES:
        obj = os.path.join(OBJ, "%s.%s.o" % (os.path.splitext(src)[0], kind))
        run(cc + ["-c", os.path.join(ROOT, "src", src), "-o", obj], env=env)
        objs.append(obj)
    for src in GEN_SOURCES:
        obj = os.path.join(OBJ, "%s.%s.o" % (os.path.splitext(src)[0], kind))
        run(cc + ["-c", os.path.join(GEN, src), "-o", obj], env=env)
        objs.append(obj)
    return objs


def build(kind):
    gen_assets()
    if kind == "host":
        return build_host()
    if kind == "dos":
        return build_dos()
    if kind == "all":
        build_host()
        return build_dos()
    raise SystemExit("unknown target %r (host|dos|all)" % kind)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "host")
