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
| `CONFIG_NICE_VIEW_GEM_ANIMATION`                | bool   | Animate the art. Set to `n` to show a still frame of a random slide instead.                                                                                     | y       |
| `CONFIG_NICE_VIEW_GEM_SLIDESHOW_INTERVAL_S`     | int    | Seconds each slideshow animation plays before a random different one takes over. The switch happens at the end of a loop, and only while the half is active.     | 300     |
| `CONFIG_NICE_VIEW_GEM_ANIMATION_SPEED_PCT`      | int    | Frame time as a percentage of each animation's own pacing. `200` plays everything at half speed and halves the redraws (less battery); `50` doubles the speed. | 100     |
| `CONFIG_NICE_VIEW_GEM_LAYER_ANIMATION_NAME`     | string | Name (`display-name`) of the layer that shows the spell animation on the left half while it is active anywhere in the layer stack. Empty disables it.           | "Tibia" |
| `CONFIG_NICE_VIEW_GEM_ANIMATION_PAUSE_ON_IDLE`  | bool   | Freeze the animation on its current frame when the half goes idle (`CONFIG_ZMK_IDLE_TIMEOUT`, 30 s by default) and resume on the next keypress.                 | y       |

## Animations

The 68x140 art area plays looping animations:

| Animation    | Where                                        | Frames | Pacing      |
| ------------ | -------------------------------------------- | ------ | ----------- |
| Campfire     | Slideshow, both halves                       | 32     | 150 ms      |
| Starry night | Slideshow, both halves                       | 32     | 250 ms      |
| Astronaut    | Slideshow, both halves                       | 36     | 200 ms      |
| Tree         | Slideshow, both halves                       | 48     | 400 ms      |
| Cat          | Slideshow, both halves                       | 44     | 140 ms      |
| Spells       | Left half, while the "Tibia" layer is active | 48     | 170 ms      |

Each half starts on a random slide and moves to a random different one every 5 minutes. Only the central half knows the active layers in a ZMK split, so the layer animation lives on the left.

Battery: one LVGL timer advances the frames and is paused as soon as the half goes idle, and the shield enables `CONFIG_ZMK_DISPLAY_BLANK_ON_IDLE` so ZMK also stops its display tick while idle. The nice!view keeps showing the last frame, so nothing visibly changes. The number of animations does not affect battery, only how often frames are drawn.

The frames are generated by the Python scripts in `tools/animations/` (numpy + Pillow); each `make_<name>.py` defines its frame count, pacing and drawing. After editing one, run `python3 tools/animations/build_all.py` to rewrite the `.c`/`.h` files in `boards/shields/nice_view_gem/assets/` and refresh the previews in `tools/animations/preview/`.

## Credits

Shoutout to Teenage Engineering for their [TX-6](https://teenage.engineering/products/tx-6), from which the inspiration (and maybe even a few pixel strokes) originated. 😬

As for the floating crystal, appreciation goes to the pixel wizardry of Trixelized, who graciously lent their art to this project. 💎

The font, Pixel Operator, is the work of Jayvee Enaguas, kindly shared under a [Creative Commons Zero (CC0) 1.0](https://creativecommons.org/publicdomain/zero/1.0/) license. 🖋️
