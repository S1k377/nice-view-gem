"""Regenerate every nice!view animation.

    python3 tools/animations/build_all.py

Writes the firmware sources into boards/shields/nice_view_gem/assets/ and previews
(GIFs, contact sheets, PNG frames) into tools/animations/preview/.
Requires: Python 3, numpy, Pillow.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import make_campfire, make_gaming, make_night  # noqa: E402
from nvlib import export  # noqa: E402

ASSETS = os.path.normpath(os.path.join(HERE, "..", "..", "boards", "shields", "nice_view_gem", "assets"))
PREVIEW = os.path.join(HERE, "preview")

# name, module, preview frame delay (ms)
ANIMATIONS = [
    ("campfire", make_campfire, 150),   # left half, base layer
    ("gaming", make_gaming, 110),       # left half, any other layer
    ("night", make_night, 150),         # right half
]


def main():
    for name, mod, ms in ANIMATIONS:
        export(name, [mod.frame(t) for t in range(mod.N)], ASSETS, PREVIEW, ms)
        print(f"{name}: {mod.N} frames")


if __name__ == "__main__":
    main()
