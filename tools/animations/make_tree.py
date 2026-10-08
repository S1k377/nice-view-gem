"""A great old tree in the wind: a broad trunk with spreading roots, big limbs and a heavy
canopy of leaf clumps that sway in waves, leaves blowing off across the screen, grass
bending in the gusts. 40 frames, seamless."""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, thick_line, export

N = 40
FRAME_MS = 180
TAU = 2 * math.pi
GROUND = 127
NOISE = np.random.RandomState(9).rand(H, W)

rng = random.Random(5)

# limbs: (x0, y0, x1, y1, width at base, width at tip)
LIMBS = [
    (31, 96, 5, 70, 9, 4),             # great limbs spreading almost sideways
    (37, 95, 63, 69, 9, 4),
    (30, 94, 15, 57, 7, 3.5),
    (38, 93, 53, 56, 7, 3.5),
    (34, 92, 34, 50, 7, 3.5),
    (10, 75, -2, 66, 3.5, 2),
    (58, 74, 70, 65, 3.5, 2),
]

# a broad, flat-topped crown wider than the screen: leaf clumps (x, y, radius)
CLUMPS = [(34, 17, 10), (20, 21, 10), (48, 21, 10), (6, 29, 9.5), (62, 29, 9.5),
          (-2, 42, 9), (70, 42, 9), (14, 37, 10), (54, 37, 10), (27, 32, 10), (41, 32, 10),
          (3, 56, 9), (65, 56, 9), (19, 51, 10), (49, 51, 10), (34, 46, 10),
          (10, 66, 7.5), (58, 66, 7.5), (25, 63, 8), (43, 63, 8)]
CLUMPS = [(x, y, r, rng.uniform(0, TAU)) for x, y, r in CLUMPS]
CLUMPS.sort(key=lambda c: c[1])            # draw top ones first, lower ones in front

LEAVES = [(rng.uniform(0, 1), rng.uniform(20, 110), rng.uniform(0, TAU)) for _ in range(5)]
GRASS = [(x, rng.uniform(3, 6)) for x in range(3, W - 2, 3)]


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


def wind(t):
    """Gust strength 0..1: a strong gust then a calm, once per loop."""
    return 0.55 + 0.45 * math.sin(TAU * t / N)


def sway(x, y, t, ph=0.0):
    """Horizontal push for a point at height y: grows with height, travels as a wave."""
    k = max(0.0, (GROUND - y) / 110.0) ** 1.8
    return x + k * (3.6 * wind(t) - 1.2 + 1.6 * math.sin(TAU * t * 2 / N - y * 0.06 + ph))


def frame(t):
    img = np.zeros((H, W), bool)

    # trunk and limbs, tapering, swaying with height
    wood = np.zeros((H, W), bool)
    for x0, y0, x1, y1, w0, w1 in LIMBS:
        n = 8
        for i in range(n):
            a, b = i / n, (i + 1) / n
            ya, yb = y0 + (y1 - y0) * a, y0 + (y1 - y0) * b
            xa, xb = sway(x0 + (x1 - x0) * a, ya, t), sway(x0 + (x1 - x0) * b, yb, t)
            wood |= thick_line(xa, ya, xb, yb, w0 + (w1 - w0) * (a + b) / 2)
    # massive trunk that curves out into separate roots at the base
    TOP = 90
    trunk = np.zeros((H, W), bool)
    grooves = np.zeros((H, W), bool)
    for y in range(TOP, GROUND + 1):
        f = (y - TOP) / (GROUND - TOP)
        hw = 8.5 + 22 * f ** 3.2
        cx = sway(34, y, t)
        trunk[y, max(0, int(round(cx - hw))):min(W, int(round(cx + hw)) + 1)] = True
        # bark: long wavy grooves following the trunk, fanning out into the roots
        for rel in (-0.62, -0.25, 0.12, 0.5):
            gx = cx + rel * hw + 0.8 * math.sin(y * 0.35 + rel * 5)
            if (y + int(rel * 10)) % 9 < 7:
                grooves[y, int(round(gx))] = True
        # gaps between the roots near the ground
        if f > 0.55:
            for rel in (-0.55, 0.0, 0.55):
                gx = cx + rel * hw
                gw = (f - 0.55) * 7
                trunk[y, max(0, int(round(gx - gw / 2))):int(round(gx + gw / 2)) + 1] = False
    wood |= trunk

    # canopy: each clump gets a crisp outline and leafy texture that is denser where the
    # light hits (upper left); lower clumps overlap the ones behind them
    canopy = np.zeros((H, W), bool)
    canopy_area = np.zeros((H, W), bool)
    for cx, cy, r, ph in CLUMPS:
        sx = sway(cx, cy, t, ph * 0.3)
        c = disc(sx, cy, r)
        lx, ly = (xx - sx) / r, (yy - cy) / r
        light = np.clip(0.5 - 0.32 * (lx + ly), 0.04, 0.75)
        canopy &= ~c
        canopy |= c & (BAYER < light) & ~disc(sx, cy, r - 1.5)
        canopy |= c & (NOISE < light * 0.9)
        canopy &= ~(c & ~disc(sx, cy, r - 1.0) ^ c & ~disc(sx, cy, r - 1.0))
        canopy |= c & ~disc(sx, cy, r - 1.0)                       # outline
        canopy &= ~(c & disc(sx, cy, r - 1.0) & ~disc(sx, cy, r - 2.0))   # gap inside it
        canopy_area |= c

    bark = grooves & trunk & erode(trunk)
    img &= ~dilate(wood | canopy_area)
    img |= wood & ~bark
    img &= ~canopy_area
    img |= canopy

    # ground and grass bending with the wind
    img[GROUND:, :] = False
    img[GROUND, :] = True
    img |= (yy > GROUND + 2) & (BAYER < 0.08)
    img |= wood & (yy >= GROUND - 1) & (yy <= GROUND)
    for gx, gh in GRASS:
        if trunk[GROUND - 2, gx] or trunk[GROUND - 2, max(0, gx - 2)] or trunk[GROUND - 2, min(W - 1, gx + 2)]:
            continue
        lean = gh * 0.5 * wind(t) + 0.8 * math.sin(TAU * t * 2 / N + gx * 0.3)
        img |= thick_line(gx, GROUND, gx + lean, GROUND - gh, 1)

    # leaves blowing off and tumbling across the screen
    for off, y0, ph in LEAVES:
        q = (t / N + off) % 1.0
        x = -4 + q * (W + 8)
        y = y0 + 6 * math.sin(TAU * q * 2 + ph) + q * 10
        ang = TAU * q * 3 + ph
        u = (xx - x) * math.cos(ang) + (yy - y) * math.sin(ang)
        v = -(xx - x) * math.sin(ang) + (yy - y) * math.cos(ang)
        leaf = (u / 2.4) ** 2 + (v / 1.2) ** 2 <= 1
        img &= ~(dilate(leaf) & ~leaf)
        img |= leaf

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
