"""Pack the DOS release zip.

  python tools/package.py <version>   ->  dosya-<version>.zip in the repo root

Uses Python's zipfile instead of shelling out to `zip`, because the build
already requires Python and `zip` is not guaranteed to exist everywhere (it is
missing on a stock Debian, for one). The PLAY.txt that ships inside is written
here, in CP866, so it is readable on a real DOS machine with TYPE.
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

PLAY_TXT = """\
ДОСЯ и автобус
==============

1. Скопируйте все файлы в одну папку на жёстком диске.
2. Запустите DOSYA.EXE

Управление:
  Стрелки / A, D  - идти
  Пробел          - прыжок (держите дольше - прыжок выше)
  Z / X / Ctrl    - кинуть навоз
  P               - пауза
  Esc             - выход

CWSDPMI.EXE должен лежать рядом с DOSYA.EXE.
Без него игра сообщит "no DPMI - Get csdpmi*b.zip".

Совсем древняя DOS покажет этот файл кракозябрами: он в CP866,
как и всё остальное здесь.
"""


def main(version):
    name = "dosya-%s" % version
    out = os.path.join(ROOT, name + ".zip")

    required = ["DOSYA.EXE", "CWSDPMI.EXE"]
    for f in required:
        p = os.path.join(DIST, f)
        if not os.path.exists(p):
            raise SystemExit("missing %s - run tools/build.py dos first" % p)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in required:
            z.write(os.path.join(DIST, f), "%s/%s" % (name, f))
        z.write(os.path.join(ROOT, "README.md"), "%s/README.md" % name)
        # CP866 on purpose: that is what DOS displays without help.
        z.writestr("%s/PLAY.txt" % name, PLAY_TXT.encode("cp866"))

    size = os.path.getsize(out)
    print("wrote %s (%d bytes)" % (os.path.basename(out), size))
    with zipfile.ZipFile(out) as z:
        for i in z.infolist():
            print("  %-28s %6d" % (i.filename, i.file_size))
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python tools/package.py <version>")
    main(sys.argv[1])
