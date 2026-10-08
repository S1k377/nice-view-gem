"""Astronaut drifting in space: gentle tilt and bob, one arm waving, a tether snaking off
screen, a ringed planet turning below, twinkling stars and drifting space dust.
36 frames, seamless."""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, export

N = 36
FRAME_MS = 200
TAU = 2 * math.pi

rng = random.Random(42)
STARS = [(rng.randrange(2, W - 2), rng.randrange(2, 100), rng.random(), rng.random() < 0.25)
         for _ in range(30)]
DUST_TILE = 36                                   # dust repeats every 36 px and moves 1 px/frame
DUST = [(rng.randrange(2, W - 2), rng.randrange(0, DUST_TILE)) for _ in range(5)]
PX, PY, PR = 58, 136, 36                         # planet, mostly below the bottom-right corner


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


class Body:
    """Shapes in the astronaut's own rotated coordinate frame (origin = chest, -y = up)."""

    def __init__(self, cx, cy, th, scale=1.0):
        c, s = math.cos(th), math.sin(th)
        self.lx = (c * (xx - cx) + s * (yy - cy)) / scale
        self.ly = (-s * (xx - cx) + c * (yy - cy)) / scale
        self.cx, self.cy, self.c, self.s, self.k = cx, cy, c, s, scale

    def disc(self, x, y, r):
        return (self.lx - x) ** 2 + (self.ly - y) ** 2 <= r * r

    def ell(self, x, y, rx, ry):
        return ((self.lx - x) / rx) ** 2 + ((self.ly - y) / ry) ** 2 <= 1

    def rect(self, x0, y0, x1, y1):
        return (self.lx >= x0) & (self.lx <= x1) & (self.ly >= y0) & (self.ly <= y1)

    def line(self, x0, y0, x1, y1, w):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy or 1
        t = np.clip(((self.lx - x0) * dx + (self.ly - y0) * dy) / L2, 0, 1)
        return (self.lx - x0 - t * dx) ** 2 + (self.ly - y0 - t * dy) ** 2 <= (w / 2) ** 2

    def to_screen(self, x, y):
        x, y = x * self.k, y * self.k
        return self.cx + self.c * x - self.s * y, self.cy + self.s * x + self.c * y


def planet(img, p):
    body = disc(PX, PY, PR)
    img &= ~dilate(body)
    # surface bands that slide sideways as it turns (pattern period divides the loop)
    shift = p * 24
    band = np.sin((yy - PY) / 3.2 + np.sin((xx + shift) / 7.0) * 0.9)
    shade = (xx - PX) + (yy - PY) * 0.6                          # lit from the upper left
    lit = np.clip(0.75 - (shade + PR) / (2.2 * PR), 0.05, 0.75)
    img |= body & (BAYER < lit) & (band > -0.2)
    img |= body & ~erode(body) & (shade < 10)
    # ring: back half hidden behind the planet, front half drawn over it
    ring = ((xx - PX) / 52.0) ** 2 + ((yy - PY + 6 - (xx - PX) * 0.32) / 9.0) ** 2
    ring_m = (ring <= 1) & (ring >= 0.8)
    front = (yy - PY + 6 - (xx - PX) * 0.32) > 0
    img |= ring_m & (~body | front)
    img &= ~((ring <= 0.8) & (ring >= 0.68) & front & body)     # gap between ring and planet


def frame(t):
    p = t / N
    img = np.zeros((H, W), bool)

    for x, y, ph, big in STARS:
        b = math.sin(TAU * (2 * p + ph))
        if b > -0.5:
            img[y, x] = True
        if big and b > 0.6:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                img[y + dy, x + dx] = True
    for x, y in DUST:                                           # drifting dust, seamless
        for rep in range(-1, H // DUST_TILE + 2):
            yy0 = (y + t) % DUST_TILE + rep * DUST_TILE
            if 1 <= yy0 < H - 1:
                img[yy0, x] = True

    planet(img, p)

    # astronaut pose for this frame
    th = math.radians(9) * math.sin(TAU * p)
    cx = 33 + 2.5 * math.sin(TAU * p + 1.0)
    cy = 60 + 3.5 * math.sin(TAU * p)
    a = Body(cx, cy, th, 1.28)
    wave = math.sin(TAU * p * 3)

    suit = np.zeros((H, W), bool)
    dark = np.zeros((H, W), bool)
    # backpack (life support) peeking out behind the shoulders
    pack = a.rect(-10, -9, 10, 9)
    # legs: hips -> knees -> boots, relaxed float
    kick = 1.5 * math.sin(TAU * p * 2)
    suit |= a.line(-4, 9, -7, 17 + kick, 5.5) | a.line(-7, 17 + kick, -4, 25 + kick, 5)
    suit |= a.line(4, 9, 8, 16 - kick, 5.5) | a.line(8, 16 - kick, 7, 24 - kick, 5)
    suit |= a.rect(-8, 24 + kick, -1, 28 + kick) | a.rect(4, 23 - kick, 11, 27 - kick)   # boots
    dark |= a.rect(-9, 16 + kick, -4, 16.8 + kick) | a.rect(5, 15 - kick, 10, 15.8 - kick)  # knees
    # torso with chest control box and belt
    suit |= a.rect(-8, -6, 8, 11)
    dark |= a.rect(-4, -1, 4, 5) & ~a.rect(-3, 0, 3, 4)
    dark |= a.rect(-2.5, 1.5, -1.5, 2.5) | a.rect(1.5, 1.5, 2.5, 2.5)
    dark |= a.rect(-8, 8, 8, 8.8)
    # arms: viewer-left arm waves, right arm reaches down toward the tether clip
    hx, hy = -17 + 2 * wave, -14 - 4 * wave
    suit |= a.line(-8, -4, -14, -6 - wave, 5) | a.line(-14, -6 - wave, hx, hy, 4.5)
    suit |= a.disc(hx, hy, 3)
    suit |= a.line(8, -4, 13, 4, 5) | a.line(13, 4, 11, 11, 4.5) | a.disc(11, 12, 2.8)
    # helmet with a dark visor and a bright reflection
    suit |= a.disc(0, -15, 9.5)
    visor = a.ell(1.5, -14.5, 6.6, 5)
    dark |= visor
    shine = a.ell(-1.5, -17, 3.2, 1.6) & ~a.ell(-1.0, -16.2, 3.0, 1.4)
    dark |= a.disc(0, -15, 9.5) & ~a.disc(0, -15, 8.6) & (a.ly > -12)   # rim shadow

    img &= ~dilate(dilate(suit | pack))
    img |= pack & ~erode(pack)
    img |= pack & (BAYER < 0.3)
    img &= ~dilate(suit)
    img |= suit
    img &= ~dark
    img |= shine & visor
    img |= visor & a.disc(3.5, -12, 0.9)                         # second glint

    # tether from the hip clip, snaking up and off the right edge
    sx, sy = a.to_screen(11, 12)
    pts = []
    for i in range(40):
        q = i / 39
        x = sx + q * (W + 6 - sx) + 5 * math.sin(TAU * (q * 1.5 - p)) * q
        y = sy - q * 70 + 4 * math.sin(TAU * (q * 2 + p)) * q
        pts.append((x, y))
    teth = np.zeros((H, W), bool)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for j in range(n + 1):
            X, Y = int(round(x0 + (x1 - x0) * j / n)), int(round(y0 + (y1 - y0) * j / n))
            if 0 < X < W - 1 and 0 < Y < H - 1:
                teth[Y, X] = True
    teth &= ~dilate(suit)
    img &= ~(dilate(teth) & ~teth)                               # thin dark halo
    img |= teth

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
