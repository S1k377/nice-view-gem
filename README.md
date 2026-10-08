# nice-view-gem

![Preview](https://github.com/m165437/nice-view-gem/blob/main/.github/assets/preview.jpg?raw=true)

### A sleek customization for the nice!view shield

Add this shield to your keymap repo (see usage below) and run the GitHub action to build your firmware.

### Features

- Uses a **fixed range for the chart and gauge deflection**. 📈
- Includes a **beautiful animation** for the peripheral of split keyboards. 💎
- Comes with **pixel-perfect symbols** for BLE and USB connections. 📡

## Usage

To use this shield, first add it to your `config/west.yml` by adding a new entry to remotes and projects:

```yml
manifest:
  remotes:
    - name: zmkfirmware
      url-base: https://github.com/zmkfirmware
    - name: m165437 #new entry
      url-base: https://github.com/M165437 #new entry
  projects:
    - name: zmk
      remote: zmkfirmware
      revision: main
      import: app/west.yml
    - name: nice-view-gem #new entry
      remote: m165437 #new entry
      revision: main #new entry
  self:
    path: config
```

Now, simply swap out the default nice_view shield on the board for nice_view_gem in your `build.yaml` file.

```yml
---
include:
  - board: nice_nano_v2
    shield: kyria_left nice_view_adapter nice_view_gem #updated entry
  - board: nice_nano_v2
    shield: kyria_right nice_view_adapter nice_view_gem #updated entry
```

Finally, make sure to enable the custom status screen in your ZMK configuration:

```conf
CONFIG_ZMK_DISPLAY=y
CONFIG_ZMK_DISPLAY_STATUS_SCREEN_CUSTOM=y
```

## Configuration

Modify the behavior of this shield by adjusting these options in your personal configuration files. For a more detailed explanation, refer to [Configuration in the ZMK documentation](https://zmk.dev/docs/config).

| Option                                     | Type | Description                                                                                                                                                                                                                                                       | Default |
| ------------------------------------------ | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `CONFIG_NICE_VIEW_GEM_WPM_FIXED_RANGE`     | bool | This shield uses a fixed range for the chart and gauge deflection. If you set this option to `n`, it will switch to a dynamic range, like the default nice!view shield, which dynamically adjusts based on the last 10 WPM values provided by ZMK.                | y       |
| `CONFIG_NICE_VIEW_GEM_WPM_FIXED_RANGE_MAX` | int  | You can adjust the maximum value of the fixed range to align with your current goal.                                                                                                                                                                              | 100     |
| `CONFIG_NICE_VIEW_GEM_ANIMATION`                   | bool | Animate the art. Set to `n` to show a still frame instead (the set still switches with the layer on the left half).                                                                                                                                           | y       |
| `CONFIG_NICE_VIEW_GEM_ANIMATION_FRAME_MS`            | int  | Milliseconds per frame for the campfire (left half, layer 0). Higher is slower and uses less battery.                                                                                                                                                         | 150     |
| `CONFIG_NICE_VIEW_GEM_ANIMATION_PERIPHERAL_FRAME_MS` | int  | Milliseconds per frame for the starry night on the right half.                                                                                                                                                                                                | 250     |
| `CONFIG_NICE_VIEW_GEM_ANIMATION_LAYER_FRAME_MS`    | int  | Milliseconds per frame for the spell animation shown on the left half when any layer other than 0 is active.                                                                                                                                                  | 170     |
| `CONFIG_NICE_VIEW_GEM_ANIMATION_PAUSE_ON_IDLE`     | bool | Freeze the animation on its current frame when the half goes idle (`CONFIG_ZMK_IDLE_TIMEOUT`, 30 s by default) and resume on the next keypress. Keeps the display from redrawing while you are away.                                                         | y       |

## Animations

The 68x140 art area plays a looping animation:

| Half          | Layer 0          | Any other layer                       |
| ------------- | ---------------- | ------------------------------------- |
| Left (central)  | Campfire         | Spells: fireball → lightning → thorns |
| Right (peripheral) | Starry night | Starry night                          |

Only the central half knows the active layer in a ZMK split, so the layer-dependent animation lives on the left. Each half only links the frames it shows.

The frames are generated by the Python scripts in `tools/animations/` (numpy + Pillow). After editing one, run `python3 tools/animations/build_all.py` to rewrite `boards/shields/nice_view_gem/assets/{campfire,gaming,night}.{c,h}` and refresh the previews in `tools/animations/preview/`.

## Credits

Shoutout to Teenage Engineering for their [TX-6](https://teenage.engineering/products/tx-6), from which the inspiration (and maybe even a few pixel strokes) originated. 😬

As for the floating crystal, appreciation goes to the pixel wizardry of Trixelized, who graciously lent their art to this project. 💎

The font, Pixel Operator, is the work of Jayvee Enaguas, kindly shared under a [Creative Commons Zero (CC0) 1.0](https://creativecommons.org/publicdomain/zero/1.0/) license. 🖋️
