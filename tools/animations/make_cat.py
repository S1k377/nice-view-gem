"""A chonky cat hopping up from side to side: it sits on a little ledge, wiggles, crouches
and leaps to the next ledge up on the other side, turns around and does it again, while the
view scrolls upward so the climb never ends. 44 frames (4 hops), seamless."""
import math, os, random
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc, export

N = 44
FRAME_MS = 120
TAU = 2 * math.pi
C = 11                     # frames per hop
D = 34                     # vertical distance between ledges
Y0 = 97                    # screen y of the cat's feet when it lands
LEFT_X, RIGHT_X = 19, 49   # where the cat sits on each side

rng = random.Random(8)
DUST = [(rng.randrange(3, W - 3), rng.randrange(0, 2 * D)) for _ in range(9)]


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def erode(m):
    return ~dilate(~m)


class Cat:
    """Pixel coordinates in the cat's frame: origin at its feet, -y up, facing +x."""

    def __init__(self, fx, fy, face, ang=0.0, k=1.12):
        c, s = math.cos(ang), math.sin(ang)
        dx, dy = (xx - fx) * face / k, (yy - fy) / k
        self.x = c * dx + s * dy
        self.y = -s * dx + c * dy

    def ell(self, x, y, rx, ry):
        return ((self.x - x) / rx) ** 2 + ((self.y - y) / ry) ** 2 <= 1

    def line(self, x0, y0, x1, y1, w):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy or 1
        t = np.clip(((self.x - x0) * dx + (self.y - y0) * dy) / L2, 0, 1)
        return (self.x - x0 - t * dx) ** 2 + (self.y - y0 - t * dy) ** 2 <= (w / 2) ** 2

    def tri(self, ax, ay, bx, by, cx, cy):
        def side(px, py, qx, qy):
            return (self.x - qx) * (py - qy) - (px - qx) * (self.y - qy)
        d1, d2, d3 = side(ax, ay, bx, by), side(bx, by, cx, cy), side(cx, cy, ax, ay)
        return ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))


def draw_cat(img, fx, fy, face, pose, k, ang=0.0):
    """pose: 'sit', 'crouch', 'jump' or 'land'; k = small per-frame wiggle/blink phase."""
    c = Cat(fx, fy, face, ang)
    dark = np.zeros((H, W), bool)
    blink = pose == "sit" and k == 2
    if pose == "sit":
        body = c.ell(-1, -8.5, 10.5, 9) | c.ell(-1, -4.5, 11.5, 5)
        hx, hy = 4.5, -17.5 - 0.5 * (k % 2)
        sw = 2.5 * math.sin(k * 1.6)
        tail = (c.line(-10, -3, -13, -9 + sw, 3.4) | c.line(-13, -9 + sw, -11, -16 + sw, 3.0))
        paws = c.ell(3, -1, 2.6, 1.6) | c.ell(7.5, -1, 2.6, 1.6)
    elif pose in ("crouch", "land"):
        body = c.ell(-1, -6, 11.5, 6.5) | c.ell(-1, -3.5, 12, 4)
        hx, hy = 7.5, -11
        tail = c.line(-11, -5, -13, -10, 3.4) | c.line(-13, -10, -13, -15, 3.0)
        paws = c.ell(7, -1, 2.8, 1.5) | c.ell(11, -1, 2.8, 1.5) | c.ell(-8, -1, 3, 1.6)
        if pose == "land":
            paws |= c.ell(13, -1.5, 2.8, 1.6)
    else:  # jump: stretched out, front paws reaching, back legs kicked out
        body = c.ell(0, -7, 13, 7.2)
        hx, hy = 12, -10
        tail = c.line(-12, -8, -18, -12, 3.2) | c.line(-18, -12, -22, -11, 2.8)
        paws = c.line(9, -4, 17, -2, 3.4) | c.line(-9, -4, -16, 0, 3.6)
    head = c.ell(hx, hy, 7.2, 6.2)
    ears = (c.tri(hx - 5.5, hy - 3, hx - 1.5, hy - 4.5, hx - 4.5, hy - 9.5) |
            c.tri(hx + 1.5, hy - 4.5, hx + 5.5, hy - 3, hx + 4.5, hy - 9.5))
    cat = body | head | ears | tail | paws

    # face: eyes (or a blink), a tiny nose, inner ears; a seam where tail and paws cross
    if blink:
        dark |= (c.ell(hx - 1.5, hy, 1.4, 0.5) | c.ell(hx + 3.5, hy, 1.4, 0.5))
    else:
        dark |= c.ell(hx - 1.5, hy - 0.3, 0.9, 1.3) | c.ell(hx + 3.5, hy - 0.3, 0.9, 1.3)
    dark |= c.ell(hx + 1, hy + 2.2, 0.8, 0.5)
    dark |= (c.tri(hx - 4.5, hy - 4.5, hx - 2.5, hy - 5.2, hx - 4.0, hy - 7.6) |
             c.tri(hx + 2.5, hy - 5.2, hx + 4.5, hy - 4.5, hx + 4.0, hy - 7.6))
    dark |= dilate(tail) & body & ~tail
    dark |= dilate(head) & body & ~head & (c.y < hy + 4)
    dark |= dilate(paws) & body & ~paws

    img &= ~dilate(cat)
    img |= cat
    img &= ~dark


def ledge(img, side, y):
    """A short rounded plank sticking out of the wall."""
    x0, x1 = (1, 31) if side == 0 else (37, 66)
    y = int(round(y))
    if y + 4 < 0 or y > H:
        return
    plank = (xx >= x0) & (xx <= x1) & (yy >= y) & (yy <= y + 3)
    plank &= ~(((xx == x1) | (xx == x0)) & ((yy == y) | (yy == y + 3)) & (xx != 1) & (xx != 66))
    img &= ~dilate(plank)
    img |= plank
    img &= ~((yy == y + 2) & (xx > x0 + 1) & (xx < x1 - 1) & ((xx % 7) != 3))   # wood grain


def frame(t):
    img = np.zeros((H, W), bool)
    cam = D * t / C                                    # the view rises one ledge per hop

    for x, y in DUST:                                  # far-away specks, slower (parallax)
        for rep in range(-1, H // (2 * D) + 2):
            sy = int((y + cam / 2) % (2 * D) + rep * 2 * D)
            if 1 <= sy < H - 1:
                img[sy, x] = True

    hop = t // C
    f = t % C
    for i in range(hop - 2, hop + 6):                  # ledges in view
        ledge(img, i % 2, Y0 + 1 - D * i + cam)

    side = hop % 2                                     # 0 = sitting on the left ledge
    face = 1 if side == 0 else -1
    x0 = LEFT_X if side == 0 else RIGHT_X
    x1 = RIGHT_X if side == 0 else LEFT_X
    feet = Y0 - D * hop + cam
    if f == 0:
        draw_cat(img, x0, feet, face, "land", 0)
    elif f <= 4:
        draw_cat(img, x0, feet, face, "sit", f - 1 + 2 * (hop % 2))
    elif f <= 6:
        draw_cat(img, x0, feet, face, "crouch", 0)
    else:
        q = (f - 6) / 5
        x = x0 + (x1 - x0) * q
        y = feet - D * q - 14 * 4 * q * (1 - q)
        vy = -D - 14 * 4 * (1 - 2 * q)
        ang = max(-0.6, min(0.5, math.atan2(vy, abs(x1 - x0)) * 0.8))
        draw_cat(img, x, y, face, "jump", 0, ang)

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
