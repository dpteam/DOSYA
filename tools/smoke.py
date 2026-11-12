"""Smoke test: run the autopilot and assert the game can actually be finished.

This is the test CI runs. It builds nothing -- it expects build/dosya_host.exe
to exist -- and it fails loudly if the bot cannot clear all three levels.

    python tools/smoke.py

Exit code 0 means: every level was reached, and the win screen was reached.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, "build", "dosya_host.exe")
SCRIPT = os.path.join(ROOT, "build", "smoke.txt")

# Scancodes. Two spaces take us from the title through the intro into play.
SPACE = 0x39

ST_TITLE, ST_INTRO, ST_PLAY, ST_DEAD, ST_LEVEL_DONE, ST_WIN, ST_GAMEOVER = range(7)

STATE_NAMES = {
    ST_TITLE: "TITLE", ST_INTRO: "INTRO", ST_PLAY: "PLAY", ST_DEAD: "DEAD",
    ST_LEVEL_DONE: "LEVEL_DONE", ST_WIN: "WIN", ST_GAMEOVER: "GAMEOVER",
}


def write_script():
    os.makedirs(os.path.dirname(SCRIPT), exist_ok=True)
    with open(SCRIPT, "w", encoding="ascii") as f:
        # frame, scancode. The high bit (0x80) is a release.
        f.write("5 39\n")     # press space
        f.write("7 b9\n")     # release
        f.write("20 39\n")    # press again -> leave the intro
        f.write("22 b9\n")


def run():
    env = dict(os.environ)
    env["DOSYA_SCRIPT"] = SCRIPT
    env["DOSYA_AUTOPILOT"] = "1"
    env["DOSYA_DBG"] = "1"           # state transitions only
    env["DOSYA_DUMP_EVERY"] = "0"    # no PPM spam
    env["DOSYA_MAX_FRAMES"] = "80000"

    print("running", os.path.basename(EXE), "with autopilot...")
    p = subprocess.run([EXE], cwd=ROOT, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, timeout=300)
    return p.stderr


TICK = re.compile(r"\[tick\] state (\d) -> (\d) lvl=(\d)")


def check(stderr):
    transitions = [(int(a), int(b), int(c)) for a, b, c in TICK.findall(stderr)]
    if not transitions:
        print("FAIL: the game never changed state. Did it even start?")
        return False

    levels_cleared = set()
    reached_win = False
    died = 0
    game_over = False

    for _src, dst, lvl in transitions:
        if dst == ST_LEVEL_DONE:
            levels_cleared.add(lvl)
            print("  level %d cleared (%s)" % (lvl + 1, STATE_NAMES[dst]))
        elif dst == ST_WIN:
            # The final level skips LEVEL_DONE and goes straight to the win
            # screen, so reaching WIN also means "last level cleared".
            levels_cleared.add(lvl)
            reached_win = True
            print("  WIN screen reached")
        elif dst == ST_DEAD:
            died += 1
        elif dst == ST_GAMEOVER:
            game_over = True

    print()
    print("  deaths: %d, game overs: %d" % (died, game_over))
    print("  levels cleared: %s" % sorted(x + 1 for x in levels_cleared))

    ok = True
    if len(levels_cleared) != 3:
        print("FAIL: expected 3 levels cleared, got %d" % len(levels_cleared))
        ok = False
    if not reached_win:
        print("FAIL: the win screen was never reached")
        ok = False
    if game_over:
        print("FAIL: the autopilot ran out of lives")
        ok = False
    return ok


def main():
    if not os.path.exists(EXE):
        print("FAIL: %s missing. Run: python tools/build.py host" % EXE)
        return 1
    write_script()
    stderr = run()
    ok = check(stderr)
    print()
    print("SMOKE TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
