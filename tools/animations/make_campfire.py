"""Campfire: centered fire on a stack of bark-textured logs with end grain, ringed by stones.
Soft smoke rises toward a crescent moon. 32 frames, seamless."""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, export

N = 32
FRAME_MS = 150
TAU = 2 * math.pi
FX, FIRE_BASE = 34, 116
rng = random.Random(7)
STARS = [(x, y, ph) for x, y, ph in ((rng.randrange(3, W - 3), rng.randrange(4, 62), rng.random())
                                     for _ in range(22))
         if (x - 53) ** 2 + (y - 16) ** 2 > 100]
TONGUES = [(34, 14, 48, 0.0, 2), (26, 9, 31, 1.7, 3), (42, 9, 32, 3.9, 3), (30, 7, 38, 5.1, 2),
           (38, 7, 37, 2.4, 2)]


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


def tongue(cx, hw, h, lean, phase, base=FIRE_BASE):
    m = np.zeros((H, W), bool)
    for i in range(int(h) + 1):
        f = i / h
        y = base - i
        width = hw * (1 - f ** 1.6) * (0.75 + 0.25 * math.cos(f * 2.2))
        shift = lean * f * f + 2.1 * math.sin(f * 5 + phase) * f
        if 0 <= y < H:
            m[y, max(0, int(round(cx + shift - width))):min(W, int(round(cx + shift + width)) + 1)] = True
    return m


def log(img, x0, y0, x1, y1, w):
    """A log seen at an angle: clean outline, one dashed bark groove, a knot, and the cut
    end at (x0, y0) facing the viewer with growth rings."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    u = (xx - x0) * ux + (yy - y0) * uy               # along the log
    v = -(xx - x0) * uy + (yy - y0) * ux              # across the log
    body = (u >= 0) & (u <= L) & (np.abs(v) <= w / 2)
    img &= ~dilate(body)
    img |= body & ~erode(body)
    img |= body & (np.abs(v) < 0.6) & ((u % 8) < 5) & (u > w * 0.6)        # bark groove
    img |= body & (np.abs(np.abs(v) - w * 0.3) < 0.5) & (((u + 4) % 11) < 3) & (u > w * 0.6)
    kxp, kyp = x0 + ux * L * 0.62 + uy * w * 0.2, y0 + uy * L * 0.62 - ux * w * 0.2
    img &= ~disc(kxp, kyp, 1.7)
    img |= disc(kxp, kyp, 1.7) & ~disc(kxp, kyp, 0.8)                     # knot
    r = w / 2 + 0.5                                                         # cut face
    face = ((xx - x0) / (r * 0.78)) ** 2 + ((yy - y0) / r) ** 2 <= 1
    img &= ~dilate(face)
    img |= face
    rings = ((xx - x0) / (r * 0.78)) ** 2 + ((yy - y0) / r) ** 2
    img &= ~((rings > 0.62) & (rings < 0.82))                               # dark growth ring
    img &= ~((rings > 0.18) & (rings < 0.32))
    return body


def frame(t):
    p = t / N
    img = np.zeros((H, W), bool)

    # moon + stars
    img |= disc(53, 16, 7) & ~disc(56, 14, 6)
    for sx, sy, ph in STARS:
        if math.sin(TAU * (p * 2 + ph)) > -0.4:
            img[sy, sx] = True

    # smoke ribbons
    for k in range(3):
        for i in range(27):
            q = i / 27
            y = 70 - i * 2.4
            x = FX + 6 * math.sin(TAU * (p * 2 - q * 1.2) + k * 2.1) * (0.4 + q)
            if (i + k + t) % 3 != 0 and q < 1 - k * 0.15:
                img |= disc(x + k * 2 - 2, y, 1.0 + q * 2.6) & (BAYER < 0.55 * (1 - q))

    # ground with a little ash under the fire
    img[131:, :] = False
    img[131, :] = True
    img |= (yy > 132) & (BAYER < 0.12)

    # flames
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

    # two front logs leaning in, cut ends toward the viewer
    log(img, 11, 125, 43, 107, 10)
    log(img, 57, 125, 25, 107, 10)

    # glowing embers between the logs
    for i, (ex, ey) in enumerate(((28, 124), (33, 126), (39, 124), (31, 128), (36, 128))):
        if math.sin(TAU * (p * 3 + i * 0.37)) > -0.3:
            img[ey, ex:ex + 2] = True

    # stone ring in front
    for sx, sy, rx, ry in ((5, 136, 3.4, 2.4), (13, 135, 4.2, 3.0), (22, 136.5, 3.0, 2.0),
                           (31, 135.5, 4.6, 2.6), (41, 136, 3.4, 2.4), (50, 135, 4.4, 3.0),
                           (60, 136, 4.0, 2.4)):
        stone = ((xx - sx) / rx) ** 2 + ((yy - sy) / ry) ** 2 <= 1
        img &= ~dilate(stone)
        img |= stone & ~erode(stone)
        img |= stone & (yy < sy - ry * 0.3) & (xx < sx) & (BAYER < 0.4)    # moonlit top

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
