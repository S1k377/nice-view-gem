#pragma once

#include <lvgl.h>
#include "util.h"
#include "screen.h"

/*
 * Draws the 68x140 art area (top-left of the screen object, on top of the status canvas).
 *
 * Both halves: a random slideshow (campfire, starry night, astronaut, tree, cat), switching
 * every CONFIG_NICE_VIEW_GEM_SLIDESHOW_INTERVAL_S seconds at the end of a loop.
 * Left (central) half: the gaming animation while the layer named
 * CONFIG_NICE_VIEW_GEM_LAYER_ANIMATION_NAME is active.
 *
 * Battery: frames advance from a single LVGL timer that is paused whenever the
 * keyboard half goes idle, so nothing redraws while you are not typing.
 */
void draw_animation(lv_obj_t *parent);
