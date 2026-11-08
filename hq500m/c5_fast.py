"""Exact HQ500M C5 oracle-compatible generator, optimized for firing-neuron batches.

Computes source-invariant hash/polarity/region only once for all 32 slots.
No approximation, rounding, topological shortcut, or quantized weights.
This is an optimization of the existing synthetic C5 generator, not a
learned neural model or human connectome.
"""
from functools import lru_cache
from .core import (
    BOUNDS, K, MASK, MODULE, ROUTES, SEED, VIRTUAL_NEURONS,
    mix, region,
)

C5_GAIN = 0.000035


@lru_cache(maxsize=8192)
def source_edges(global_id):
    """Tuple of 32 (exact target ID, signed LIF gain) from original C5."""
    if type(global_id) is not int or not 0 <= global_id < VIRTUAL_NEURONS:
        raise ValueError("global_id must be an integer in 0..499999999")

    h0 = mix(global_id ^ SEED)
    inhibitory = h0 % 100 < 20
    sign = -1 if inhibitory else 1

    page_base = global_id // MODULE * MODULE
    page_len = min(MODULE, VIRTUAL_NEURONS - page_base)
    offset = global_id - page_base
    odd = ((h0 >> 11) & 0xFFFFFFFF) | 1

    r = region(global_id)
    target_region = ROUTES[r]
    begin = BOUNDS[target_region]
    end = BOUNDS[target_region + 1]
    remote_modules = (end - begin + MODULE - 1) // MODULE

    result = []
    for slot in range(32):
        h = mix(h0 ^ (((slot + 1) * K) & MASK))
        if slot < 24:
            target = page_base + (((offset + (slot + 1) * odd) & 0xFFFFFFFF) % page_len)
        else:
            remote_base = begin + (
                mix(h ^ (global_id // MODULE)) % remote_modules
            ) * MODULE
            last_count = min(MODULE, end - remote_base)
            target = remote_base + ((h >> 24) % last_count)

        weight = sign * (300 + ((h >> 33) % 4800))
        result.append((target, weight * C5_GAIN))
    return tuple(result)
