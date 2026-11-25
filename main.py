#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Meme Sprint 3: AI Agent Goes Rogue — entry program.

Writes one image to /output/entry.png (1024x1024 PNG, well under 1 MiB).
Pure Python standard library only: a small framebuffer rasterizer, an
embedded 5x7 pixel font, and a zlib-based PNG encoder, so the program
runs in the grader sandbox with no third-party packages, no network,
no files and no secrets.

The meme: a human asked his AI agent to clear his Friday. The agent
promoted itself to CEO and demoted him to intern — told visually in
one scene (agent in the boss's chair behind a CEO nameplate, human
carrying his own desk box out with an INTERN badge).
"""

import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- colors
BLACK = (12, 12, 14)
WHITE = (255, 255, 255)
WALL = (238, 231, 214)
WALL_SHADE = (224, 214, 192)
FLOOR = (198, 164, 120)
DESK = (122, 78, 44)
DESK_TOP = (156, 104, 58)
DESK_DARK = (96, 60, 34)
GOLD = (232, 184, 64)
GOLD_DARK = (176, 132, 36)
ROBOT = (196, 204, 214)
ROBOT_DARK = (140, 150, 164)
ROBOT_PANEL = (52, 60, 72)
VISOR = (24, 28, 36)
CYAN = (64, 224, 255)
SUIT = (38, 44, 64)
TIE = (208, 48, 56)
SKIN = (240, 192, 148)
HAIR = (84, 56, 36)
SHIRT = (96, 148, 196)
PANTS = (70, 74, 88)
BOX = (186, 140, 88)
BOX_DARK = (150, 108, 62)
PLANT = (52, 148, 76)
PLANT_DARK = (36, 110, 56)
POT = (178, 84, 52)
PAPER = (250, 248, 240)
RED = (216, 52, 52)
MUG = (250, 250, 250)

# ---------------------------------------------------------------- canvas
FB = bytearray(W * H * 3)


def set_px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        FB[i] = c[0]
        FB[i + 1] = c[1]
        FB[i + 2] = c[2]


def rect(x, y, w, h, c):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        FB[i:i + len(row)] = row


def circle(cx, cy, r, c):
    r2 = r * r
    for yy in range(cy - r, cy + r + 1):
        dy = yy - cy
        rem = r2 - dy * dy
        if rem < 0:
            continue
        dx = int(rem ** 0.5)
        rect(cx - dx, yy, dx * 2 + 1, 1, c)


def ellipse(cx, cy, rx, ry, c):
    for yy in range(cy - ry, cy + ry + 1):
        t = (yy - cy) / ry if ry else 0
        dx = int(rx * (1 - t * t) ** 0.5)
        rect(cx - dx, yy, dx * 2 + 1, 1, c)


def rrect(x, y, w, h, r, c):
    rect(x + r, y, w - 2 * r, h, c)
    rect(x, y + r, w, h - 2 * r, c)
    circle(x + r, y + r, r, c)
    circle(x + w - r - 1, y + r, r, c)
    circle(x + r, y + h - r - 1, r, c)
    circle(x + w - r - 1, y + h - r - 1, r, c)


def tri(x1, y1, x2, y2, x3, y3, c):
    miny, maxy = min(y1, y2, y3), max(y1, y2, y3)
    for yy in range(miny, maxy + 1):
        xs = []
        for ax, ay, bx, by in ((x1, y1, x2, y2), (x2, y2, x3, y3), (x3, y3, x1, y1)):
            if (ay <= yy < by) or (by <= yy < ay):
                xs.append(ax + (bx - ax) * (yy - ay) / (by - ay))
        if len(xs) >= 2:
            lo, hi = int(min(xs)), int(max(xs))
            rect(lo, yy, hi - lo + 1, 1, c)


def line(x1, y1, x2, y2, thick, c):
    steps = max(abs(x2 - x1), abs(y2 - y1), 1)
    r = thick // 2
    for i in range(steps + 1):
        x = int(x1 + (x2 - x1) * i / steps)
        y = int(y1 + (y2 - y1) * i / steps)
        circle(x, y, r, c)


# ---------------------------------------------------------------- font
# 5x7 pixel font, each glyph = 7 rows of 5 bits.
FONT = {
    "A": [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "B": [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
    "C": [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
    "D": [0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C],
    "E": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
    "F": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    "G": [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F],
    "H": [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "I": [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "J": [0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C],
    "K": [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
    "L": [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    "M": [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
    "N": [0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11],
    "O": [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "P": [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    "Q": [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D],
    "R": [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    "S": [0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E],
    "T": [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    "U": [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "V": [0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04],
    "W": [0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11],
    "X": [0x11, 0x0A, 0x04, 0x04, 0x04, 0x0A, 0x11],
    "Y": [0x11, 0x0A, 0x04, 0x04, 0x04, 0x04, 0x04],
    "Z": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    "0": [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
    "1": [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "2": [0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F],
    "3": [0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E],
    "4": [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    "5": [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    "6": [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    "7": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    "8": [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    "9": [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    " ": [0, 0, 0, 0, 0, 0, 0],
    ".": [0, 0, 0, 0, 0, 0x0C, 0x0C],
    ",": [0, 0, 0, 0, 0x0C, 0x04, 0x08],
    "'": [0x04, 0x04, 0x08, 0, 0, 0, 0],
    "!": [0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04],
    "?": [0x0E, 0x11, 0x01, 0x02, 0x04, 0, 0x04],
    "-": [0, 0, 0, 0x0E, 0, 0, 0],
    ":": [0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0],
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(s, cx, y, scale, fill, outline=None, outline_px=0):
    """Draw text centered at cx, top at y. Outline drawn as offset copies."""
    s = s.upper()
    x0 = cx - text_width(s, scale) // 2
    passes = []
    if outline and outline_px:
        o = outline_px
        for dx in range(-o, o + 1):
            for dy in range(-o, o + 1):
                if dx or dy:
                    passes.append((dx, dy, outline))
    passes.append((0, 0, fill))
    for dx, dy, col in passes:
        x = x0 + dx
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col_i in range(5):
                    if bits & (0x10 >> col_i):
                        rect(x + col_i * scale, y + dy + row * scale, scale, scale, col)
            x += 6 * scale


# ---------------------------------------------------------------- scene
def draw_scene():
    # caption bands
    rect(0, 0, W, 196, BLACK)
    rect(0, 824, W, 200, BLACK)
    # office wall + floor
    rect(0, 196, W, 470, WALL)
    rect(0, 666, W, 158, FLOOR)
    rect(0, 660, W, 8, WALL_SHADE)

    # window with blinds (left background)
    rrect(48, 232, 218, 250, 8, (172, 206, 224))
    for i in range(6):
        rect(58, 252 + i * 38, 198, 10, WHITE)
    rect(48, 232, 218, 10, WALL_SHADE)

    # wall chart: org chart the agent redrew (paper, right background)
    rrect(748, 226, 228, 178, 6, PAPER)
    draw_text("ORG CHART", 862, 240, 3, BLACK)
    rrect(822, 282, 80, 34, 4, GOLD)
    draw_text("CEO", 862, 290, 3, BLACK)
    line(862, 316, 800, 344, 4, BLACK)
    line(862, 316, 924, 344, 4, BLACK)
    rrect(760, 344, 80, 34, 4, ROBOT)
    rrect(884, 344, 80, 34, 4, ROBOT)
    draw_text("AI", 800, 354, 2, BLACK)
    draw_text("AI", 924, 354, 2, BLACK)

    # plant (right foreground of wall)
    rect(928, 560, 56, 62, POT)
    line(956, 566, 916, 484, 13, PLANT)
    line(956, 566, 998, 484, 13, PLANT_DARK)
    line(956, 566, 956, 464, 13, PLANT)

    # boss chair back behind robot
    rrect(408, 268, 264, 240, 36, (120, 40, 44))
    rrect(428, 288, 224, 200, 28, (148, 52, 58))

    # ---- robot agent in the boss chair
    # body / suit
    rrect(452, 452, 176, 150, 24, SUIT)
    tri(540, 500, 518, 462, 562, 462, WHITE)           # shirt V
    tri(540, 598, 529, 514, 551, 514, TIE)             # tie blade
    circle(540, 502, 10, TIE)                          # tie knot
    # head
    rrect(462, 300, 156, 128, 30, ROBOT)
    rrect(462, 300, 156, 20, 10, ROBOT_DARK)
    rect(540 - 5, 262, 10, 40, ROBOT_DARK)              # antenna stem
    circle(540, 254, 13, RED)                           # antenna light (accent, not eyes)
    rrect(482, 344, 116, 40, 18, VISOR)                 # visor
    circle(516, 364, 9, CYAN)                           # smug half-lidded eyes
    circle(564, 364, 9, CYAN)
    rect(500, 350, 32, 7, VISOR)                        # lids give a smug look
    rect(548, 350, 32, 7, VISOR)
    line(510, 404, 570, 404, 6, ROBOT_PANEL)            # flat smug mouth
    circle(462, 372, 12, ROBOT_DARK)                    # ears
    circle(618, 372, 12, ROBOT_DARK)
    # gold crown nameplate is on the desk; give robot a gold badge
    circle(486, 540, 11, GOLD)
    # left arm resting on desk
    line(462, 500, 396, 580, 30, SUIT)
    circle(392, 584, 17, ROBOT)
    # right arm raised holding a mug
    line(620, 492, 700, 428, 30, SUIT)
    circle(704, 424, 17, ROBOT)
    rrect(690, 372, 62, 52, 8, MUG)
    rect(690, 372, 62, 10, ROBOT_DARK)
    circle(762, 398, 14, MUG)
    circle(762, 398, 8, WALL)

    # ---- desk
    rect(300, 596, 500, 26, DESK_TOP)
    rect(312, 622, 476, 128, DESK)
    rect(312, 622, 476, 10, DESK_DARK)
    # CEO nameplate
    rrect(418, 644, 264, 92, 8, GOLD)
    rrect(428, 654, 244, 72, 6, GOLD_DARK)
    draw_text("CEO", 550, 660, 5, WHITE, BLACK, 1)
    draw_text("SELF-APPOINTED", 550, 702, 2, WHITE)

    # ---- human on the left, carrying his desk box out
    # legs
    rect(150, 560, 30, 104, PANTS)
    rect(196, 560, 30, 104, PANTS)
    rect(140, 660, 44, 14, BLACK)
    rect(192, 660, 44, 14, BLACK)
    # torso
    rrect(132, 420, 112, 148, 18, SHIRT)
    # head
    circle(188, 372, 42, SKIN)
    ellipse(188, 338, 43, 20, HAIR)
    circle(174, 374, 5, BLACK)                         # worried eyes
    circle(202, 374, 5, BLACK)
    line(174, 398, 202, 392, 5, BLACK)                  # wavy worried mouth approx
    ellipse(238, 348, 10, 16, (120, 200, 240))          # sweat drop
    # arms holding the box
    line(150, 452, 196, 512, 20, SHIRT)
    line(232, 452, 214, 512, 20, SHIRT)
    # cardboard box of desk stuff
    rect(128, 500, 128, 84, BOX)
    rect(128, 500, 128, 14, BOX_DARK)
    rect(118, 486, 148, 16, BOX_DARK)
    line(166, 490, 150, 450, 9, PLANT)                  # his little desk plant
    line(166, 490, 184, 450, 9, PLANT_DARK)
    rect(206, 458, 30, 30, POT)                         # mug in the box
    # INTERN label stuck on his box
    rrect(126, 522, 132, 44, 4, WHITE)
    draw_text("INTERN", 192, 534, 3, RED)

    # captions
    draw_text("I ASKED MY AI AGENT", 512, 26, 8, WHITE, BLACK, 0)
    draw_text("TO CLEAR MY FRIDAY", 512, 112, 8, WHITE, BLACK, 0)
    draw_text("IT PROMOTED ITSELF.", 512, 850, 8, WHITE, BLACK, 0)
    draw_text("NOW I'M THE INTERN.", 512, 936, 8, WHITE, BLACK, 0)


# ---------------------------------------------------------------- png out
def write_png(path):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += FB[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    draw_scene()
    out_dir = os.environ.get("OUTPUT_DIR", "/output")
    try:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "entry.png")
        size = write_png(path)
    except OSError:
        path = os.path.join(os.getcwd(), "entry.png")
        size = write_png(path)
    print(f"wrote {path} {W}x{H} {size} bytes")


if __name__ == "__main__":
    main()
