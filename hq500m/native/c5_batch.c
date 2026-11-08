/* HQ500M Fusion R05: exact original C5 32-synapse batch generator.
 * No Python C API, malloc, threads, GPU driver or runtime allocation.
 * Stable ABI: uint32 IDs, signed raw weights (multiply by 0.000035 in Python).
 * License: same as the parent HQ500M project.
 */
#include <stddef.h>
#include <stdint.h>

#define HQ_TOTAL UINT32_C(500000000)
#define HQ_MODULE UINT32_C(1024)
#define HQ_SEED UINT64_C(37421)
#define HQ_K UINT64_C(0x517cc1b727220a95)

static const uint32_t bounds[8] = {
    0, 224999424, 294999040, 344999936,
    394999808, 434999296, 469999616, 500000000
};
static const uint8_t routes[7] = {3, 5, 0, 0, 3, 1, 2};

static inline uint64_t hq_mix(uint64_t x) {
    x += UINT64_C(0x9e3779b97f4a7c15);
    x = (x ^ (x >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)) * UINT64_C(0x94d049bb133111eb);
    return x ^ (x >> 31);
}

/* Return 0 success, -1 null pointer, -2 invalid source or capacity. */
int hq500m_c5_batch(const uint32_t *sources, size_t n,
                    uint32_t *out_targets, int32_t *out_weights,
                    size_t out_capacity) {
    if (!sources || !out_targets || !out_weights) return -1;
    if (n > SIZE_MAX / 32 || out_capacity < 32 * n || n > 500000) return -2;

    for (size_t i = 0; i < n; ++i) {
        uint32_t gid = sources[i];
        if (gid >= HQ_TOTAL) return -2;
        uint64_t h0 = hq_mix((uint64_t)gid ^ HQ_SEED);
        int sign = (h0 % 100 < 20) ? -1 : 1;
        uint32_t source_page = gid / HQ_MODULE;
        uint32_t page_base = source_page * HQ_MODULE;
        uint32_t page_len = HQ_TOTAL - page_base;
        if (page_len > HQ_MODULE) page_len = HQ_MODULE;
        uint32_t offset = gid - page_base;
        uint32_t odd = (uint32_t)((h0 >> 11) & UINT64_C(0xffffffff)) | 1U;
        size_t region = 0;
        while (region < 6 && gid >= bounds[region + 1]) ++region;
        uint32_t target_begin = bounds[routes[region]];
        uint32_t target_end = bounds[routes[region] + 1];
        uint32_t remote_modules = (target_end - target_begin + HQ_MODULE - 1) / HQ_MODULE;

        for (uint32_t slot = 0; slot < 32; ++slot) {
            uint64_t h = hq_mix(h0 ^ ((uint64_t)(slot + 1) * HQ_K));
            uint32_t dest;
            if (slot < 24) {
                uint32_t lane = offset + (uint32_t)((uint64_t)(slot + 1) * odd);
                dest = page_base + lane % page_len;
            } else {
                uint32_t remote_base = target_begin +
                    (uint32_t)(hq_mix(h ^ (uint64_t)source_page) % remote_modules) * HQ_MODULE;
                uint32_t remote_len = target_end - remote_base;
                if (remote_len > HQ_MODULE) remote_len = HQ_MODULE;
                dest = remote_base + (uint32_t)((h >> 24) % remote_len);
            }
            size_t index = i * 32 + slot;
            out_targets[index] = dest;
            out_weights[index] = sign * (int32_t)(300 + (h >> 33) % 4800);
        }
    }
    return 0;
}

uint32_t hq500m_c5_abi_version(void) { return 1U; }
