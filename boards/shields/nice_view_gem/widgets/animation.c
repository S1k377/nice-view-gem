#include <zephyr/kernel.h>

#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <zmk/display.h>
#include <zmk/event_manager.h>

#include "animation.h"

#define ANIM_IS_CENTRAL (!IS_ENABLED(CONFIG_ZMK_SPLIT) || IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL))

#if ANIM_IS_CENTRAL
#include <zmk/keymap.h>
#include <zmk/events/layer_state_changed.h>
#include "../assets/campfire.h"
#include "../assets/gaming.h"
#else
#include "../assets/night.h"
#endif

#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION_PAUSE_ON_IDLE)
#include <zmk/activity.h>
#include <zmk/events/activity_state_changed.h>
#endif

struct anim_set {
    const lv_img_dsc_t *const *frames;
    uint16_t count;
    uint16_t frame_ms;
};

#if ANIM_IS_CENTRAL
static const struct anim_set base_set = {
    .frames = campfire_imgs,
    .count = CAMPFIRE_FRAME_COUNT,
    .frame_ms = CONFIG_NICE_VIEW_GEM_ANIMATION_FRAME_MS,
};
static const struct anim_set layer_set = {
    .frames = gaming_imgs,
    .count = GAMING_FRAME_COUNT,
    .frame_ms = CONFIG_NICE_VIEW_GEM_ANIMATION_LAYER_FRAME_MS,
};
#else
static const struct anim_set base_set = {
    .frames = night_imgs,
    .count = NIGHT_FRAME_COUNT,
    .frame_ms = CONFIG_NICE_VIEW_GEM_ANIMATION_FRAME_MS,
};
#endif

static lv_obj_t *art;
static const struct anim_set *current;
static uint16_t frame;
#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION)
static lv_timer_t *timer;
#endif
static bool active = true;

static void show_frame(void) { lv_img_set_src(art, current->frames[frame]); }

#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION)
static void next_frame(lv_timer_t *t) {
    ARG_UNUSED(t);
    frame = (frame + 1) % current->count;
    show_frame();
}
#endif

/* Run the timer only while the half is active; it is the only thing that wakes the display. */
static void update_timer(void) {
#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION)
    if (timer == NULL) {
        return;
    }
    lv_timer_set_period(timer, current->frame_ms);
    if (active) {
        lv_timer_reset(timer);
        lv_timer_resume(timer);
    } else {
        lv_timer_pause(timer);
    }
#endif
}

#if ANIM_IS_CENTRAL
static void select_set(const struct anim_set *set) {
    if (set == current) {
        return;
    }
    current = set;
    frame = 0;
    show_frame();
    update_timer();
}

/**
 * Layer: swap image sets only when the highest active layer crosses 0 <-> non-zero
 **/

struct anim_layer_state {
    uint8_t layer;
};

static void anim_layer_update_cb(struct anim_layer_state state) {
    select_set(state.layer == 0 ? &base_set : &layer_set);
}

static struct anim_layer_state anim_layer_get_state(const zmk_event_t *eh) {
    ARG_UNUSED(eh);
    return (struct anim_layer_state){.layer = zmk_keymap_highest_layer_active()};
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_anim_layer, struct anim_layer_state, anim_layer_update_cb,
                            anim_layer_get_state)
ZMK_SUBSCRIPTION(widget_anim_layer, zmk_layer_state_changed);
#endif /* ANIM_IS_CENTRAL */

#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION_PAUSE_ON_IDLE)
/**
 * Activity: freeze on the current frame when idle/asleep, resume on the next keypress
 **/

struct anim_activity_state {
    bool active;
};

static void anim_activity_update_cb(struct anim_activity_state state) {
    if (state.active == active) {
        return;
    }
    active = state.active;
    update_timer();
}

static struct anim_activity_state anim_activity_get_state(const zmk_event_t *eh) {
    const struct zmk_activity_state_changed *ev = as_zmk_activity_state_changed(eh);
    enum zmk_activity_state s = (ev != NULL) ? ev->state : zmk_activity_get_state();
    return (struct anim_activity_state){.active = (s == ZMK_ACTIVITY_ACTIVE)};
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_anim_activity, struct anim_activity_state,
                            anim_activity_update_cb, anim_activity_get_state)
ZMK_SUBSCRIPTION(widget_anim_activity, zmk_activity_state_changed);
#endif /* CONFIG_NICE_VIEW_GEM_ANIMATION_PAUSE_ON_IDLE */

void draw_animation(lv_obj_t *parent) {
    art = lv_img_create(parent);
    lv_obj_align(art, LV_ALIGN_TOP_LEFT, 0, 0);

    current = &base_set;
    frame = 0;
    show_frame();

#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION)
    timer = lv_timer_create(next_frame, current->frame_ms, NULL);
#endif

#if ANIM_IS_CENTRAL
    widget_anim_layer_init();
#endif
#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION_PAUSE_ON_IDLE)
    widget_anim_activity_init();
#endif
}
