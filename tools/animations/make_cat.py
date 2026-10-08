"""A cat jumping around a room: sits on the floor, leaps up to a shelf, turns, leaps to a
higher shelf, looks out the window, then drops back down. 44 frames, seamless."""
import math, os
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, rect, thick_line, export

N = 44
FRAME_MS = 140
TAU = 2 * math.pi
FLOOR, SHELF_A, SHELF_B = 132, 94, 56

# Sprites face right. 'X' = white, 'o' = black detail inside the cat.
SIT_UP = [
    "............X..X.",
    "............XXXX.",
    "...........XXXXXX",
    "...........XoXXoX",
    "...........XXXXXX",
    "............XXXX.",
    "...........XXXX..",
    "..........XXXXX..",
    ".........XXXXXX..",
    "........XXXXXXX..",
    "........XXXXXXX..",
    "..X....XXXXXXXX..",
    ".X.X...XXXXXXXX..",
    ".X..X..XXXXXXXXX.",
    ".X...XXXXXXXoXXX.",
    "..X..XXXXXXXoXXX.",
    "...XXXXXXXXXoXXX.",
    ".....XXXXXXXXXXXX",
]
SIT_DOWN = [r for r in SIT_UP[:11]] + [
    "........XXXXXXX..",
    ".......XXXXXXXX..",
    ".......XXXXXXXXX.",
    ".....XXXXXXXoXXX.",
    "...XXXXXXXXXoXXX.",
    ".XXX.XXXXXXXoXXX.",
    "X....XXXXXXXXXXXX",
]
SIT_BLINK = [r.replace("XoXXoX", "XXXXXX") if "XoXXoX" in r else r for r in SIT_UP]
CROUCH = [
    "................X..X",
    "................XXXX",
    "...............XXXXX",
    "...............XoXXo",
    "....XXXXXXXXXXXXXXXX",
    ".XXXXXXXXXXXXXXXXXX.",
    "X..XXXXXXXXXXXXXXXX.",
    "...XXXXXXXXXXXXXXX..",
    "...XXoXXXX...XXoXX..",
    "..XX..XX.....XX.XX..",
]
LEAP = [
    "....................X..X",
    "...................XXXX.",
    "...................XXXXX",
    "..XXXXXXXXXXXXXXXXXXXoXX",
    "XX.XXXXXXXXXXXXXXXXXXXX.",
    "X...XXXXXXXXXXXXXXXXXX..",
    "...XXXX.........XXXX....",
    "..XX...............XX...",
    ".XX.................XX..",
]


def to_arr(sp):
    on = np.array([[c == "X" for c in r] for r in sp])
    dark = np.array([[c == "o" for c in r] for r in sp])
    return on, dark


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


SCALE = 1.5


def place(sprite, fx, fy, face=1, angle=0.0, scale=SCALE):
    """Masks for a sprite whose bottom-centre (feet) sits at (fx, fy), optionally mirrored
    (face=-1) and rotated about that point (radians, positive = nose down)."""
    on, dark = to_arr(sprite)
    if face < 0:
        on, dark = on[:, ::-1], dark[:, ::-1]
    h, w = on.shape
    c, s = math.cos(-angle * face), math.sin(-angle * face)
    # map each screen pixel back into sprite space (centre of rotation = feet)
    dx, dy = xx - fx, yy - fy
    sx = (c * dx - s * dy) / scale + w / 2
    sy = (s * dx + c * dy) / scale + h
    ix, iy = np.floor(sx).astype(int), np.floor(sy).astype(int)
    ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
    ixc, iyc = np.clip(ix, 0, w - 1), np.clip(iy, 0, h - 1)
    return ok & on[iyc, ixc], ok & dark[iyc, ixc]


def arc(t, t0, t1, p0, p1, height):
    q = (t - t0) / (t1 - t0)
    x = p0[0] + (p1[0] - p0[0]) * q
    y = p0[1] + (p1[1] - p0[1]) * q - height * 4 * q * (1 - q)
    # tilt with the direction of travel
    vx = (p1[0] - p0[0])
    vy = (p1[1] - p0[1]) - height * 4 * (1 - 2 * q)
    ang = math.atan2(vy, abs(vx) + 1e-6)
    return x, y, ang


# keyframes: (first frame, last frame, pose)
A, B, F0 = (29, FLOOR), (48, SHELF_A), (22, SHELF_B)


def pose(t):
    """(sprite, feet_x, feet_y, facing, angle) for frame t."""
    if t <= 5:
        return (SIT_BLINK if t == 3 else (SIT_UP if t % 4 < 2 else SIT_DOWN)), 29, FLOOR, 1, 0
    if t <= 7:
        return CROUCH, 29, FLOOR, 1, 0
    if t <= 12:
        x, y, a = arc(t, 7.5, 12.5, A, B, 22)
        return LEAP, x, y, 1, max(-0.5, min(0.5, a * 0.7))
    if t == 13:
        return CROUCH, 48, SHELF_A, 1, 0
    if t <= 19:
        return (SIT_UP if t % 4 < 2 else SIT_DOWN), 48, SHELF_A, -1, 0
    if t <= 21:
        return CROUCH, 48, SHELF_A, -1, 0
    if t <= 26:
        x, y, a = arc(t, 21.5, 26.5, B, F0, 20)
        return LEAP, x, y, -1, max(-0.5, min(0.5, a * 0.7))
    if t == 27:
        return CROUCH, 22, SHELF_B, -1, 0
    if t <= 33:
        sp = SIT_BLINK if t == 30 else (SIT_UP if t % 4 < 2 else SIT_DOWN)
        return sp, 22, SHELF_B, 1, 0
    if t <= 35:
        return CROUCH, 22, SHELF_B, 1, 0
    if t <= 40:
        x, y, a = arc(t, 35.5, 40.5, F0, (29, FLOOR), 8)
        return LEAP, x, y, 1, max(-0.3, min(0.6, a * 0.7))
    if t == 41:
        return CROUCH, 29, FLOOR, 1, 0
    return SIT_DOWN if t == 42 else SIT_UP, 29, FLOOR, 1, 0


def room(t):
    img = np.zeros((H, W), bool)
    # window with a moon and a few stars, upper right
    win = rect(38, 8, 63, 40)
    img |= win & ~rect(40, 10, 61, 38)
    img |= (win & ((xx == 50) | (yy == 24)))
    img |= disc(56, 16, 3.5) & ~disc(57.5, 15, 3)
    for sx, sy, ph in ((44, 14, 0.0), (45, 31, 0.4), (57, 32, 0.7), (43, 21, 0.2)):
        if math.sin(TAU * (t / N * 2 + ph)) > -0.3:
            img[sy, sx] = True
    img |= rect(36, 41, 65, 42)                                    # sill
    # shelves with brackets
    img |= rect(2, SHELF_B + 1, 36, SHELF_B + 2)
    img |= thick_line(6, SHELF_B + 3, 12, SHELF_B + 9, 1.4) | rect(4, SHELF_B + 3, 5, SHELF_B + 10)
    img |= thick_line(30, SHELF_B + 3, 24, SHELF_B + 9, 1.4) | rect(31, SHELF_B + 3, 32, SHELF_B + 10)
    img |= rect(32, SHELF_A + 1, 65, SHELF_A + 2)
    img |= thick_line(37, SHELF_A + 3, 43, SHELF_A + 9, 1.4) | rect(35, SHELF_A + 3, 36, SHELF_A + 10)
    img |= thick_line(61, SHELF_A + 3, 55, SHELF_A + 9, 1.4) | rect(62, SHELF_A + 3, 63, SHELF_A + 10)
    # a little potted plant on the upper shelf
    img |= rect(4, SHELF_B - 5, 9, SHELF_B) & ~rect(5, SHELF_B - 4, 8, SHELF_B - 1)
    img |= thick_line(6.5, SHELF_B - 5, 4, SHELF_B - 11, 1.3) | thick_line(6.5, SHELF_B - 5, 9, SHELF_B - 10, 1.3)
    img |= thick_line(6.5, SHELF_B - 5, 6.5, SHELF_B - 12, 1.3)
    # floor, rug and a ball of yarn
    img |= rect(1, FLOOR + 1, W - 2, FLOOR + 1)
    img |= (yy > FLOOR + 2) & (BAYER < 0.12)
    img |= ((xx - 54) / 4.5) ** 2 + ((yy - (FLOOR - 3.5)) / 3.5) ** 2 <= 1
    img &= ~((((xx - 54) / 4.5) ** 2 + ((yy - (FLOOR - 3.5)) / 3.5) ** 2 <= 0.75)
             & (((xx + yy) % 3) == 0))
    img |= thick_line(58, FLOOR - 1, 64, FLOOR, 1)
    return img


def frame(t):
    img = room(t)
    sp, fx, fy, face, ang = pose(t)
    on, dark = place(sp, fx, fy, face, ang)
    img &= ~dilate(on)
    img |= on
    img &= ~dark
    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
