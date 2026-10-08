#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/random/random.h>

#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <zmk/display.h>
#include <zmk/event_manager.h>

#include "animation.h"
#include "../assets/astronaut.h"
#include "../assets/campfire.h"
#include "../assets/cat.h"
#include "../assets/night.h"
#include "../assets/waterfall.h"
#include "../assets/waves.h"

#define ANIM_IS_CENTRAL (!IS_ENABLED(CONFIG_ZMK_SPLIT) || IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL))

#if ANIM_IS_CENTRAL
#include <zmk/keymap.h>
#include <zmk/events/layer_state_changed.h>
#include "../assets/gaming.h"
#endif

#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION_PAUSE_ON_IDLE)
#include <zmk/activity.h>
#include <zmk/events/activity_state_changed.h>
#endif

/* The random slideshow, on both halves. */
static const struct nv_anim *const slides[] = {
    &campfire_anim, &night_anim, &astronaut_anim, &cat_anim, &waves_anim, &waterfall_anim,
};

#if ANIM_IS_CENTRAL
/* Shown instead of the slideshow while the layer named
 * CONFIG_NICE_VIEW_GEM_LAYER_ANIMATION_NAME is active (left half only). */
static const struct nv_anim *const layer_set = &gaming_anim;
#endif

/*
 * Frames are stored compressed in flash and rebuilt one at a time into this buffer:
 * an 8-byte palette followed by the 1-bit pixels, which LVGL draws as a normal image.
 * Palette index 1 is the background, matching the original hammerbeam art.
 */
static uint8_t art_buf[8 + NV_ANIM_BYTES] __aligned(4);
static const lv_img_dsc_t art_dsc = {
    .header.cf = LV_IMG_CF_INDEXED_1BIT,
    .header.always_zero = 0,
    .header.reserved = 0,
    .header.w = NV_ANIM_WIDTH,
    .header.h = NV_ANIM_HEIGHT,
    .data_size = sizeof(art_buf),
    .data = art_buf,
};

static lv_obj_t *art;
static const struct nv_anim *current;
static uint8_t slide;
static uint16_t frame;
static int64_t slide_started_ms;
static bool active = true;
#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION)
static lv_timer_t *timer;
#endif

static uint32_t frame_period(const struct nv_anim *set) {
    return MAX(20u, (uint32_t)set->frame_ms * CONFIG_NICE_VIEW_GEM_ANIMATION_SPEED_PCT / 100u);
}

/* Frames must be shown in order (0, 1, 2, ...) since each is stored as a change to the last. */
static void show_frame(void) {
    nv_anim_decode(current, frame, art_buf + 8);
    lv_obj_invalidate(art);
}

/* Run the timer only while the half is active; it is the only thing that redraws the art. */
static void update_timer(void) {
#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION)
    if (timer == NULL) {
        return;
    }
    lv_timer_set_period(timer, frame_period(current));
    if (active) {
        lv_timer_reset(timer);
        lv_timer_resume(timer);
    } else {
        lv_timer_pause(timer);
    }
#endif
}

static void select_set(const struct nv_anim *set) {
    if (set == current) {
        return;
    }
    current = set;
    frame = 0;
    show_frame();
    update_timer();
}

static void next_slide(void) {
    if (ARRAY_SIZE(slides) > 1) {
        /* any slide except the one just shown */
        slide = (slide + 1 + sys_rand32_get() % (ARRAY_SIZE(slides) - 1)) % ARRAY_SIZE(slides);
    }
    slide_started_ms = k_uptime_get();
    select_set(slides[slide]);
}

#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION)
static void next_frame(lv_timer_t *t) {
    ARG_UNUSED(t);
    frame = (frame + 1) % current->count;
    /* Change slides only at the end of a loop, once the interval has passed. */
    if (frame == 0 && current == slides[slide] &&
        k_uptime_get() - slide_started_ms >= (int64_t)CONFIG_NICE_VIEW_GEM_SLIDESHOW_INTERVAL_S * 1000) {
        next_slide();
        return;
    }
    show_frame();
}
#endif

#if ANIM_IS_CENTRAL
/**
 * Layer: show the layer animation while the named layer is active anywhere in the stack
 **/

static bool name_matches(const char *a, const char *b) {
    if (a == NULL || b == NULL || *b == '\0') {
        return false;
    }
    for (; *a && *b; a++, b++) {
        char ca = (*a >= 'A' && *a <= 'Z') ? *a + 32 : *a;
        char cb = (*b >= 'A' && *b <= 'Z') ? *b + 32 : *b;
        if (ca != cb) {
            return false;
        }
    }
    return *a == *b;
}

struct anim_layer_state {
    bool layer_anim;
};

static void anim_layer_update_cb(struct anim_layer_state state) {
    select_set(state.layer_anim ? layer_set : slides[slide]);
}

static struct anim_layer_state anim_layer_get_state(const zmk_event_t *eh) {
    ARG_UNUSED(eh);
    bool found = false;
    for (zmk_keymap_layer_id_t id = 0; id < ZMK_KEYMAP_LAYERS_LEN && !found; id++) {
        found = zmk_keymap_layer_active(id) &&
                name_matches(zmk_keymap_layer_name(id), CONFIG_NICE_VIEW_GEM_LAYER_ANIMATION_NAME);
    }
    return (struct anim_layer_state){.layer_anim = found};
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
    /* eh is NULL on the initial refresh; as_zmk_*() must not be called with NULL. */
    const struct zmk_activity_state_changed *ev =
        (eh != NULL) ? as_zmk_activity_state_changed(eh) : NULL;
    enum zmk_activity_state s = (ev != NULL) ? ev->state : zmk_activity_get_state();
    return (struct anim_activity_state){.active = (s == ZMK_ACTIVITY_ACTIVE)};
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_anim_activity, struct anim_activity_state,
                            anim_activity_update_cb, anim_activity_get_state)
ZMK_SUBSCRIPTION(widget_anim_activity, zmk_activity_state_changed);
#endif /* CONFIG_NICE_VIEW_GEM_ANIMATION_PAUSE_ON_IDLE */

void draw_animation(lv_obj_t *parent) {
    static const uint8_t palette[8] = {
#if IS_ENABLED(CONFIG_NICE_VIEW_WIDGET_INVERTED)
        0xff, 0xff, 0xff, 0xff, /* index 0 */
        0x00, 0x00, 0x00, 0xff, /* index 1 */
#else
        0x00, 0x00, 0x00, 0xff, /* index 0 */
        0xff, 0xff, 0xff, 0xff, /* index 1 */
#endif
    };
    memcpy(art_buf, palette, sizeof(palette));

    art = lv_img_create(parent);
    lv_obj_align(art, LV_ALIGN_TOP_LEFT, 0, 0);

    /* Start on a random slide (each half picks its own). */
    slide = sys_rand32_get() % ARRAY_SIZE(slides);
    slide_started_ms = k_uptime_get();
    current = slides[slide];
    frame = 0;
    show_frame();
    lv_img_set_src(art, &art_dsc);

#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION)
    timer = lv_timer_create(next_frame, frame_period(current), NULL);
#endif

#if ANIM_IS_CENTRAL
    widget_anim_layer_init();
#endif
#if IS_ENABLED(CONFIG_NICE_VIEW_GEM_ANIMATION_PAUSE_ON_IDLE)
    widget_anim_activity_init();
#endif
}
