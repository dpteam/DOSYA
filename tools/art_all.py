"""Every sprite in the game, plus the exporter that turns them into C arrays.

Run:  python tools/art_all.py
Out:  build/gen/assets.h  (palette, tiles, sprites, sprite table)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pix  # noqa: E402
import pal  # noqa: E402
import gen_tiles  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "build", "gen")

L = {
    "w": "white8", "W": "white6", "v": "white3",
    "r": "red8", "R": "red6", "q": "red4", "Q": "red2",
    "o": "orange6", "O": "orange4",
    "y": "yellow6", "Y": "yellow4", "j": "yellow2",
    "x": "skin8", "X": "skin6", "z": "skin4",
    "b": "wood4", "B": "wood2",
    "d": "green7", "D": "green5", "g": "green3",
    "k": "void0", "K": "grey1", "m": "grey3",
    "n": "dirt5", "N": "dirt3",
    "M": "metal4", "u": "blue6", "U": "blue4",
    "p": "pink6", "P": "pink4",
    "t": "teal5", "T": "teal3",
    "s": "grey5", "S": "grey3",
    "a": "white9", "A": "white6",
    "h": "hay5",
}

# --------------------------------------------------------------- DOSYA -------

HEAD = [
    "................",
    ".....rrrrrr.....",
    "....rrrrrrrr....",
    "...rrrrrrrrrr...",
    "...rrRrrrrrRr...",
    "...rRxxxxxxRr...",
    "...rrxxxxxxrr...",
    "...rrxkxkxkrr...",
    "...rrxxxxxxrr...",
    "...rrxxQQxxrr...",
    "....rxxxxxxr....",
]

DRESS = [
    "....dddddddd....",
    "..dddaaaaaaddd..",
    "..ddaaaaaaaadd..",
    "..ddaaaaaaaadd..",
    "..ddaaaaaaaadd..",
    ".dddddddddddddd.",
    ".dddddddddddddd.",
]

# legs: (left_x, right_x) column of each 3-wide leg, plus shoe offset
LEG_POSES = [
    (3, 10, 0),   # stand
    (2, 9, 0),    # walk contact
    (4, 8, 0),    # passing
    (4, 9, 0),    # walk contact other side
    (3, 11, 1),   # stride
]


def leg_rows(lx, rx, lift=0):
    rows = []
    for i in range(4):
        row = ["."] * 16
        if not (lift and i >= 4 - lift):
            for k in range(3):
                row[lx + k] = "x"
        for k in range(3):
            row[rx + k] = "x"
        rows.append("".join(row))
    for i in range(2):
        row = ["."] * 16
        if not (lift and i >= 2 - lift):
            for k in range(4):
                if 0 <= lx - 1 + k < 16:
                    row[lx - 1 + k] = "b"
        for k in range(4):
            if rx - 1 + k < 16:
                row[rx - 1 + k] = "b"
        rows.append("".join(row))
    return rows


def dosya_stand():
    return list(HEAD) + list(DRESS) + leg_rows(3, 10)


def dosya_walk(f):
    lx, rx, lift = LEG_POSES[f]
    return list(HEAD) + list(DRESS) + leg_rows(lx, rx, lift)


def dosya_jump():
    legs = [
        "..xxx....xxx....",
        "..xxx....xxx....",
        ".xxx......xxx...",
        ".bbb......bbb...",
        "bbbb......bbbb..",
        "bbbb......bbbb..",
    ]
    return list(HEAD) + list(DRESS) + legs


def dosya_fall():
    legs = [
        "...xxx..xxx.....",
        "..xxx....xxx....",
        "..xxx....xxx....",
        "..bbb....bbb....",
        ".bbbb....bbbb...",
        ".bbbb....bbbb...",
    ]
    return list(HEAD) + list(DRESS) + legs


def dosya_hurt():
    rows = list(HEAD)
    rows[7] = "...rrxkxkxkrr..."
    rows[9] = "...rrxkkkkxrr..."
    return rows + list(DRESS) + [
        "..xxx......xxx..",
        ".xxx........xxx.",
        ".xxx........xxx.",
        ".bbb........bbb.",
        "bbbb........bbbb",
        "bbbb........bbbb",
    ]


def dosya_dead():
    return [
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "....rrrrrrrr....",
        "...rrrrrrrrrr...",
        "..rrxxkkkkxxrr..",
        ".dddddddddddddd.",
        "dddddddddddddddd",
        "..xxxx....xxxx..",
        "..bbb......bbb..",
        "................",
        "................",
        "................",
        "................",
        "................",
    ]


def dosya_win():
    head = list(HEAD)
    head[7] = "...rrxkxkxkrr..."
    head[9] = "...rrxaAAAxrr..."
    return head + [
        ".xxddddddddddxx.",
        ".xxdaaaaaaaddxx.",
        ".xxdaaaaaaaddxx.",
        "..ddaaaaaaaadd..",
        "..ddaaaaaaaadd..",
        ".dddddddddddddd.",
        "..xxx......xxx..",
        "..xxx......xxx..",
        "..xxx......xxx..",
        "..bbb......bbb..",
        ".bbbb......bbbb.",
        ".bbbb......bbbb.",
        "................",
    ]


# ------------------------------------------------------------- enemies -------

CHICKEN = [
    [
        "..............",
        ".....rrr......",
        "....rrrrr.....",
        "....rRRRr.....",
        "...wwwwwww....",
        "..wwwwwwwww...",
        "..wwkwwwwwwy..",
        "..wwwwwwwww...",
        "...wwwwwww....",
        "....wwwww.....",
        "....x...x.....",
        "....x...x.....",
        "...xx...xx....",
        "..............",
    ],
    [
        "..............",
        ".....rrr......",
        "....rrrrr.....",
        "....rRRRr.....",
        "...wwwwwww....",
        "..wwwwwwwww...",
        "..wwkwwwwwwy..",
        "..wwwwwwwww...",
        "...wwwwwww....",
        "....wwwww.....",
        "...x.....x....",
        "...x.....x....",
        "..xx.....xx...",
        "..............",
    ],
]

ROOSTER = [
    [
        "................",
        "......qqq.......",
        ".....rrrrq......",
        "....rrRRrrr.....",
        "....rrrrrrrr....",
        "....wwwwwwww....",
        "...wwwwwwwww....",
        "...wwkwwwwwwyo..",
        "...wwwwwwwwww...",
        "....wwwwwwww....",
        ".....wwwwww.....",
        ".....ooooo......",
        "......x..x......",
        "......x..x......",
        ".....xx..xx.....",
        "................",
    ],
    [
        "................",
        "......qqq.......",
        ".....rrrrq......",
        "....rrRRrrr.....",
        "....rrrrrrrr....",
        "....wwwwwwww....",
        "...wwwwwwwww....",
        "...wwkwwwwwwyo..",
        "...wwwwwwwwww...",
        "....wwwwwwww....",
        ".....wwwwww.....",
        ".....ooooo......",
        ".....x....x.....",
        ".....x....x.....",
        "....xx....xx....",
        "................",
    ],
]

GOAT = [
    [
        "......................",
        "..............bb......",
        ".............bbbb.....",
        "............wwwww.....",
        "...........wwwwww.....",
        "..wwwwwwwwwwwwkwww....",
        ".wwwwwwwwwwwwwwwwww...",
        ".wwwwwwwwwwwwwwwwww...",
        "..wwwwwwwwwwwwwwww....",
        "...x..x.....x..x......",
        "...x..x.....x..x......",
        "..xx..xx...xx..xx.....",
        "......................",
    ],
    [
        "......................",
        "..............bb......",
        ".............bbbb.....",
        "............wwwww.....",
        "...........wwwwww.....",
        "..wwwwwwwwwwwwkwww....",
        ".wwwwwwwwwwwwwwwwww...",
        ".wwwwwwwwwwwwwwwwww...",
        "..wwwwwwwwwwwwwwww....",
        "..x...x.......x...x...",
        "..x...x.......x...x...",
        ".xx...xx.....xx...xx..",
        "......................",
    ],
]

DED = [
    [
        "................",
        ".....KKKKKK.....",
        "....KKKKKKKK....",
        "....KKKKKKKK....",
        "....KxxxxxxK....",
        "....KxkxkxK.....",
        "....KxxxxxxK....",
        ".....KxWWxK.....",
        "....KKKKKKKK....",
        "...KKKKKKKKKK...",
        "..KKKKKKKKKKKK..",
        "..KKKKKKKKKKKK..",
        "..KKKKKKKKKKKK..",
        "..KKKKKKKKKKKK..",
        "..KKKKKKKKKKKK..",
        "...KKKKKKKKKK...",
        "...KKKK..KKKK...",
        "...KKKK..KKKK...",
        "..BBBB....BBBB..",
        "..BBBB....BBBB..",
    ],
    [
        "................",
        ".....KKKKKK.....",
        "....KKKKKKKK....",
        "....KKKKKKKK....",
        "....KxxxxxxK....",
        "....KxkxkxK.....",
        "....KxxxxxxK....",
        ".....KxWWxK.....",
        "....KKKKKKKK....",
        "...KKKKKKKKKK...",
        "..KKKKKKKKKKKK..",
        "..KKKKKKKKKKKK..",
        "..KKKKKKKKKKKK..",
        "..KKKKKKKKKKKK..",
        "..KKKKKKKKKKKK..",
        "...KKKKKKKKKK...",
        "..KKKK....KKKK..",
        "..KKKK....KKKK..",
        ".BBBB......BBBB.",
        ".BBBB......BBBB.",
    ],
]

TRACTOR = [
    [
        "................................",
        "................................",
        ".......dddddddddd...............",
        "......dddddddddddd..............",
        ".....dduuuuuuuuuud..............",
        ".....dduuUUUUUUuudd.............",
        ".....dduuuuuuuuuudd.............",
        ".....dddddddddddddd.............",
        "......MM........MM..............",
        "....MMMMMM....MMMMMM............",
        "...MMMMMMMM..MMMMMMMM...........",
        "...MMssssMM..MMssssMM...........",
        "...MMsSSsMM..MMsSSsMM...........",
        "...MMssssMM..MMssssMM...........",
        "....MMMMMM....MMMMMM............",
        "................................",
    ],
    [
        "................................",
        "................................",
        ".......dddddddddd...............",
        "......dddddddddddd..............",
        ".....dduuuuuuuuuud..............",
        ".....dduuUUUUUUuudd.............",
        ".....dduuuuuuuuuudd.............",
        ".....dddddddddddddd.............",
        "......MM........MM..............",
        "....MMMMMM....MMMMMM............",
        "...MMMMMMMM..MMMMMMMM...........",
        "...MMSSssMM..MMSSssMM...........",
        "...MMssSSMM..MMssSSMM...........",
        "...MMssssMM..MMssssMM...........",
        "....MMMMMM....MMMMMM............",
        "................................",
    ],
]

# ---------------------------------------------------------------- faces ------
# DOOM-style status bar face. Four damage states, same layout so the eyes
# never jump around while she is being murdered by poultry.

FACE_OK = [
    "................",
    "....rrrrrrrr....",
    "...rrrrrrrrrr...",
    "...rrRrrrrrRr...",
    "...rRxxxxxxRr...",
    "...rrxkxkxkrr...",
    "...rrxxxxxxrr...",
    "...rrxxxxxxrr...",
    "...rrxaAAaxrr...",
    "...rrxxxxxxrr...",
    "...rrxxxxxxrr...",
    "....rrrrrrrr....",
    ".....rrrrrr.....",
    "................",
]

FACE_HURT = [
    "................",
    "....rrrrrrrr....",
    "...rrrrrrrrrr...",
    "...rrRrrrrrRr...",
    "...rRxxxxxxRr...",
    "...rrxkxxxkrr...",
    "...rrxxPxxxrr...",
    "...rrxPxxxxrr...",
    "...rrxakkaxrr...",
    "...rrxxkkkkrr...",
    "...rrxxxxxxrr...",
    "....rrrrrrrr....",
    ".....rrrrrr.....",
    "................",
]

FACE_BAD = [
    "................",
    "....rrrrrrrr....",
    "...rrrrrrrrrr...",
    "...rrRrrrrrRr...",
    "...rRxxxxxxRr...",
    "...rrxkxxxkrr...",
    "...rrxrxxxxrr...",
    "...rrxxrxxxrr...",
    "...rrxaAAaxrr...",
    "...rrxrrrrxrr...",
    "...rrxxxxxxrr...",
    "....rrrrrrrr....",
    ".....rrrrrr.....",
    "................",
]

FACE_DEAD = [
    "................",
    "....rrrrrrrr....",
    "...rrrrrrrrrr...",
    "...rrRrrrrrRr...",
    "...rRxxxxxxRr...",
    "...rrxkxxkxrr...",
    "...rrxxkkxxrr...",
    "...rrxkxxkxrr...",
    "...rrxxAAAxrr...",
    "...rrxAAAAxrr...",
    "...rrxxxxxxrr...",
    "....rrrrrrrr....",
    ".....rrrrrr.....",
    "................",
]

# ---------------------------------------------------------------- items ------

MILK = [
    "........",
    "...ww...",
    "..wWWw..",
    "..wWWw..",
    ".wwwwww.",
    ".wWWWWw.",
    ".wWWWWw.",
    ".wWWWWw.",
    ".wWWWWw.",
    ".wwwwww.",
    "........",
]

EGG = [
    "........",
    "...ww...",
    "..wwww..",
    ".wwwwww.",
    ".wWwwWw.",
    ".wwwwww.",
    ".wwwwww.",
    "..wwww..",
    "...ww...",
    "........",
]

MANURE = [
    "..........",
    "....nn....",
    "...nNNn...",
    "..nNNNNn..",
    ".nNNNNNNn.",
    ".nNNNNNNn.",
    "..nNNNNn..",
    "...nnnn...",
    "..........",
]

SAMOGON = [
    "........",
    "..wwww..",
    "..wWWw..",
    "..wWWw..",
    ".wwwwww.",
    ".wyyyyw.",
    ".wyYYyw.",
    ".wyyyyw.",
    ".wwwwww.",
    "........",
]

# ---------------------------------------------------------------- props ------

SIGN = [
    "............",
    "...bbbbbb...",
    "..bbbbbbbb..",
    "..bbBBBBbb..",
    "..bbBBBBbb..",
    "..bbbbbbbb..",
    "...bbbbbb...",
    "....bb......",
    "....bb......",
    "....bb......",
    "...bbbb.....",
    "............",
]

BUSH = [
    "................",
    "................",
    "......gggg......",
    "....ggdddgg.....",
    "...gdddddddgg...",
    "..gdddddddddg...",
    "..gdddddddddg...",
    "..ggdddddddgg...",
    "...gggddgggg....",
    ".....gggg.......",
    "................",
]

SUNFLOWER = [
    "................",
    ".....yyyyy......",
    "....yyjjjyy.....",
    "...yyjjjjjyy....",
    "...yyjjjjjyy....",
    "....yyjjjyy.....",
    ".....yyyyy......",
    ".......d........",
    ".......d........",
    "..d....d....d...",
    "...d...d...d....",
    "....d..d..d.....",
    ".......d........",
    ".......d........",
    ".......d........",
    "......ddd.......",
]

CLOUD = [
    "......................",
    "........wwww..........",
    "......wwwwwwww........",
    "....wwwwwwwwwwww......",
    "...wwwwwwwwwwwwww.....",
    "..wwwwwwwwwwwwwwww....",
    "..wwwwwwwwwwwwwwww....",
    "...wwwwwwwwwwwwww.....",
    "......................",
]

BUS = [
    "..............................",
    "..............................",
    "...yyyyyyyyyyyyyyyyyyyyyyyy...",
    "..yyyyyyyyyyyyyyyyyyyyyyyyyy..",
    "..yuuyyuuyyuuyyuuyyuuyyuuyyy..",
    "..yuuyyuuyyuuyyuuyyuuyyuuyyy..",
    "..yyyyyyyyyyyyyyyyyyyyyyyyyy..",
    "..yyyyyyyyyyyyyyyyyyyyyyyyyy..",
    "..yyyyyyyyyyyyyyyyyyyyyyyyyy..",
    "..KKKKKKKKKKKKKKKKKKKKKKKKKK..",
    "..KK..KK..............KK..KK..",
    "...KKKK................KKKK...",
    "..............................",
]

SPRITES = {}


def add(name, rows):
    w = len(rows[0])
    for i, r in enumerate(rows):
        assert len(r) == w, "%s row %d len %d != %d" % (name, i, len(r), w)
    SPRITES[name] = rows


def build():
    add("dosya_stand", dosya_stand())
    for i in range(1, 5):
        add("dosya_walk%d" % i, dosya_walk(i))
    add("dosya_jump", dosya_jump())
    add("dosya_fall", dosya_fall())
    add("dosya_hurt", dosya_hurt())
    add("dosya_dead", dosya_dead())
    add("dosya_win", dosya_win())

    for i, r in enumerate(CHICKEN):
        add("chicken%d" % i, r)
    for i, r in enumerate(ROOSTER):
        add("rooster%d" % i, r)
    for i, r in enumerate(GOAT):
        add("goat%d" % i, r)
    for i, r in enumerate(DED):
        add("ded%d" % i, r)
    for i, r in enumerate(TRACTOR):
        add("tractor%d" % i, r)

    add("milk", MILK)
    add("egg", EGG)
    add("manure", MANURE)
    add("samogon", SAMOGON)
    add("face_ok", FACE_OK)
    add("face_hurt", FACE_HURT)
    add("face_bad", FACE_BAD)
    add("face_dead", FACE_DEAD)
    add("sign", SIGN)
    add("bush", BUSH)
    add("sunflower", SUNFLOWER)
    add("cloud", CLOUD)
    add("bus", BUS)
    return SPRITES


def c_array(name, data):
    lines = ["const unsigned char %s[] = {" % name]
    for i in range(0, len(data), 20):
        lines.append("  " + ",".join("%d" % b for b in data[i:i + 20]) + ",")
    lines.append("};")
    return "\n".join(lines)


def export():
    os.makedirs(GEN, exist_ok=True)
    spr = build()
    hdr = []
    src = []
    hdr.append("/* generated by tools/art_all.py - do not edit */")
    hdr.append("#ifndef DOSYA_ASSETS_H")
    hdr.append("#define DOSYA_ASSETS_H")
    hdr.append("")
    hdr.append("typedef struct { unsigned char w, h; const unsigned char *px; } Sprite;")
    hdr.append("")

    src.append("/* generated by tools/art_all.py - do not edit */")
    src.append('#include "assets.h"')
    src.append("")

    # palette
    src.append(c_array("g_pal", pal.pal_rgb()))
    hdr.append("extern const unsigned char g_pal[768];")
    src.append("")

    # tiles
    tiles = [fn() for _, fn in gen_tiles.TILES]
    names = [n for n, _ in gen_tiles.TILES]
    blob = bytearray()
    dimblob = bytearray()
    for t in tiles:
        blob += t.px
        dimblob += bytearray(pal.dim_index(b, 4) for b in t.px)
    src.append(c_array("g_tiles", blob))
    src.append(c_array("g_tiles_dim", dimblob))
    src.append("const char *const g_tile_names[NTILES] = {")
    src.append("  " + ",".join('"%s"' % n for n in names))
    src.append("};")
    src.append("")
    hdr.append("#define NTILES %d" % len(tiles))
    hdr.append("#define TILE_W 16")
    hdr.append("#define TILE_H 16")
    hdr.append("extern const unsigned char g_tiles[];")
    hdr.append("extern const unsigned char g_tiles_dim[];")
    hdr.append("")

    # sprites
    dims = {}
    for name in spr:
        rows = spr[name]
        w = len(rows[0])
        h = len(rows)
        # 1px transparent margin so the outline never gets clipped
        canvas = pal.Canvas(w + 2, h + 2)
        canvas.blit(pix.art(rows, L), 1, 1)
        pix.outline(canvas)
        dims[name] = (w + 2, h + 2)
        src.append(c_array("spr_%s" % name, canvas.px))
    src.append("")
    src.append("const Sprite g_sprites[NSPRITES] = {")
    for name in spr:
        w, h = dims[name]
        src.append("  { %d, %d, spr_%s }," % (w, h, name))
    src.append("};")
    src.append("")

    hdr.append("#define NSPRITES %d" % len(spr))
    hdr.append("extern const Sprite g_sprites[NSPRITES];")
    hdr.append("enum {")
    for i, name in enumerate(spr):
        hdr.append("  SPR_%s = %d," % (name.upper(), i))
    hdr.append("};")
    hdr.append("")
    hdr.append("#endif")

    with open(os.path.join(GEN, "assets.h"), "w", encoding="ascii") as f:
        f.write("\n".join(hdr) + "\n")
    with open(os.path.join(GEN, "assets.c"), "w", encoding="ascii") as f:
        f.write("\n".join(src) + "\n")
    print("wrote assets.h + assets.c,", len(spr), "sprites")
    return spr


if __name__ == "__main__":
    spr = export()
    cs = []
    for name in spr:
        c = pix.art(spr[name], L)
        pix.outline(c)
        cs.append(c)
    pix.save_preview(cs, os.path.join(ROOT, "tools", "prev_all.png"), scale=3, cols=9, bg=(70, 90, 60))
    print("ok")
