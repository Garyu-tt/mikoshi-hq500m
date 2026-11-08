"""Bounded four-branch dendritic proxy for synthetic event-driven neurons.

This is NOT a measured human cell or biophysical NMDA simulation.
It supplies deterministic synthetic slot-to-branch routing, branch
leak, local supralinear coincidence and somatic coupling. States exist
only for touched global IDs and are serializable in page checkpoints.
"""
import math

BRANCH_NAMES = ("basal_a", "basal_b", "proximal", "apical")
BRANCH_COUNT = len(BRANCH_NAMES)
BRANCH_DECAY = (0.60, 0.60, 0.68, 0.78)
BRANCH_COUPLING = (0.40, 0.40, 0.48, 0.52)
SOMA_DECAY = 0.68
ZERO_BRANCHES = (0.0, 0.0, 0.0, 0.0)
INITIAL = (0.0, -1, -100, *ZERO_BRANCHES)


def branch_for_slot(slot):
    """Synthetic proxy mapping; no target morphology is encoded in C5."""
    if type(slot) is not int or not 0 <= slot < 32:
        raise ValueError("C5 slot must be in 0..31")
    return slot // 8


def integrate(row, now, threshold, soma_current, branch_currents):
    """Advance a single touched, non-refractory neuron on an event tick.

    The somatic integrator is leaky. Each branch stores a bounded signed
    potential, decays independently, and contributes linearly plus a
    bounded supralinear term when local excitation is coincident.
    Spikes hard-reset all compartments in this minimal proxy.
    """
    if len(row) != 7 or len(branch_currents) != BRANCH_COUNT:
        raise ValueError("bad compartment vector")
    voltage, previous, fired, *old_branches = row
    if type(now) is not int or now < 0 or now <= previous:
        raise ValueError("non-monotonic dendritic tick")
    if now - fired <= 2:
        raise ValueError("refractory neurons must be excluded by caller")
    age = now - previous
    branches = tuple(
        max(-2.0, min(2.0, old * (BRANCH_DECAY[i] ** age) + branch_currents[i]))
        for i, old in enumerate(old_branches)
    )
    linear = sum(branches[i] * BRANCH_COUPLING[i] for i in range(BRANCH_COUNT))
    # Saturated proxy for regenerative local dendritic coincidence.
    nonlinear = sum(0.35 * max(0.0, v - 0.55)**2 for v in branches)
    voltage = voltage * (SOMA_DECAY ** age) + soma_current + linear + nonlinear
    if voltage >= threshold:
        return (0.0, now, now, *ZERO_BRANCHES), True
    return (max(-2.0, min(1.0, voltage)), now, fired, *branches), False
