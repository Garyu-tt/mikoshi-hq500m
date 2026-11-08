"""Mikoshi HQ500M public CPU playground (synthetic, not biological)."""
from .core import Brain, VIRTUAL_NEURONS, describe_ports, edge

__all__ = ["Brain", "VIRTUAL_NEURONS", "describe_ports", "edge", "BitWeaveBrain", "PagedBrain"]

from .bitweave import BitWeaveBrain

from .page_engine import PagedBrain
