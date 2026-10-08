"""Gaming layer: full-screen spell sequence, 48 frames, seamless.
   frames  0-15  FIREBALL  rises from the bottom, grows, explodes, embers rain down
   frames 16-31  LIGHTNING storm clouds crackle, main bolt + screen flash, branches, afterglow
   frames 32-47  THORNS    thorny vines burst up the screen, bloom, then wither away
"""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, rect, thick_line, export

N = 48
TAU = 2 * math.pi


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def put(img, x, y, v=True):
    x, y = int(round(x)), int(round(y))
    if 0 < x < W - 1 and 0 < y < H - 1:
        img[y, x] = v


def sparkle(img, x, y, size):
    for d in range(-size, size + 1):
        put(img, x + d, y)
        put(img, x, y + d)


rng = random.Random(21)
STARS = [(rng.randrange(2, W - 2), rng.randrange(2, H - 2), rng.random()) for _ in range(18)]


# --------------------------------------------------------------------------- fireball
EMBERS = [(rng.uniform(0, TAU), rng.uniform(0.6, 1.0), rng.uniform(-0.5, 0.5)) for _ in range(22)]
BOOM = (34, 40)


def fireball(img, x, y, r, f):
    m = disc(x, y, r)
    for i in range(1, 8):                               # tail trailing downward
        g = i / 8
        wob = 2.5 * math.sin(f * 9 + i * 1.4) * g
        m |= disc(x + wob, y + r * 0.8 * i, r * (1 - g * 0.85))
    for side in (-1, 1):                                # side flame licks
        for i in range(1, 6):
            m |= disc(x + side * (r * 0.55 + i * 0.9 + math.sin(f * 7 + side) * 1.5),
                      y + r * 0.6 * i, max(0.8, r * 0.4 * (1 - i / 6)))
    img &= ~dilate(m)
    img |= m
    core = disc(x, y - 1, r * 0.6)
    img &= ~(core & (BAYER < 0.5))                      # dithered hot core
    img |= disc(x, y - 1, r * 0.25)
    # heat sparks shedding off
    for k in range(5):
        a = k * 1.3 + f * 11
        put(img, x + math.cos(a) * (r + 3 + k), y + r + 4 + k * 4)


def fire_phase(img, t):
    bx, by = BOOM
    if t < 10:                                          # rise
        f = t / 9
        x = 34 + 7 * math.sin(f * math.pi * 1.5)
        y = 138 - f * (138 - by)
        fireball(img, x, y, 5 + 6 * f, f)
    elif t == 10:                                       # impact flash
        img |= disc(bx, by, 22) & ~(disc(bx, by, 12) & (BAYER < 0.5))
        for k in range(12):
            a = TAU * k / 12
            img |= thick_line(bx + 22 * math.cos(a), by + 22 * math.sin(a),
                              bx + 32 * math.cos(a), by + 32 * math.sin(a), 2)
    elif t == 11:                                       # shockwave ring with flame tongues
        ring = disc(bx, by, 31) & ~disc(bx, by, 26)
        img |= ring
        img |= disc(bx, by, 22) & (BAYER < 0.3)
        for k in range(14):
            a = TAU * k / 14 + 0.2
            img |= disc(bx + 33 * math.cos(a), by + 33 * math.sin(a), 2.5)
    elif t == 12:                                       # ring fading
        img |= (disc(bx, by, 40) & ~disc(bx, by, 35)) & (BAYER < 0.5)
        img |= disc(bx, by, 30) & (BAYER < 0.1)
    if t >= 11:                                         # embers fly out then rain down
        s = t - 10
        for a, sp, drift in EMBERS:
            x = bx + math.cos(a) * sp * 9 * s + drift * s
            y = by + math.sin(a) * sp * 7 * s + 1.6 * s * s
            if t < 15 or (int(a * 10) % 2 == 0):
                sparkle(img, x, y, 1 if (s < 4 or (t + int(a * 7)) % 2) else 0)


# --------------------------------------------------------------------------- lightning
def make_bolt(seed, x0, y0, y1, jitter):
    r = random.Random(seed)
    pts = [(x0, y0)]
    x, y = x0, y0
    while y < y1:
        y += r.uniform(5, 10)
        x = min(W - 4, max(3, x + r.uniform(-jitter, jitter)))
        pts.append((x, min(y, y1)))
    return pts


MAIN = make_bolt(4, 30, 16, 136, 9)
BRANCHES = [make_bolt(10 + i, *MAIN[j], MAIN[j][1] + 30 + 8 * i, 7) for i, j in enumerate((2, 5, 8))]
SIDE2 = make_bolt(77, 50, 16, 136, 8)
SIDE2_BRANCH = make_bolt(78, *SIDE2[4], SIDE2[4][1] + 34, 7)
SIDE_BOLTS = [make_bolt(40, 12, 16, 96, 7), make_bolt(41, 56, 16, 110, 7)]


def draw_bolt(pts, w):
    m = np.zeros((H, W), bool)
    for (a, b), (c, d) in zip(pts, pts[1:]):
        m |= thick_line(a, b, c, d, w)
    return m


def clouds(img, t, bright):
    for k, (cx, cy, r) in enumerate(((8, 6, 11), (24, 2, 12), (42, 5, 13), (60, 3, 11), (34, 12, 9))):
        cx2 = cx + 2 * math.sin(t * 0.5 + k)
        c = disc(cx2, cy, r)
        img |= c & (BAYER < (0.55 if bright else 0.22))
        img |= c & ~disc(cx2, cy, r - 1) & (yy > cy)


def lightning_phase(img, t):
    clouds(img, t, t in (3, 4))
    if t < 3:                                           # crackling charge in the clouds
        for k in range(4 + t * 3):
            put(img, 6 + (k * 13 + t * 7) % 56, 14 + (k * 5 + t * 3) % 8)
        if t == 2:
            img |= draw_bolt(MAIN[:3], 1)
    elif t == 3:                                        # strike
        img |= draw_bolt(MAIN, 3)
        for b in BRANCHES:
            img |= draw_bolt(b, 1)
    elif t == 4:                                        # full-screen flash: invert everything
        img |= draw_bolt(MAIN, 3) | draw_bolt(BRANCHES[0], 1) | draw_bolt(BRANCHES[1], 1)
        img[:] = ~img
    elif t in (5, 6):
        img |= draw_bolt(MAIN, 2 if t == 5 else 1)
        img |= draw_bolt(BRANCHES[2], 1)
    elif 7 <= t <= 10:                                  # side strikes
        b = SIDE_BOLTS[0] if t < 9 else SIDE_BOLTS[1]
        img |= draw_bolt(b, 2 if t % 2 else 1)
        img |= draw_bolt(MAIN, 1) & (BAYER < 0.4 - 0.1 * (t - 7))
    elif t == 12:                                       # second strike from the right
        img |= draw_bolt(SIDE2, 3) | draw_bolt(SIDE2_BRANCH, 1)
    elif t == 13:
        img |= draw_bolt(SIDE2, 1)
    elif t >= 11:                                       # afterglow: scattered static arcs
        k = (t - 11) if t == 11 else (t - 13)
        for j in range(5 - k):
            x = 8 + (j * 17 + k * 5) % 52
            y = 128 - (j * 23 + k * 7) % 60
            for s in range(3):
                put(img, x + s, y + (s % 2) * 2 - 1)
        img |= (yy > 132) & (BAYER < 0.3 - k * 0.06)     # scorch glow at the strike point


# --------------------------------------------------------------------------- thorns
VINES = [  # base x, sway amplitude, sway phase, max height, side the bloom faces
    (8, 4, 0.0, 128, 1), (24, 5, 2.0, 96, -1), (42, 5, 4.0, 116, 1), (60, 4, 1.0, 104, -1)]


def vine_point(x0, amp, ph, s):
    return x0 + amp * math.sin(s / 11.0 + ph), H - 2 - s


def thorns_phase(img, t):
    grow = min(1.0, (t + 1) / 10)                       # 0-9 grow, 10-12 hold, 13-15 wither
    wither = max(0.0, (t - 12) / 3)
    m = np.zeros((H, W), bool)
    for i, (x0, amp, ph, hmax, face) in enumerate(VINES):
        L = hmax * min(1.0, grow * (1.15 - i * 0.05))
        s = 0
        prev = vine_point(x0, amp, ph, 0)
        while s < L:
            s2 = min(L, s + 3)
            p2 = vine_point(x0, amp, ph, s2)
            m |= thick_line(*prev, *p2, 3 if s < L - 10 else 2)
            prev, s = p2, s2
        # thorns: alternate sides every 7 px, pointing outward and up
        for k, s in enumerate(range(6, int(L) - 3, 7)):
            px, py = vine_point(x0, amp, ph, s)
            side = 1 if k % 2 else -1
            m |= thick_line(px, py, px + side * 5, py - 3, 1.2)
            m |= thick_line(px, py + 1, px + side * 3, py - 1, 1.6)
        tx, ty = vine_point(x0, amp, ph, L)
        if grow >= 1.0 and wither < 0.7:                # bloom at the tip once grown
            r = 3 + (1 if t in (11, 12) else 0)
            for k in range(5):
                a = TAU * k / 5 + i
                m |= disc(tx + r * math.cos(a), ty + r * math.sin(a), 2)
        else:
            m |= thick_line(tx, ty, tx + face * 3, ty - 3, 1.5)   # curled growing tip
    # cross-tendrils from the screen edges
    for side, y0 in ((-1, 60), (1, 34), (-1, 20)):
        L = 30 * max(0.0, min(1.0, (t - 3) / 7))
        x_start = 1 if side < 0 else W - 2
        prev = (x_start, y0)
        for s in range(2, int(L) + 1, 2):
            p2 = (x_start - side * s, y0 + 4 * math.sin(s / 6.0))
            m |= thick_line(*prev, *p2, 2)
            if s % 8 == 0:
                m |= thick_line(*p2, p2[0] - side * 2, p2[1] - 4 * (1 if (s // 8) % 2 else -1), 1.2)
            prev = p2
    if wither > 0:
        m &= BAYER >= wither * 0.95                     # dissolve away
        img |= (yy > H - 8) & (BAYER < 0.3 * (1 - wither))
    img &= ~dilate(m)
    img |= m


def frame(t):
    img = np.zeros((H, W), bool)
    if 16 <= t < 32:
        pass                                            # storm: no stars
    else:
        for x, y, ph in STARS:
            if math.sin(TAU * (t / 16 + ph)) > 0:
                img[y, x] = True
    if t < 16:
        fire_phase(img, t)
    elif t < 32:
        lightning_phase(img, t - 16)
    else:
        thorns_phase(img, t - 32)
    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
