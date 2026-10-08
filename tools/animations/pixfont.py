"""Tiny 3x5 pixel font for score counters and labels on the 68x140 screen."""
import numpy as np

FONT = {
    "0": ["XXX", "X.X", "X.X", "X.X", "XXX"], "1": [".X.", "XX.", ".X.", ".X.", "XXX"],
    "2": ["XXX", "..X", "XXX", "X..", "XXX"], "3": ["XXX", "..X", ".XX", "..X", "XXX"],
    "4": ["X.X", "X.X", "XXX", "..X", "..X"], "5": ["XXX", "X..", "XXX", "..X", "XXX"],
    "6": ["XXX", "X..", "XXX", "X.X", "XXX"], "7": ["XXX", "..X", ".X.", ".X.", ".X."],
    "8": ["XXX", "X.X", "XXX", "X.X", "XXX"], "9": ["XXX", "X.X", "XXX", "..X", "XXX"],
    "A": [".X.", "X.X", "XXX", "X.X", "X.X"], "B": ["XX.", "X.X", "XX.", "X.X", "XX."],
    "C": [".XX", "X..", "X..", "X..", ".XX"], "D": ["XX.", "X.X", "X.X", "X.X", "XX."],
    "E": ["XXX", "X..", "XX.", "X..", "XXX"], "F": ["XXX", "X..", "XX.", "X..", "X.."],
    "G": [".XX", "X..", "X.X", "X.X", ".XX"], "H": ["X.X", "X.X", "XXX", "X.X", "X.X"],
    "I": ["XXX", ".X.", ".X.", ".X.", "XXX"], "K": ["X.X", "X.X", "XX.", "X.X", "X.X"],
    "L": ["X..", "X..", "X..", "X..", "XXX"], "M": ["X.X", "XXX", "XXX", "X.X", "X.X"],
    "N": ["XX.", "X.X", "X.X", "X.X", "X.X"], "O": [".X.", "X.X", "X.X", "X.X", ".X."],
    "P": ["XX.", "X.X", "XX.", "X..", "X.."], "R": ["XX.", "X.X", "XX.", "X.X", "X.X"],
    "S": [".XX", "X..", ".X.", "..X", "XX."], "T": ["XXX", ".X.", ".X.", ".X.", ".X."],
    "U": ["X.X", "X.X", "X.X", "X.X", "XXX"], "V": ["X.X", "X.X", "X.X", "X.X", ".X."],
    "W": ["X.X", "X.X", "XXX", "XXX", "X.X"], "X": ["X.X", "X.X", ".X.", "X.X", "X.X"],
    "Y": ["X.X", "X.X", ".X.", ".X.", ".X."], "-": ["...", "...", "XXX", "...", "..."],
    "+": ["...", ".X.", "XXX", ".X.", "..."], "!": [".X.", ".X.", ".X.", "...", ".X."],
    " ": ["...", "...", "...", "...", "..."],
}


def text_mask(s, x, y, shape, scale=1):
    """Mask with the string drawn at (x, y) top-left; 1 px gap between letters."""
    H, W = shape
    m = np.zeros(shape, bool)
    cx = x
    for ch in s.upper():
        g = FONT.get(ch, FONT[" "])
        for j, row in enumerate(g):
            for i, c in enumerate(row):
                if c == "X":
                    for a in range(scale):
                        for b in range(scale):
                            X, Y = cx + i * scale + b, y + j * scale + a
                            if 0 <= X < W and 0 <= Y < H:
                                m[Y, X] = True
        cx += 4 * scale
    return m


def text_width(s, scale=1):
    return len(s) * 4 * scale - scale
