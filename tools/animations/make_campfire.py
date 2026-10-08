"""Left half (base layer): a cozy campfire. 32 frames, seamless.
Flickering fire, soft smoke, a cat asleep by the fire (breathing, floating z's),
quiet stars and a moon."""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, rect, thick_line, sprite, export

N = 32
TAU = 2 * math.pi
FX, FIRE_BASE = 49, 119
rng = random.Random(7)
STARS = [(x, y, ph) for x, y, ph in ((rng.randrange(3, W - 3), rng.randrange(4, 60), rng.random()) for _ in range(22))
         if (x - 15) ** 2 + (y - 16) ** 2 > 100]
TONGUES = [(49, 14, 46, 0.0, 2), (41, 9, 30, 1.7, 3), (57, 8, 31, 3.9, 3), (45, 7, 36, 5.1, 2), (53, 7, 35, 2.4, 2)]

NOISE = np.random.RandomState(1).rand(H, W)
ZED_S = ["XXX", ".X.", "XXX"]
ZED_M = ["XXX", "..X", ".X.", "X..", "XXX"]
ZED_L = ["XXXXX", "...X.", "..X..", ".X...", "XXXXX"]


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
        shift = lean * f * f + 2.1 * math.sin(f * 5 + phase) * f
        if 0 <= y < H:
            m[y, max(0, int(round(cx + shift - width))):min(W, int(round(cx + shift + width)) + 1)] = True
    return m


def cat(t):
    """Curled-up sleeping cat facing the fire, on the left. Breathes once per 16 frames."""
    breath = 0.9 * math.sin(TAU * t / 16)
    hy = 121 - breath * 0.6
    body = ((xx - 15) / 14.0) ** 2 + ((yy - 127) / (7.0 + breath)) ** 2 <= 1
    body &= yy <= 133
    head = disc(27, hy, 6.3)
    ear1 = (yy >= hy - 9.5) & (yy <= hy - 3) & (np.abs(xx - 23.5) <= (yy - (hy - 9.5)) * 0.65)
    ear2 = (yy >= hy - 9) & (yy <= hy - 3) & (np.abs(xx - 31) <= (yy - (hy - 9)) * 0.65)
    tail = np.zeros((H, W), bool)
    for i in range(13):                                  # tail wrapped around the front
        a = math.pi * (0.15 + i / 15)
        tail |= disc(16 + 14 * math.cos(a), 129 + 4.6 * math.sin(a), 2.3)
    shape = body | head | ear1 | ear2 | tail
    fill = shape.copy()
    tail_edge = dilate(tail) & body & ~tail              # separate the tail from the body
    fill &= ~tail_edge
    ey = int(round(hy))
    eyes = (((yy == ey) & (((xx >= 23) & (xx <= 25)) | ((xx >= 28) & (xx <= 30))))
            | ((yy == ey - 1) & ((xx == 22) | (xx == 31))))                 # closed, curved
    nose = (yy == ey + 2) & (xx >= 26) & (xx <= 27)
    return shape, fill & ~eyes & ~nose, eyes


def frame(t):
    p = t / N
    img = np.zeros((H, W), bool)

    # moon + stars
    img |= disc(15, 16, 7) & ~disc(18, 14, 6)
    for sx, sy, ph in STARS:
        b = math.sin(TAU * (p * 2 + ph))
        if b > -0.4:
            img[sy, sx] = True

    # soft smoke wisps (thin dithered ribbons that sway and fade)
    for k in range(3):
        for i in range(27):
            q = i / 27
            y = 76 - i * 2.6
            x = FX - 2 + 6 * math.sin(TAU * (p * 2 - q * 1.2) + k * 2.1) * (0.4 + q)
            if (i + k + t) % 3 != 0 and q < 1 - k * 0.15:
                r = 1.0 + q * 2.6
                img |= disc(x + k * 2 - 2, y, r) & (BAYER < 0.55 * (1 - q))

    # ground
    img[134:, :] = False
    img[134, :] = True
    img |= (yy > 135) & (BAYER < 0.18)

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
    img |= tongue(FX, 4, 11 + 3 * math.sin(TAU * p * 3), 1.8 * math.sin(TAU * p * 2), TAU * p * 2) & core

    # logs (crossed) with end rings
    logs = np.zeros((H, W), bool)
    inner = np.zeros((H, W), bool)
    for (x0, y0, x1, y1) in ((37, 129, 61, 116), (37, 116, 61, 129)):
        logs |= thick_line(x0, y0, x1, y1, 9)
        inner |= thick_line(x0, y0, x1, y1, 5)
    img &= ~dilate(dilate(logs))
    img |= logs & ~inner
    img |= inner & ((xx + yy) % 5 == 0)
    for cx, cy in ((37, 116), (37, 129), (61, 116), (61, 129)):
        img &= ~disc(cx, cy, 4.5)
        img |= disc(cx, cy, 4.5) & ~disc(cx, cy, 3.3)
        img |= disc(cx, cy, 1)
    for i, (ex, ey) in enumerate(((43, 125), (49, 123), (55, 126))):     # embers in the bed
        if math.sin(TAU * (p * 3 + i * 0.37)) > -0.3:
            img[ey, ex:ex + 3] = True

    # sleeping cat on the left + floating z's
    shape, fill, eyes = cat(t)
    img &= ~dilate(dilate(shape))
    img |= fill
    for k in range(2):
        q = (p * 2 + k * 0.5) % 1.0
        if q < 0.85:
            z = ZED_S if q < 0.3 else (ZED_M if q < 0.6 else ZED_L)
            on, _ = sprite(z, int(19 + q * 8), int(104 - q * 36))
            img &= ~dilate(on)
            img |= on

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
