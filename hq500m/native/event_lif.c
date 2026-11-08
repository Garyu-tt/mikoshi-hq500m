/* Fusion R06 exact event reduction and lazy membrane integration */
#include <stdint.h>
#include <stddef.h>
#include <math.h>
#define HQ_TOTAL UINT32_C(500000000)
#define HQ_NATIVE_MAX UINT32_C(1200000)
uint32_t hq500m_event_lif_abi_version(void) { return 1U; }
int hq500m_reduce_sorted(const uint32_t *ids, const double *amps,
                         size_t n, uint32_t *out_ids, double *out_amps,
                         size_t capacity, size_t *nout) {
    if (!ids || !amps || !out_ids || !out_amps || !nout) return -1;
    if (n > HQ_NATIVE_MAX || capacity < n) return -2;
    *nout = 0;
    if (n == 0) return 0;
    uint32_t current_id = ids[0];
    if (current_id >= HQ_TOTAL) return -2;
    double acc = 0.0;
    for (size_t i = 0; i < n; ++i) {
        uint32_t id = ids[i];
        if (id >= HQ_TOTAL || id < current_id) return -2;
        if (id != current_id) {
            out_ids[*nout] = current_id;
            out_amps[*nout] = acc;
            ++(*nout);
            current_id = id;
            acc = 0.0;
        }
        acc = acc + amps[i];
    }
    out_ids[*nout] = current_id;
    out_amps[*nout] = acc;
    ++(*nout);
    return 0;
}
int hq500m_lif_batch(double *voltages,
                     int64_t *last_updates, int64_t *last_fires,
                     const double *currents, unsigned char *flags,
                     size_t n, int64_t now, double threshold) {
    if (!voltages || !last_updates || !last_fires || !currents || !flags)
        return -1;
    if (n > HQ_NATIVE_MAX || now < 0 || !isfinite(threshold) ||
        threshold < 0.25 || threshold > 2.0) return -2;
    for (size_t i = 0; i < n; ++i) {
        if (now - last_fires[i] <= 2) {
            flags[i] = 0;
            continue;
        }
        if (last_updates[i] > now || last_updates[i] < -1 ||
            !isfinite(voltages[i]) || !isfinite(currents[i])) return -2;
        double decay = pow(0.68, (double)(now - last_updates[i]));
        double voltage = voltages[i] * decay + currents[i];
        last_updates[i] = now;
        if (voltage >= threshold) {
            voltages[i] = 0.0;
            last_fires[i] = now;
            flags[i] = 1;
        } else {
            if (voltage < -2.0) voltage = -2.0;
            else if (voltage > 1.0) voltage = 1.0;
            voltages[i] = voltage;
            flags[i] = 0;
        }
    }
    return 0;
}
