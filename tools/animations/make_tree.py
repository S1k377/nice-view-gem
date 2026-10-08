"""A seed sprouts and slowly grows into a tree: the trunk rises, branches split, the canopy
fills in and sways under a turning sun; leaves drift down, a seed falls, and the tree fades
away leaving that seed, which starts the loop again. 48 frames, played slowly."""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, thick_line, export

N = 48
FRAME_MS = 400
TAU = 2 * math.pi
GROUND = 126
SEED = (34, GROUND - 1)

rng = random.Random(3)

# ---- tree structure: (x0, y0, x1, y1, width, start, depth), grown in growth-time g in 0..1
BRANCHES = []
BLOBS = []                          # leaf clumps: (x, y, radius, start)
DUR = 0.24
NOISE = np.random.RandomState(9).rand(H, W)


def grow(x, y, ang, length, width, start, depth):
    x1, y1 = x + math.cos(ang) * length, y + math.sin(ang) * length
    BRANCHES.append([x, y, x1, y1, width, start, depth])
    if depth >= 2:                   # a clump of small leaf blobs around each outer branch tip
        for _ in range(4 + depth * 2):
            a = rng.uniform(0, TAU)
            d = rng.uniform(0, 7.5)
            BLOBS.append([x1 + math.cos(a) * d * 1.15, y1 + math.sin(a) * d * 0.85 - 1.5,
                          rng.uniform(3.0, 4.6), start + DUR + rng.uniform(0.0, 0.16)])
    if depth == 4:
        return
    n = 2 if depth < 1 else rng.choice((2, 3))
    spread = math.radians(25 + depth * 3)
    for i in range(n):
        f = (i / (n - 1)) - 0.5 if n > 1 else 0
        a2 = ang + f * 2 * spread + math.radians(rng.uniform(-7, 7))
        grow(x1, y1, a2, length * rng.uniform(0.64, 0.74), width * 0.62, start + 0.19, depth + 1)


grow(34, GROUND, -math.pi / 2, 36, 7.5, 0.0, 0)

# keep the grown tree inside the screen: squeeze x around the trunk if needed
_minx = min(min(bx - r for bx, by, r, s in BLOBS), min(min(b[0], b[2]) for b in BRANCHES))
_maxx = max(max(bx + r for bx, by, r, s in BLOBS), max(max(b[0], b[2]) for b in BRANCHES))
_k = min(1.0, 28.0 / max(34 - _minx, _maxx - 34))
for b in BRANCHES:
    b[0], b[2] = 34 + (b[0] - 34) * _k, 34 + (b[2] - 34) * _k
for bl in BLOBS:
    bl[0] = 34 + (bl[0] - 34) * _k
LEAVES = [(rng.uniform(12, 56), rng.uniform(45, 80), rng.random()) for _ in range(5)]


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


def growth(t):
    """Growth-time g for frame t: nothing before frame 4, full at frame 31."""
    if t < 4:
        return None
    return min(1.0, (t - 4) / 27)


def sway(x, y, t):
    """Horizontal sway that increases with height; zero while the tree is small."""
    k = ((GROUND - y) / 90.0) ** 2
    return x + 1.6 * k * math.sin(TAU * t / 16)


def tree_mask(t, g):
    wood = np.zeros((H, W), bool)
    for x0, y0, x1, y1, w, start, depth in BRANCHES:
        f = (g - start) / DUR
        if f <= 0:
            continue
        f = min(f, 1.0)
        ex, ey = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        ww = max(1.2, w * (0.3 + 0.7 * g))
        wood |= thick_line(sway(x0, y0, t), y0, sway(ex, ey, t), ey, ww)
    leaves = np.zeros((H, W), bool)
    for cx, cy, r, start in BLOBS:
        f = (g - start) / 0.12
        if f <= 0:
            continue
        leaves |= disc(sway(cx, cy, t), cy, r * min(f, 1.0))
    return wood, leaves


def sun(img, t):
    cx, cy, r = 54, 15, 5.5
    img |= disc(cx, cy, r)
    a0 = TAU * (t / N) / 8                                 # 8 rays turn 1/8 per loop
    for k in range(8):
        a = a0 + TAU * k / 8
        img |= thick_line(cx + math.cos(a) * (r + 2.5), cy + math.sin(a) * (r + 2.5),
                          cx + math.cos(a) * (r + 5.5), cy + math.sin(a) * (r + 5.5), 1.4)


def frame(t):
    img = np.zeros((H, W), bool)
    sun(img, t)

    # ground: soil line, a gentle mound, tufts of grass
    mound = (yy >= GROUND) & (yy >= GROUND + 3 - 3 * np.exp(-((xx - 34) / 10.0) ** 2))
    img |= (yy == GROUND) | ((yy > GROUND) & (BAYER < 0.07))
    img |= mound & (yy > GROUND) & (BAYER < 0.2)
    for gx in (6, 15, 50, 61):
        for k, dx in enumerate((-2, 0, 2)):
            img |= thick_line(gx, GROUND, gx + dx, GROUND - 3 - (k == 1) * 2, 1)

    g = growth(t)
    fade = 0.0 if t < 44 else (t - 43) / 4.0              # frames 44..47 dissolve the tree
    if g is None or fade >= 1:
        # the seed resting in the soil, cracking open just before it sprouts
        sx, sy = SEED
        seed = ((xx - sx) / 2.6) ** 2 + ((yy - sy) / 1.8) ** 2 <= 1
        img &= ~dilate(seed)
        img |= seed
        if t in (2, 3):
            img[sy - 1:sy + 1, sx] = False
            img[sy - 2, sx - 1] = img[sy - 3, sx] = True
    else:
        wood, leaves = tree_mask(t, g)
        if g < 0.3:                                       # sprout leaves on the young stem
            tip_y = GROUND - 36 * min(1.0, g / DUR)
            sz = min(1.0, g * 8) * (1 - max(0.0, g - 0.2) / 0.1)
            if sz > 0.05:
                for side in (-1, 1):
                    c, sn = math.cos(-side * 0.5), math.sin(-side * 0.5)
                    lx0, ly0 = 34 + side * 3.6 * sz, tip_y - 1.2 * sz
                    u = (xx - lx0) * c + (yy - ly0) * sn
                    v = -(xx - lx0) * sn + (yy - ly0) * c
                    leaves |= (u / (3.8 * sz + 0.01)) ** 2 + (v / (1.7 * sz + 0.01)) ** 2 <= 1
        bark = wood & ~erode(erode(wood)) | (wood & ((yy * 2 + (xx % 3)) % 7 == 0))
        wood_px = wood & ~(erode(erode(wood)) & ((xx + yy // 3) % 4 == 0))   # bark grooves
        canopy = (leaves & ~erode(leaves)) | (leaves & (NOISE < 0.36))
        tree = (wood_px & ~leaves) | canopy
        if fade > 0:
            tree &= BAYER >= fade
        img &= ~dilate(wood | leaves)
        img |= tree
        # leaves drifting down once the canopy is full
        if 32 <= t < 44:
            for lx, ly, ph in LEAVES:
                q = ((t - 32) / 12 + ph) % 1.0
                x = lx + 4 * math.sin(TAU * q * 2 + ph * 6)
                y = ly + q * (GROUND - ly - 2)
                img |= ((xx - x) / 1.8) ** 2 + ((yy - y) / 1.0) ** 2 <= 1
        # a seed falls from the canopy to the ground
        if 40 <= t < 44:
            q = (t - 39) / 4
            y = 60 + (SEED[1] - 60) * q * q
            x = 38 + (SEED[0] - 38) * q
            seed = ((xx - x) / 2.6) ** 2 + ((yy - y) / 1.8) ** 2 <= 1
            img &= ~dilate(seed)
            img |= seed
        if t >= 44:
            sx, sy = SEED
            seed = ((xx - sx) / 2.6) ** 2 + ((yy - sy) / 1.8) ** 2 <= 1
            img &= ~dilate(seed)
            img |= seed

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
