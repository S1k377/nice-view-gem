"""Shared helpers for nice!view slideshow frames (68x140 portrait, 1-bit).

Frames are numpy bool arrays shaped (140, 68), True = white pixel.

Each animation is exported as <name>.c/.h holding one `struct nv_anim` (see
assets/nv_anim.h). Frames are stored rotated 90deg CW as 140x68 1-bit rows of 18 bytes
(the same pixel layout as the original hammerbeam art), with background bits = 1.
To keep the firmware small, frame 0 is stored run-length encoded and every later frame
as the run-length encoded XOR against the frame before it; the firmware rebuilds each
frame into one RAM buffer as it plays them in order.
"""
import os
import numpy as np
from PIL import Image

W, H = 68, 140
yy, xx = np.mgrid[0:H, 0:W]
_B = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
BAYER = np.tile(_B, (H // 4 + 1, W // 4 + 1))[:H, :W]


def disc(cx, cy, r):
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r


def rect(x0, y0, x1, y1):
    return (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)


def thick_line(x0, y0, x1, y1, w):
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy or 1
    t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / L2, 0, 1)
    px, py = x0 + t * dx, y0 + t * dy
    return (xx - px) ** 2 + (yy - py) ** 2 <= (w / 2) ** 2


def sprite(rows, x, y):
    """Stamp an ASCII sprite: 'X' = white, 'o' = force black, '.' = transparent."""
    on = np.zeros((H, W), bool)
    off = np.zeros((H, W), bool)
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            X, Y = x + i, y + j
            if 0 <= X < W and 0 <= Y < H:
                if c == "X":
                    on[Y, X] = True
                elif c == "o":
                    off[Y, X] = True
    return on, off


STRIDE = 18                      # bytes per stored row (140 px rounded up to 144)
FRAME_BYTES = STRIDE * W         # 68 stored rows -> 1224 bytes


def stored_bytes(f):
    """Portrait frame -> the 1224 bytes the firmware draws. Background = 1, as in the
    original hammerbeam art: palette index 1 is the background colour (black by default
    on this shield's setup, swapped by CONFIG_NICE_VIEW_WIDGET_INVERTED)."""
    st = np.rot90(~f, k=-1)                          # (68, 140)
    st = np.pad(st, ((0, 0), (0, STRIDE * 8 - st.shape[1])))
    return np.packbits(st.astype(np.uint8), axis=1).ravel()


def rle(data):
    """0x00-0x7F: copy the next (c+1) bytes.  0x80-0xFF: repeat the next byte (c-0x80+2) times."""
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        j = i
        while j < n and j - i < 129 and data[j] == data[i]:
            j += 1
        if j - i >= 2:
            out += bytes([0x80 + (j - i - 2), int(data[i])])
            i = j
            continue
        j = i + 1
        while j < n and j - i < 128 and not (j + 1 < n and data[j] == data[j + 1]):
            j += 1
        out += bytes([j - i - 1]) + bytes(int(x) for x in data[i:j])
        i = j
    return bytes(out)


def unrle(blob, prev=None):
    """Reference decoder (mirrors nv_anim.c); used to self-check every export."""
    out = np.zeros(FRAME_BYTES, np.uint8) if prev is None else prev.copy()
    i = p = 0
    while p < len(blob):
        c = blob[p]; p += 1
        if c & 0x80:
            n, v = (c & 0x7F) + 2, blob[p]; p += 1
            seg = np.full(n, v, np.uint8)
        else:
            n = c + 1
            seg = np.frombuffer(blob[p:p + n], np.uint8); p += n
        out[i:i + n] = seg if prev is None else out[i:i + n] ^ seg
        i += n
    assert i == FRAME_BYTES
    return out


def encode(frames):
    raw = [stored_bytes(f) for f in frames]
    blobs = [rle(raw[0])] + [rle(raw[k] ^ raw[k - 1]) for k in range(1, len(raw))]
    cur = None
    for k, b in enumerate(blobs):                    # verify round trip, in playing order
        cur = unrle(b) if k == 0 else unrle(b, cur)
        assert np.array_equal(cur, raw[k]), f"frame {k} does not round-trip"
    return blobs


def export(name, frames, c_dir, preview_dir, preview_ms=150):
    """Write <name>.c/.h into c_dir and PNG frames, a GIF preview and a contact sheet into preview_dir."""
    os.makedirs(os.path.join(preview_dir, "frames", name), exist_ok=True)
    big = []
    for i, f in enumerate(frames, 1):
        im = Image.fromarray(np.where(f, 255, 0).astype(np.uint8))
        im.convert("1").save(os.path.join(preview_dir, "frames", name, f"{name}_{i:02d}.png"))
        big.append(im.resize((W * 4, H * 4), Image.NEAREST))
    big[0].save(os.path.join(preview_dir, f"{name}_preview.gif"), save_all=True,
                append_images=big[1:], duration=preview_ms, loop=0)
    cols = 10
    rws = (len(frames) + cols - 1) // cols
    sheet = Image.new("L", (cols * (W + 4), rws * (H + 4)), 128)
    for i, f in enumerate(frames):
        sheet.paste(Image.fromarray(np.where(f, 255, 0).astype(np.uint8)),
                    ((i % cols) * (W + 4), (i // cols) * (H + 4)))
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(
        os.path.join(preview_dir, f"{name}_sheet.png"))

    n = len(frames)
    up = name.upper()
    blobs = encode(frames)
    data = b"".join(blobs)
    offs = [0]
    for b in blobs:
        offs.append(offs[-1] + len(b))
    c = ["/*",
         f" * {name}: {n} frames, 68x140 portrait. {len(data)} bytes compressed",
         f" * ({n * (FRAME_BYTES + 8)} bytes as plain images). Format: see nv_anim.h.",
         " * Generated by tools/animations - edit the generator, not this file.",
         " */", "",
         f'#include "{name}.h"', "",
         f"static const uint8_t {name}_data[{len(data)}] = {{"]
    for k in range(0, len(data), 18):
        c.append("    " + ", ".join(f"0x{x:02x}" for x in data[k:k + 18]) + ",")
    c += ["};", "",
          f"static const uint32_t {name}_offsets[{n + 1}] = {{"]
    for k in range(0, n + 1, 8):
        c.append("    " + ", ".join(str(o) for o in offs[k:k + 8]) + ",")
    c += ["};", "",
          f"const struct nv_anim {name}_anim = {{",
          f"    .count = {up}_FRAME_COUNT,",
          f"    .frame_ms = {up}_FRAME_MS,",
          f"    .data = {name}_data,",
          f"    .offsets = {name}_offsets,",
          "};"]
    with open(os.path.join(c_dir, f"{name}.c"), "w") as fh:
        fh.write("\n".join(c) + "\n")
    with open(os.path.join(c_dir, f"{name}.h"), "w") as fh:
        fh.write(f'#pragma once\n\n#include "nv_anim.h"\n\n#define {up}_FRAME_COUNT {n}\n'
                 f"#define {up}_FRAME_MS {preview_ms}\n\n"
                 f"extern const struct nv_anim {name}_anim;\n")
    return len(data)
