"""Waterfall: a river spills over the lip between two dark cliffs and rushes down in
streaks into a pool, churning up foam and spreading ripples under a crescent moon.
32 frames, seamless."""
import math, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc

N = 32
FRAME_MS = 110
TAU = 2 * math.pi
LIP = 34                     # where the water goes over
POOL = 116                   # pool surface
FX0, FX1 = 19, 49            # waterfall edges

rng = random.Random(4)
NOISE = np.random.RandomState(3).rand(H, W)
# falling streaks: (x, phase offset, length); each moves 8 px per frame, period 64 px
STREAKS = [(x, rng.randrange(0, 64), rng.randint(6, 14)) for x in range(FX0 + 1, FX1, 2)]


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


def frame(t):
    p = t / N
    img = np.zeros((H, W), bool)

    # night sky with a few stars and a moon behind the falls
    for sx, sy in ((6, 6), (14, 14), (55, 5), (62, 18), (44, 10), (25, 4)):
        img[sy, sx] = True
    img |= disc(34, 14, 6) & ~disc(37, 12, 5)

    # cliffs: dark rock with a lit edge and a few cracks
    left_edge = FX0 - 1 + 1.6 * np.sin(yy * 0.21) + 1.0 * np.sin(yy * 0.53 + 1)
    right_edge = FX1 + 1 + 1.6 * np.sin(yy * 0.19 + 2) + 1.0 * np.sin(yy * 0.47)
    top = LIP - 4 + 2 * np.sin(xx * 0.4) * ((xx < FX0 - 2) | (xx > FX1 + 2))
    cliff = ((xx <= left_edge) | (xx >= right_edge)) & (yy >= top) & (yy < POOL)
    img &= ~cliff
    img |= cliff & ((np.abs(xx - left_edge) < 1) | (np.abs(xx - right_edge) < 1) | (np.abs(yy - top) < 1))
    for x0, y0, dx in ((8, 50, 3), (4, 72, 4), (12, 92, -3), (58, 56, -3), (62, 80, -4), (55, 100, 3)):
        for i in range(7):
            yy_, xx_ = y0 + i, int(x0 + dx * math.sin(i * 0.7))
            if cliff[yy_, xx_]:
                img[yy_, xx_] = True
    for gx in range(3, W - 2, 4):                                          # grass on top
        if gx < FX0 - 3 or gx > FX1 + 3:
            ty = int(top[0, gx])
            img[ty - 2:ty, gx] = True

    # falling water: bright, with dark streaks racing down and ragged edges
    lip = LIP + 2 * ((xx - 34) / 15.0) ** 2
    fall = (xx > FX0) & (xx < FX1) & (yy > lip) & (yy < POOL)
    img &= ~fall
    dark = np.zeros((H, W), bool)
    for x, off, L in STREAKS:
        for rep in range(-1, 4):
            y0 = LIP + ((off + 8 * t) % 64) + rep * 64
            dark |= (xx == x) & (yy >= y0) & (yy < y0 + L)
    img |= fall & ~dark
    # the river sliding in over the lip
    river = (xx > FX0) & (xx < FX1) & (yy >= LIP - 4) & (yy <= lip)
    img &= ~river
    img |= river & (((xx // 3 + yy * 5 + t * 3) % 7) < 2)
    img |= (np.abs(yy - lip) < 0.7) & (xx > FX0) & (xx < FX1)

    # pool: dark water, foam cloud at the foot of the falls, ripples spreading out
    pool = yy > POOL
    img &= ~pool
    img[POOL, :] = True
    for k in range(4):
        q = (p * 2 + k / 4) % 1.0
        rx, ry = 16 + q * 38, 2.5 + q * 9
        d = ((xx - 34) / rx) ** 2 + ((yy - (POOL + 3)) / ry) ** 2
        img |= pool & (np.abs(d - 1) < 0.07) & ((xx // 2 + k) % (1 + int(q * 3)) == 0)
    # foam: puffy white clouds churning at the foot of the falls, each with a dark outline
    for k in range(7):
        q = (p * 2 + k / 7) % 1.0
        fx = 34 + (k - 3) * 5.5 + 2.5 * math.sin(TAU * q + k)
        fy = POOL + 1 - q * 9
        r = 4.5 + q * 2.5 - (q > 0.7) * (q - 0.7) * 12
        if r <= 0.5:
            continue
        puff = disc(fx, fy, r)
        img &= ~dilate(puff)
        img |= puff & ((BAYER < 0.85 - q * 0.6) | ~erode(puff))
    img |= pool & (yy < POOL + 3) & (np.abs(xx - 34) < 17)

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
