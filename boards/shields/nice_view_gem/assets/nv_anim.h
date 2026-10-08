#pragma once

#include <stdint.h>

/*
 * Compressed 1-bit animations for the 68x140 art area.
 *
 * Pixels are stored rotated (140 wide x 68 tall, 18 bytes per row, MSB first), exactly as an
 * LV_IMG_CF_INDEXED_1BIT image without its palette; background bits are 1.
 *
 * Frame 0 is run-length encoded; every later frame is the run-length encoded XOR against the
 * frame before it, so frames must be decoded in order (0, 1, 2, ..., then 0 again).
 * Codes: 0x00-0x7F = copy the next (c + 1) bytes, 0x80-0xFF = repeat the next byte
 * (c - 0x80 + 2) times.
 */

#define NV_ANIM_WIDTH 140
#define NV_ANIM_HEIGHT 68
#define NV_ANIM_STRIDE 18
#define NV_ANIM_BYTES (NV_ANIM_STRIDE * NV_ANIM_HEIGHT)

struct nv_anim {
    uint16_t count;
    uint16_t frame_ms;
    const uint8_t *data;
    const uint32_t *offsets; /* count + 1 entries */
};

/*
 * Turns `bits` (NV_ANIM_BYTES) into frame `frame`. For frame 0 the old contents don't matter;
 * for any other frame `bits` must hold frame `frame - 1`.
 */
void nv_anim_decode(const struct nv_anim *anim, uint16_t frame, uint8_t *bits);
