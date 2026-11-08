#!/usr/bin/env python3
"""Inspect 32 virtual edges from one global HQ500M neuron. CPU-only."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from hq500m_oracle import N, expected, region  # noqa: E402


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 tools/query_edges.py NEURON_ID (0..499999999)")
    try:
        src = int(sys.argv[1], 10)
    except ValueError:
        raise SystemExit("Neuron ID must be an integer")
    if not 0 <= src < N:
        raise SystemExit(f"Neuron ID must be within 0..{N - 1}")
    edges = []
    for slot in range(32):
        target, weight, gene, inhibitory = expected(src, slot)
        edges.append({
            "slot": slot, "target": target, "weight_raw": weight,
            "gene": gene, "inhibitory": bool(inhibitory),
            "type": "local" if slot < 24 else "projected"
        })
    print(json.dumps({
        "project": "Mikoshi HQ500M",
        "source": src,
        "region_index": region(src),
        "virtual_neurons": N,
        "edges_materialized_by_this_query": len(edges),
        "full_graph_materialized": False,
        "edges": edges
    }, indent=2))


if __name__ == "__main__":
    main()
