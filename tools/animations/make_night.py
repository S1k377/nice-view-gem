"""Right half: starry night. The moon cycles through its phases, stars twinkle,
a cloud drifts past, a shooting star streaks by, pines on a glowing horizon.
32 frames, seamless."""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, export

N = 32
TAU = 2 * math.pi
MX, MY, MR = 34, 42, 17

rng = random.Random(11)
STARS = []
while len(STARS) < 34:
    x, y = rng.randrange(3, W - 3), rng.randrange(3, 108)
    if (x - MX) ** 2 + (y - MY) ** 2 > (MR + 5) ** 2:
        STARS.append((x, y, rng.random(), rng.random() < 0.2))
STARS = [s for s in STARS if s[1] < 92]
CRATERS = [(-6, -5, 4), (5, 2, 5), (-3, 8, 3), (8, -8, 2.5), (-9, 4, 2)]


def moon(p):
    """Phase p in 0..1: 0 = new, 0.5 = full. Lit area bounded by the terminator ellipse."""
    dx, dy = xx - MX, yy - MY
    inside = dx * dx + dy * dy <= MR * MR
    half = np.sqrt(np.clip(MR * MR - dy * dy, 0, None))        # half-width of moon at each row
    k = math.cos(TAU * p)                                        # 1 -> new, -1 -> full
    term = k * half                                              # terminator x offset
    if p < 0.5:      # waxing: right side lit
        lit = dx >= term
    else:            # waning: left side lit
        lit = dx <= -term
    lit &= inside
    shade = np.zeros_like(lit)
    for cx, cy, r in CRATERS:
        shade |= disc(MX + cx, MY + cy, r) & (BAYER < 0.45)
    edge = inside & ~disc(MX, MY, MR - 1)
    dark_side = np.zeros_like(lit)
    return (lit & ~shade) | dark_side | (edge & (BAYER < 0.5)), inside


def pine(cx, base, h):
    m = np.zeros((H, W), bool)
    for i in range(h):
        y = base - i
        f = i / h
        w = (1 - f) * h * 0.30 * (0.55 + 0.45 * ((i % 7) / 6))    # layered branches
        m[y, max(0, int(cx - w)):min(W, int(cx + w) + 1)] = True
    m[base:base + 3, cx] = True
    return m


def frame(t):
    p = t / N
    img = np.zeros((H, W), bool)

    for x, y, ph, big in STARS:
        b = math.sin(TAU * (2 * p + ph))
        if b > -0.5:
            img[y, x] = True
        if big and b > 0.5:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                img[y + dy, x + dx] = True
            if b > 0.9:
                for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                    img[y + dy, x + dx] = True

    lit, disc_mask = moon((p + 0.5) % 1.0)        # loop starts at full moon
    img &= ~disc_mask
    img |= lit

    # cloud drifting left -> right across the moon (wraps once per loop)
    cx = -24 + p * (W + 48)
    cloud = disc(cx, 52, 5) | disc(cx + 7, 49, 7) | disc(cx + 14, 52, 5) | disc(cx - 6, 54, 3.5)
    cloud &= yy <= 56
    img &= ~cloud
    img |= cloud & ~erode(cloud)
    img |= cloud & (BAYER < 0.07)

    # shooting star during frames 8..13
    if 8 <= t <= 13:
        q = (t - 8) / 5
        hx, hy = 62 - q * 46, 72 + q * 22
        for i in range(10):
            x, y = int(hx + i * 1.6), int(hy - i * 0.75)
            if 0 < x < W - 1 and 0 < y < H and (i < 4 or (i + t) % 2 == 0):
                img[y, x] = True
        if q < 1:
            img[int(hy) - 1:int(hy) + 2, int(hx)] = True
            img[int(hy), max(1, int(hx) - 1):int(hx) + 2] = True

    # mountains: dark slopes, white ridge line, snow caps, a lake shimmer at the bottom
    ridge1 = 96 + np.abs(xx - 18) * 1.25 + 1.5 * np.sin(xx * 1.3)        # left peak
    ridge2 = 104 + np.abs(xx - 52) * 1.0 + 1.5 * np.sin(xx * 0.9 + 2)    # right peak
    ridge = np.minimum(ridge1, ridge2)
    mount = yy >= ridge
    img &= ~mount
    img |= mount & (yy < ridge + 1.5)                                     # ridge line
    snow = mount & (yy < np.minimum(96, 104) + 14) & (yy < ridge + 9 - np.abs(np.sin(xx * 0.7)) * 5)
    img |= snow & ((yy < 110) | (BAYER < 0.5))
    img |= mount & (yy >= ridge + 1.5) & ((xx * 7 + yy * 3) % 23 == 0)       # sparse rocks
    lake = yy >= 128
    img &= ~lake
    for i, y in enumerate(range(130, H - 1, 3)):
        w = 6 + 2 * i
        x0 = MX - w + int(round(2 * math.sin(TAU * p * 2 + i)))
        img[y, max(1, x0):min(W - 1, x0 + 2 * w)] = (((xx[y, max(1, x0):min(W - 1, x0 + 2 * w)] + i + t) % 3) == 0)
    img[128, :] = True

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


if __name__ == "__main__":
    import build_all
    build_all.main()
