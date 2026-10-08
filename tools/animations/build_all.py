"""Regenerate every nice!view animation.

    python3 tools/animations/build_all.py

Writes the firmware sources into boards/shields/nice_view_gem/assets/ and previews
(GIFs, contact sheets, PNG frames) into tools/animations/preview/.
Each make_<name>.py defines N (frame count), FRAME_MS (pacing) and frame(t).
Requires: Python 3, numpy, Pillow.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import make_astronaut, make_campfire, make_cat, make_gaming, make_night, make_tree  # noqa: E402
from nvlib import export  # noqa: E402

ASSETS = os.path.normpath(os.path.join(HERE, "..", "..", "boards", "shields", "nice_view_gem", "assets"))
PREVIEW = os.path.join(HERE, "preview")

ANIMATIONS = [
    ("campfire", make_campfire),     # slideshow
    ("night", make_night),           # slideshow
    ("astronaut", make_astronaut),   # slideshow
    ("tree", make_tree),             # slideshow
    ("cat", make_cat),               # slideshow
    ("gaming", make_gaming),         # left half, while the "Tibia" layer is active
]


def main():
    for name, mod in ANIMATIONS:
        export(name, [mod.frame(t) for t in range(mod.N)], ASSETS, PREVIEW, mod.FRAME_MS)
        print(f"{name}: {mod.N} frames @ {mod.FRAME_MS} ms")


if __name__ == "__main__":
    main()
