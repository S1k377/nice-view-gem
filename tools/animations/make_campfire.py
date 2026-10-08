"""Left half (base layer): a cozy campfire. 32 frames, seamless.
Flickering fire, soft smoke, a cat asleep by the fire (breathing, floating z's),
quiet stars and a moon."""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, rect, thick_line, sprite, export

N = 32
TAU = 2 * math.pi
FX, FIRE_BASE = 33, 114
rng = random.Random(7)
STARS = [(rng.randrange(3, W - 3), rng.randrange(4, 56), rng.random()) for _ in range(18)]
TONGUES = [(33, 8, 28, 0.0, 2), (28, 5, 18, 1.7, 3), (38, 5, 19, 3.9, 3), (31, 4, 22, 5.1, 2), (36, 4, 21, 2.4, 2)]

NOISE = np.random.RandomState(1).rand(H, W)
ZED = ["XXX", "..X", ".X.", "X..", "XXX"]


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
        shift = lean * f * f + 1.4 * math.sin(f * 5 + phase) * f
        if 0 <= y < H:
            m[y, max(0, int(round(cx + shift - width))):min(W, int(round(cx + shift + width)) + 1)] = True
    return m


def cat(t):
    """Curled-up sleeping cat facing the fire, on the left. Breathes once per 16 frames."""
    breath = 0.6 * math.sin(TAU * t / 16)
    body = ((xx - 11) / 9.5) ** 2 + ((yy - 123) / (5.0 + breath)) ** 2 <= 1
    body &= yy <= 127
    head = disc(19, 120 - breath * 0.5, 4.2)
    ear1 = (yy >= 113 - breath) & (yy <= 117) & (np.abs(xx - 17) <= (yy - (113 - breath)) * 0.6)
    ear2 = (yy >= 113.5 - breath) & (yy <= 117) & (np.abs(xx - 22) <= (yy - (113.5 - breath)) * 0.6)
    tail = np.zeros((H, W), bool)
    for i in range(10):                                  # tail wrapped around the front
        a = math.pi * (0.15 + i / 12)
        tail |= disc(12 + 9 * math.cos(a), 124 + 3.2 * math.sin(a), 1.6)
    shape = body | head | ear1 | ear2 | tail
    fill = shape.copy()
    tail_edge = dilate(tail) & body & ~tail              # separate the tail from the body
    fill &= ~tail_edge
    eyes = ((yy == int(round(120 - breath * 0.5))) & (((xx >= 17) & (xx <= 18)) | ((xx >= 20) & (xx <= 21))))
    nose = (yy == int(round(122 - breath * 0.5))) & (xx == 19)
    return shape, fill & ~eyes & ~nose, eyes


def frame(t):
    p = t / N
    img = np.zeros((H, W), bool)

    # moon + stars
    img |= disc(54, 14, 6) & ~disc(57, 12, 5)
    for sx, sy, ph in STARS:
        b = math.sin(TAU * (p * 2 + ph))
        if b > -0.4:
            img[sy, sx] = True

    # soft smoke wisps (thin dithered ribbons that sway and fade)
    for k in range(3):
        for i in range(26):
            q = i / 26
            y = 80 - i * 2.4
            x = FX + 1 + 5 * math.sin(TAU * (p * 2 - q * 1.2) + k * 2.1) * (0.4 + q)
            if (i + k + t) % 3 != 0 and q < 1 - k * 0.15:
                r = 0.8 + q * 2.2
                img |= disc(x + k * 2 - 2, y, r) & (BAYER < 0.55 * (1 - q))

    # ground
    img[127:, :] = False
    img[127, :] = True
    img |= (yy > 128) & (BAYER < 0.18)

    # flames
    flame = np.zeros((H, W), bool)
    core = np.zeros((H, W), bool)
    for cx, hw, h, ph, sp in TONGUES:
        a = TAU * p * sp + ph
        hh = h * (0.82 + 0.18 * math.sin(a))
        lean = 2.5 * math.sin(a * 0.5 + ph)
        flame |= tongue(cx, hw, hh, lean, a)
        core |= tongue(cx, max(1, hw - 3), hh * 0.5, lean * 0.6, a)
    img &= ~dilate(flame)
    img |= flame
    img &= ~core
    img |= tongue(FX, 2.5, 7 + 2 * math.sin(TAU * p * 3), 1.2 * math.sin(TAU * p * 2), TAU * p * 2) & core

    # logs (crossed) with end rings
    logs = np.zeros((H, W), bool)
    inner = np.zeros((H, W), bool)
    for (x0, y0, x1, y1) in ((22, 124, 45, 114), (22, 114, 45, 124)):
        logs |= thick_line(x0, y0, x1, y1, 6)
        inner |= thick_line(x0, y0, x1, y1, 3)
    img &= ~dilate(dilate(logs))
    img |= logs & ~inner
    img |= inner & ((xx + yy) % 5 == 0)
    for cx, cy in ((22, 114), (22, 124), (45, 114), (45, 124)):
        img &= ~disc(cx, cy, 3)
        img |= disc(cx, cy, 3) & ~disc(cx, cy, 2)
        img[cy, cx] = True
    for i, (ex, ey) in enumerate(((28, 119), (33, 117), (38, 120))):     # embers in the bed
        if math.sin(TAU * (p * 3 + i * 0.37)) > -0.3:
            img[ey, ex:ex + 2] = True

    # sleeping cat on the left + floating z's
    shape, fill, eyes = cat(t)
    img &= ~dilate(dilate(shape))
    img |= fill
    for k in range(2):
        q = (p * 2 + k * 0.5) % 1.0
        if q < 0.85:
            on, _ = sprite(ZED if q > 0.3 else ["XX", ".X", "XX"], int(14 + q * 6), int(108 - q * 30))
            img &= ~dilate(on)
            img |= on

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
