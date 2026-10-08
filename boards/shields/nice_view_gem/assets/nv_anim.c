#include <string.h>

#include "nv_anim.h"

void nv_anim_decode(const struct nv_anim *anim, uint16_t frame, uint8_t *bits) {
    const uint8_t *p = anim->data + anim->offsets[frame];
    const uint8_t *end = anim->data + anim->offsets[frame + 1];
    const int key = (frame == 0);
    uint32_t i = 0;

    while (p < end && i < NV_ANIM_BYTES) {
        uint8_t c = *p++;
        uint32_t n;

        if (c & 0x80) {
            /* a run of one repeated byte */
            n = (uint32_t)(c & 0x7F) + 2;
            if (p >= end) {
                break;
            }
            uint8_t v = *p++;
            if (n > NV_ANIM_BYTES - i) {
                n = NV_ANIM_BYTES - i;
            }
            if (key) {
                memset(bits + i, v, n);
            } else if (v != 0) {
                for (uint32_t k = 0; k < n; k++) {
                    bits[i + k] ^= v;
                }
            }
        } else {
            /* literal bytes */
            n = (uint32_t)c + 1;
            if (n > (uint32_t)(end - p)) {
                n = (uint32_t)(end - p);
            }
            if (n > NV_ANIM_BYTES - i) {
                n = NV_ANIM_BYTES - i;
            }
            if (key) {
                memcpy(bits + i, p, n);
            } else {
                for (uint32_t k = 0; k < n; k++) {
                    bits[i + k] ^= p[k];
                }
            }
            p += n;
        }
        i += n;
    }
}
