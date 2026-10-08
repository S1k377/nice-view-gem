"""Gaming layer: an arcade cabinet. Marquee with chasing bulbs and a blinking PLAY sign, a
screen showing a big "GG!" in 3D block letters that bob while their extrusion sways, stars
twinkling around it, a joystick wiggling and buttons being hit, coin slots glowing in turn.
32 frames, seamless."""
import math
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, rect, thick_line
from pixfont import text_mask, text_width

N = 32
# 4x5 block glyphs for the big screen title (drawn at 4x)
BIG = {
    "G": [".XXX", "X...", "X.XX", "X..X", ".XXX"],
    "!": ["X", "X", "X", ".", "X"],
}
S = 4
FRAME_MS = 120
TAU = 2 * math.pi


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


def outline(img, m):
    img &= ~m
    img |= m & ~erode(m)


def frame(t):
    p = t / N
    img = np.zeros((H, W), bool)

    # cabinet body: marquee box on top, screen section slanting back, control panel jutting out,
    # straight lower body; drawn as one outlined silhouette with side panels
    body = np.zeros((H, W), bool)
    body |= rect(5, 3, 62, 24)                                   # marquee
    for y in range(24, 86):                                      # screen section, slight taper
        body[y, 7:61] = True
    for y in range(86, 100):                                     # control panel sticks out
        f = (y - 86) / 14
        body[y, int(3 - f * 1):int(65 + f * 1)] = True
    body |= rect(7, 100, 60, 137)                                # lower body
    outline(img, body)
    img |= rect(5, 24, 62, 25)                                   # marquee bottom trim
    img |= rect(3, 99, 64, 100)                                  # panel front edge
    # side art stripes on the lower body
    for k in range(3):
        img |= thick_line(9, 104 + k * 5, 15, 98 + k * 5, 1.2) & (yy > 101)
        img |= thick_line(58, 104 + k * 5, 52, 98 + k * 5, 1.2) & (yy > 101)

    # marquee: blinking 1UP-style title and chasing bulbs round its edge
    title = "PLAY"
    tw = text_width(title, 2)
    if t % 8 < 6:
        img |= text_mask(title, 34 - tw // 2, 9, (H, W), 2)
    bulbs = [(x, 5) for x in range(9, 60, 5)] + [(x, 22) for x in range(9, 60, 5)]
    for i, (bx, by) in enumerate(bulbs):
        if (i + t) % 3 == 0:
            img |= disc(bx, by, 1.2)
        else:
            img[by, bx] = True

    # screen: rounded CRT with a paddle-and-ball game and scanlines
    scr = rect(11, 29, 56, 81) & ~(rect(11, 29, 12, 30) | rect(55, 29, 56, 30) |
                                   rect(11, 80, 12, 81) | rect(55, 80, 56, 81))
    img &= ~scr
    img |= dilate(scr) & ~scr
    # "GG!" in chunky 3D letters: solid faces with an extruded block underneath, split from
    # the face by a dark line; the title bobs gently and the extrusion leans side to side
    q = TAU * p
    widths = [len(BIG[g][0]) * S for g in "GG!"]
    total = sum(widths) + 2 * 2
    ox = 34 - total // 2
    oy = 42 + int(round(2 * math.sin(q * 2)))
    lean = 0.8 * math.sin(q)                             # extrusion sways gently left/right
    face = np.zeros((H, W), bool)
    cx = ox
    for g, w in zip("GG!", widths):
        for j, row in enumerate(BIG[g]):
            for i, c in enumerate(row):
                if c == "X":
                    face |= rect(cx + i * S, oy + j * S, cx + i * S + S - 1, oy + j * S + S - 1)
        cx += w + 2
    sides = np.zeros((H, W), bool)
    for d in range(1, 4):
        sides |= np.roll(np.roll(face, d, 0), int(round(lean * d)), 1)   # extrude downward
    sides &= ~face & scr
    img &= ~dilate(face | sides)
    img |= sides & ((xx + yy) % 2 == 0)                  # gray (checkerboard) side walls
    img |= sides & ~np.roll(sides, -1, 0) & ~face        # crisp bottom edge
    img &= ~(dilate(face) & ~face & ~sides)              # dark outline where the face meets black
    img |= face

    for k, (stx, sty) in enumerate(((16, 34), (50, 38), (19, 74), (48, 72), (33, 33), (36, 76))):
        ph = (t + k * 5) % 8
        if ph < 2:
            img |= rect(stx - 2, sty, stx + 2, sty) | rect(stx, sty - 2, stx, sty + 2)
        elif ph < 4:
            img[sty, stx] = True

    # control panel: joystick wiggling, three buttons being hit
    jx = 18 + 3.5 * math.sin(TAU * p * 4)
    img &= ~rect(8, 87, 60, 98)
    base = ((xx - 18) / 5.0) ** 2 + ((yy - 96) / 2.0) ** 2 <= 1
    outline(img, base)
    img |= thick_line(18, 95, jx, 89, 1.6)
    img |= disc(jx, 88.5, 3.2)
    img &= ~disc(jx - 1, 87.5, 0.9)                                     # shine
    for k, (bx2, by2) in enumerate(((36, 94), (44, 92), (52, 94))):
        pressed = ((t + k * 3) % 6) < 2
        cap = disc(bx2, by2 + (1 if pressed else 0), 2.9)
        ring = ((xx - bx2) / 3.9) ** 2 + ((yy - by2 - 1.5) / 2.6) ** 2 <= 1
        outline(img, ring)
        img |= cap
        if not pressed:
            img &= ~disc(bx2 - 1, by2 - 1, 0.8)                         # shine on raised caps

    # coin door: two slots that glow in turn, a speaker grille below
    for k, cx in enumerate((24, 43)):
        door = rect(cx - 5, 106, cx + 5, 118)
        outline(img, door)
        slot = rect(cx - 1, 108, cx, 114)
        if (t // 4 + k) % 2 == 0:
            img |= dilate(slot)
            img &= ~slot
        else:
            img |= slot
    for y in range(122, 135, 3):
        img |= rect(16, y, 51, y) & (xx % 2 == 0)
    img |= rect(5, 137, 62, 138)                                        # base

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
