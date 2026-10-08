"""A chunky little astronaut tumbling slowly through space: a round fishbowl helmet with a
glinting visor and a tiny antenna, a squat suit with stubby arms and legs, doing one full
roll per loop while it drifts past Saturn. 36 frames, seamless."""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, export

N = 36
FRAME_MS = 180
TAU = 2 * math.pi

rng = random.Random(42)
STARS = [(rng.randrange(2, W - 2), rng.randrange(2, H - 2), rng.random(), rng.random() < 0.25)
         for _ in range(34)]
SX, SY, SR = 30, 114, 15        # Saturn, low on the screen


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


class Local:
    """Pixel coordinates in the astronaut's own frame: origin at its middle, -y = up,
    rotated by th and scaled by k."""

    def __init__(self, cx, cy, th, k):
        c, s = math.cos(th), math.sin(th)
        self.x = (c * (xx - cx) + s * (yy - cy)) / k
        self.y = (-s * (xx - cx) + c * (yy - cy)) / k

    def ell(self, x, y, rx, ry):
        return ((self.x - x) / rx) ** 2 + ((self.y - y) / ry) ** 2 <= 1

    def rrect(self, x0, y0, x1, y1, r):
        """Rounded rectangle."""
        qx = np.maximum(np.maximum(x0 + r - self.x, self.x - (x1 - r)), 0)
        qy = np.maximum(np.maximum(y0 + r - self.y, self.y - (y1 - r)), 0)
        return (qx * qx + qy * qy <= r * r) & (self.x >= x0) & (self.x <= x1) & \
            (self.y >= y0) & (self.y <= y1)


def saturn(img, p):
    body = disc(SX, SY, SR)
    tilt = -0.32
    u = (xx - SX) * math.cos(tilt) + (yy - SY) * math.sin(tilt)
    v = -(xx - SX) * math.sin(tilt) + (yy - SY) * math.cos(tilt)
    d = (u / 31.0) ** 2 + (v / 7.5) ** 2
    ring = (d <= 1.0) & (d >= 0.5)
    front = v > 0
    img &= ~dilate(body | ring)
    # planet: lit from the upper right, with a few cloud bands that drift as it turns
    shade = -(xx - SX) * 0.7 + (yy - SY)
    lit = np.clip(0.85 - (shade + SR) / (2.2 * SR), 0.0, 0.85)
    img |= body & (BAYER < lit)
    for k, by in enumerate((-6, -1, 5)):
        wob = 0.8 * math.sin(TAU * p + k * 2)
        band = np.abs((yy - SY) - by - wob - 0.15 * (xx - SX)) < 0.6
        img &= ~(body & band)
    img |= body & ~erode(body) & (shade < 8)
    # ring: two crisp edges with a dithered middle; hidden behind the planet, over it in front
    edge = (d <= 1.0) & (d >= 0.86) | (d <= 0.62) & (d >= 0.5)
    mid = ring & ~edge & (BAYER < 0.35)
    vis = ~body | front
    img &= ~(dilate(ring & front) & body & ~ring)
    img |= (edge | mid) & vis


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

    saturn(img, p)

    # one full spin per loop around his own long axis (like a kebab on a spit): parts on
    # the front, sides and back slide round the body and hide behind it as he turns
    th = TAU * p
    tilt = 0.28 * math.sin(TAU * p) - 0.1                 # the spin axis wobbles a little
    cx = 34 + 2 * math.sin(TAU * p)
    cy = 54 + 3 * math.sin(TAU * p * 2)
    a = Local(cx, cy, tilt, 1.25)

    def around(angle, radius):
        """x offset and depth (+ = towards us) of a point at this angle round the body."""
        return radius * math.sin(th + angle), math.cos(th + angle)

    helmet = a.ell(0, -9, 10, 10)
    body = a.rrect(-9, -3, 9, 12, 5)
    lx, ld = around(-0.45, 4.5)
    rx_, rd = around(0.45, 4.5)
    leg_l = a.rrect(lx - 3, 10, lx + 3, 19.5, 2.4)
    leg_r = a.rrect(rx_ - 3, 10, rx_ + 3, 19.5, 2.4)
    px, pd = around(math.pi, 9.5)                          # air tank on his back
    pw = 2.4 + 3.6 * abs(math.cos(th))
    pack = a.rrect(px - pw, -2, px + pw, 9, 2)
    ax1, ad1 = around(math.pi / 2, 10.5)                   # arms on his sides
    ax2, ad2 = around(-math.pi / 2, 10.5)
    arm1 = a.ell(ax1, 3.5, 3.0, 4.4)
    arm2 = a.ell(ax2, 3.5, 3.0, 4.4)
    tx, td = around(0.9, 6.5)
    antenna = (np.abs(a.x - tx) < 0.7) & (a.y > -22) & (a.y < -18)
    bulb = a.ell(tx, -22.5, 1.8, 1.8)

    # back-to-front: parts facing away first, then the body, then parts facing us
    parts = [(leg_l, ld), (leg_r, rd), (pack, pd), (arm1, ad1), (arm2, ad2)]
    order = sorted(parts, key=lambda q: q[1])
    def stamp(m):
        nonlocal img
        img &= ~dilate(m)
        img |= m
    shape = helmet | body | leg_l | leg_r | pack | arm1 | arm2 | antenna | bulb
    img &= ~dilate(dilate(shape))
    img |= antenna | bulb
    for m, d in order:
        if d < 0:
            stamp(m)
    stamp(body)
    stamp(helmet)
    for m, d in order:
        if d >= 0:
            stamp(m)

    # visor on the front of the helmet: slides round and narrows, hidden when facing away
    vx, vd = around(0, 5.5)
    if vd > -0.2:
        vw = 1.2 + 6.0 * max(0.0, math.cos(th))
        visor = a.ell(vx, -9.5, vw, 6.2) & a.ell(0, -9, 8.6, 8.6)
        img &= ~visor
        gx = vx - 0.4 * vw
        img |= visor & a.ell(gx, -12.5, max(0.8, 0.35 * vw), 1.4)          # glint
    # belt all the way round; a chest patch on the front
    img &= ~(body & (np.abs(a.y - 6) < 0.6) & ~(pack & (pd > 0)))
    cpx, cpd = around(0, 5)
    if cpd > 0.3:
        cw = 3 * cpd
        img &= ~(body & a.rrect(cpx - cw, 0, cpx + cw, 4, 1) & ~a.rrect(cpx - cw + 1, 1, cpx + cw - 1, 3, 0.5))
    # seams so overlapping parts stay readable
    for m, d in parts:
        if d >= 0:
            img &= ~(dilate(m) & ~m & (body | helmet))
    img &= ~(leg_l & (np.abs(a.y - 16.5) < 0.6)) & ~(leg_r & (np.abs(a.y - 16.5) < 0.6))

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
