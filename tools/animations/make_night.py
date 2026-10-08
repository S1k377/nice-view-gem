"""Right half: starry night. A big moon (almost screen-wide) cycles through its phases,
stars twinkle, a cloud drifts across, a shooting star streaks by, snowy mountains and a
lake shimmer below. 32 frames, seamless."""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, export

N = 32
TAU = 2 * math.pi
MX, MY, MR = 34, 47, 30          # moon spans x 4..64

rng = random.Random(11)
STARS = []
while len(STARS) < 26:
    x, y = rng.randrange(3, W - 3), rng.randrange(3, 99)
    if (x - MX) ** 2 + (y - MY) ** 2 > (MR + 4) ** 2:
        STARS.append((x, y, rng.random(), rng.random() < 0.3))
# dithered "seas" (large soft patches) and ringed craters, offsets from the moon centre
SEAS = [(-11, -9, 9), (8, 4, 10), (-6, 14, 6), (15, -12, 5)]
RINGS = [(-17, 6, 3.5), (3, -18, 3), (19, 9, 2.5), (-2, 22, 2.5), (11, 20, 2)]


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


def moon(p):
    """Phase p in 0..1: 0 = new, 0.5 = full. Lit area bounded by the terminator ellipse."""
    dx, dy = xx - MX, yy - MY
    inside = dx * dx + dy * dy <= MR * MR
    half = np.sqrt(np.clip(MR * MR - dy * dy, 0, None))
    k = math.cos(TAU * p)                       # 1 -> new, -1 -> full
    term = k * half
    lit = (dx >= term) if p < 0.5 else (dx <= -term)
    lit &= inside
    shade = np.zeros_like(lit)
    for cx, cy, r in SEAS:
        shade |= disc(MX + cx, MY + cy, r) & (BAYER < 0.4)
    for cx, cy, r in RINGS:
        shade |= disc(MX + cx, MY + cy, r) & ~disc(MX + cx - 0.6, MY + cy - 0.6, r - 1.2)
    rim = inside & ~disc(MX, MY, MR - 1)
    return (lit & ~shade) | (rim & (BAYER < 0.5)), inside


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

    lit, disc_mask = moon((p + 0.5) % 1.0)      # loop starts at full moon
    img &= ~disc_mask
    img |= lit

    # cloud drifting left -> right across the lower half of the moon (wraps once per loop)
    cx = -36 + p * (W + 72)
    cloud = (disc(cx, 69, 8) | disc(cx + 11, 64, 11) | disc(cx + 23, 69, 8) | disc(cx - 11, 71, 5.5)
             | disc(cx + 32, 72, 4.5))
    cloud &= yy <= 76
    img &= ~dilate(cloud)
    img |= cloud & ~erode(cloud)
    img |= cloud & (BAYER < 0.07)

    # shooting star in the gap between moon and mountains, frames 8..13
    if 8 <= t <= 13:
        q = (t - 8) / 5
        hx, hy = 62 - q * 48, 84 + q * 12
        for i in range(12):
            x, y = int(hx + i * 1.6), int(hy - i * 0.6)
            if 0 < x < W - 1 and 0 < y < H and (i < 5 or (i + t) % 2 == 0):
                img[y, x] = True
        if q < 1:
            img[int(hy) - 1:int(hy) + 2, int(hx)] = True
            img[int(hy), max(1, int(hx) - 1):int(hx) + 2] = True

    # mountains: dark slopes, white ridge line, snow caps
    ridge1 = 103 + np.abs(xx - 17) * 1.2 + 1.5 * np.sin(xx * 1.3)
    ridge2 = 110 + np.abs(xx - 52) * 1.0 + 1.5 * np.sin(xx * 0.9 + 2)
    ridge = np.minimum(ridge1, ridge2)
    mount = yy >= ridge
    img &= ~mount
    img |= mount & (yy < ridge + 1.5)
    snow = mount & (yy < 117) & (yy < ridge + 8 - np.abs(np.sin(xx * 0.7)) * 5)
    img |= snow & ((yy < 113) | (BAYER < 0.5))
    img |= mount & (yy >= ridge + 1.5) & ((xx * 7 + yy * 3) % 23 == 0)

    # lake with the moon's shimmering reflection
    img &= ~(yy >= 128)
    for i, y in enumerate(range(130, H - 1, 3)):
        w = 8 + 2 * i
        x0 = MX - w + int(round(2 * math.sin(TAU * p * 2 + i)))
        seg = slice(max(1, x0), min(W - 1, x0 + 2 * w))
        img[y, seg] = ((xx[y, seg] + i + t) % 3) == 0
    img[128, :] = True

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
