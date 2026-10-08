"""Campfire: a classic log pile (a back log, two crossed logs and a front log, with cut ends
showing their rings) under a big flickering flame, soft smoke drifting up to a crescent moon,
stones on the ground. 32 frames, seamless."""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, export

N = 32
FRAME_MS = 150
TAU = 2 * math.pi
FX, FIRE_BASE = 34, 114
rng = random.Random(7)
STARS = [(x, y, ph) for x, y, ph in ((rng.randrange(3, W - 3), rng.randrange(4, 62), rng.random())
                                     for _ in range(20))
         if (x - 53) ** 2 + (y - 16) ** 2 > 110]
# flame tongues: (x, half-width, height, phase, speed)
TONGUES = [(34, 13, 50, 0.0, 2), (26, 9, 33, 1.7, 3), (42, 9, 35, 3.9, 3),
           (30, 6, 40, 5.1, 2), (38, 6, 39, 2.4, 2)]


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


def tongue(cx, hw, h, lean, phase):
    m = np.zeros((H, W), bool)
    for i in range(int(h) + 1):
        f = i / h
        y = FIRE_BASE - i
        width = hw * (1 - f ** 1.6) * (0.75 + 0.25 * math.cos(f * 2.2))
        shift = lean * f * f + 2.0 * math.sin(f * 5 + phase) * f
        if 0 <= y < H:
            m[y, max(0, int(round(cx + shift - width))):min(W, int(round(cx + shift + width)) + 1)] = True
    return m


def log(img, x0, y0, x1, y1, w, rings=(True, True)):
    """A log: white outline, a dark body with two lines of bark grain along its length,
    and round cut ends showing a ring and a heart dot (like the very first version)."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    u = (xx - x0) * ux + (yy - y0) * uy
    v = -(xx - x0) * uy + (yy - y0) * ux
    body = (u >= 0) & (u <= L) & (np.abs(v) <= w / 2)
    img &= ~dilate(body)
    img |= body & ~erode(body)
    img |= body & (np.abs(v) < 0.5) & ((u % 7) < 4) & (u > w * 0.7) & (u < L - w * 0.7)   # bark grain
    r = w / 2 + 0.5
    for end, show in zip(((x0, y0), (x1, y1)), rings):
        if not show:
            continue
        ex, ey = end
        cap = disc(ex, ey, r)
        img &= ~dilate(cap)
        img |= cap & ~disc(ex, ey, r - 1.1)
        img |= disc(ex, ey, r * 0.45) & ~disc(ex, ey, r * 0.45 - 0.9)
        img |= disc(ex, ey, 0.7)


def frame(t):
    p = t / N
    img = np.zeros((H, W), bool)

    # crescent moon + quiet stars
    img |= disc(53, 16, 7) & ~disc(56, 14, 6)
    for sx, sy, ph in STARS:
        if math.sin(TAU * (p * 2 + ph)) > -0.4:
            img[sy, sx] = True

    # smoke ribbons
    for k in range(3):
        for i in range(26):
            q = i / 26
            y = 66 - i * 2.4
            x = FX + 6 * math.sin(TAU * (p * 2 - q * 1.2) + k * 2.1) * (0.4 + q)
            if (i + k + t) % 3 != 0 and q < 1 - k * 0.15:
                img |= disc(x + k * 2 - 2, y, 1.0 + q * 2.6) & (BAYER < 0.55 * (1 - q))

    # ground
    img[134:, :] = False
    img[134, :] = True
    img |= (yy > 135) & (BAYER < 0.15)


    # flames: white body, hollow dark core, small white heart
    flame = np.zeros((H, W), bool)
    core = np.zeros((H, W), bool)
    for cx, hw, h, ph, sp in TONGUES:
        a = TAU * p * sp + ph
        hh = h * (0.82 + 0.18 * math.sin(a))
        lean = 3.5 * math.sin(a * 0.5 + ph)
        flame |= tongue(cx, hw, hh, lean, a)
        core |= tongue(cx, max(1, hw - 4), hh * 0.5, lean * 0.6, a)
    img &= ~dilate(flame)
    img |= flame
    img &= ~core
    img |= tongue(FX, 4, 12 + 3 * math.sin(TAU * p * 3), 1.8 * math.sin(TAU * p * 2), TAU * p * 2) & core

    # two crossed logs in front, then a short log lying across the bottom
    log(img, 9, 125, 47, 104, 9, rings=(True, False))
    log(img, 59, 125, 21, 104, 9, rings=(True, False))
    log(img, 17, 131, 51, 131, 7)

    # embers glowing between the logs
    for i, (ex, ey) in enumerate(((28, 121), (34, 123), (40, 121), (31, 126), (37, 126))):
        if math.sin(TAU * (p * 3 + i * 0.37)) > -0.3:
            img[ey, ex:ex + 2] = True

    # a few stones
    for sx, sy, rx, ry in ((5, 133, 3.6, 2.6), (63, 133, 3.8, 2.8)):
        stone = ((xx - sx) / rx) ** 2 + ((yy - sy) / ry) ** 2 <= 1
        img &= ~dilate(stone)
        img |= stone & ~erode(stone)

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
