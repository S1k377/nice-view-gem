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
    (34, GROUND, 34, 84, 11, 7.5),     # trunk
    (34, 90, 14, 62, 7, 3.5),          # big left limb
    (34, 88, 55, 60, 7, 3.5),          # big right limb
    (34, 86, 31, 50, 6, 3),            # centre leader
    (20, 70, 8, 58, 3.2, 1.6),
    (49, 68, 61, 57, 3.2, 1.6),
    (32, 62, 22, 40, 3.2, 1.6),
    (33, 60, 46, 38, 3.2, 1.6),
]

# leaf clumps (x, y, radius), placed by hand for a broad oak-like crown
CLUMPS = [(34, 18, 11), (20, 25, 10), (48, 25, 10), (9, 40, 8.5), (59, 40, 8.5),
          (27, 36, 10), (42, 35, 10), (16, 51, 9.5), (52, 50, 9.5), (34, 50, 9),
          (7, 60, 6.5), (61, 60, 6.5), (24, 63, 7.5), (44, 63, 7.5)]
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
    k = max(0.0, (GROUND - y) / 100.0) ** 1.6
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
    # roots flaring into the ground
    for rx, s in ((22, -1), (46, 1), (28, -1), (40, 1)):
        wood |= thick_line(34 + s * 4, GROUND - 7, rx, GROUND + 1, 3.5)

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

    # bark: grooves down the trunk and limbs
    bark = wood & ((((xx * 2 + yy // 4) % 6) == 0) & erode(erode(wood)))
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
        if 27 < gx < 41:
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
