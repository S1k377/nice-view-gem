"""Ocean waves at sunset: rows of swells rolling in toward you, getting bigger as they
come closer, with foam on the crests, gulls, and the sun glittering on the water.
32 frames, seamless."""
import math
import numpy as np
from nvlib import W, H, xx, yy, BAYER, disc

N = 32
FRAME_MS = 160
TAU = 2 * math.pi
HORIZON = 52

# wave rows from far to near: (base y, amplitude, wavelength, crests travel this many
# wavelengths per loop, curl size)
ROWS = [(60, 1.5, 17, 1, 0), (68, 2.0, 22.67, 1, 0), (78, 3.0, 34, 1, 2),
        (91, 4.5, 34, 1, 3), (107, 6.0, 68, 2, 4.5), (126, 8.0, 68, 2, 6)]


def dilate(m):
    o = m.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def crest(x, t, base, amp, lam, cycles, row):
    """Height of the water surface: a steep, skewed wave so crests look like they lean."""
    ph = TAU * (x / lam - cycles * t / N) + row * 1.3
    return base - amp * (math.sin(ph) + 0.35 * math.sin(2 * ph - 0.9))


def frame(t):
    p = t / N
    img = np.zeros((H, W), bool)

    # sky: a big low sun with horizontal cloud stripes, a few gulls
    sun = disc(34, HORIZON + 2, 15) & (yy < HORIZON)
    img |= sun & ~((yy % 4 == 0) & (yy > HORIZON - 9))
    for cy, x0, x1 in ((22, 4, 30), (26, 10, 40), (30, 40, 64), (16, 44, 60)):
        img |= (yy == cy) & (xx >= x0 + 4 * math.sin(TAU * p)) & (xx <= x1 + 4 * math.sin(TAU * p)) & (BAYER < 0.6)
    for gx, gy, ph in ((16, 12, 0.0), (50, 8, 0.5)):
        x = gx + 6 * math.sin(TAU * p + ph)
        flap = 1 if math.sin(TAU * p * 4 + ph * 6) > 0 else 0
        for dx in (-2, -1, 1, 2):
            yv = gy - (abs(dx) == 2) * flap + (abs(dx) == 1) * (1 - flap) * 0
            if 0 < int(x + dx) < W - 1:
                img[int(yv), int(x + dx)] = True
        img[gy + 1, int(x)] = True

    # horizon line and sun glitter
    img[HORIZON, :] = True
    for y in range(HORIZON + 2, 70, 2):
        w = 3 + (y - HORIZON) * 0.6
        for k in range(3):
            x = 34 + (((k * 7 + y * 3 + t * 2) % 13) - 6) * w / 6
            if (y + k + t) % 3 == 0:
                img[y, int(np.clip(x, 1, W - 2))] = True

    # waves, back to front: each row hides what is behind it, then draws its foam
    for row, (base, amp, lam, cycles, curl) in enumerate(ROWS):
        surf = np.array([crest(x, t, base, amp, lam, cycles, row) for x in range(W)])
        water = yy >= surf[None, :]
        img &= ~water
        line = (yy >= surf[None, :]) & (yy < surf[None, :] + 1.2 + row * 0.25)
        img |= line
        # foam: dithered band just under each crest, densest at the peaks
        depth = yy - surf[None, :]
        peak = (base - surf)[None, :] / (amp + 1e-6)
        img |= water & (depth < 2 + row) & (BAYER < 0.15 + 0.35 * np.clip(peak, 0, 1))
        # texture lines in the trough
        img |= water & (np.abs(depth - (4 + row * 1.5)) < 0.5) & (((xx + t * cycles) % 6) < 3) & (row >= 2)
        # foam spray flicking off the tallest crests of the near rows
        if curl:
            xs = np.arange(-20, W + 20, 0.5)
            ys = np.array([crest(x, t, base, amp, lam, cycles, row) for x in xs])
            peaks = [i for i in range(1, len(xs) - 1) if ys[i] <= ys[i - 1] and ys[i] < ys[i + 1]]
            for i in peaks:
                cx, cy = xs[i], ys[i]
                img |= disc(cx + 1, cy + 0.5, curl * 0.5) & (yy >= cy - 1)
                for d in range(4):
                    sx, sy = int(cx + 2 + d * 1.6), int(cy - 1 - d * 0.7 + d * d * 0.25)
                    if 0 < sx < W - 1 and 0 < sy < H - 1 and (t + d) % 2 == 0:
                        img[sy, sx] = True

    img[0, :] = img[-1, :] = True
    img[:, 0] = img[:, -1] = True
    return img


if __name__ == "__main__":
    import build_all
    build_all.main()
