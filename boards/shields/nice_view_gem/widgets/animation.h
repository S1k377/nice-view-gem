#pragma once

#include <lvgl.h>
#include "util.h"
#include "screen.h"

/*
 * Draws the 68x140 art area (top-left of the screen object, on top of the status canvas).
 *
 * Central (left) half: campfire on layer 0, spell sequence on any other layer.
 * Peripheral (right) half: starry night.
 *
 * Battery: frames advance from a single LVGL timer that is paused whenever the
 * keyboard half goes idle, so nothing redraws while you are not typing.
 */
void draw_animation(lv_obj_t *parent);
