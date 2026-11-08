#!/usr/bin/env python3
"""CPU-only contract tests: scope, address bounds, stable deterministic edges."""
from pathlib import Path
import hq500m_oracle as q

root = Path(__file__).resolve().parents[1]
source = (root / "src" / "genesis_hq500m_q08.cu").read_text()

assert q.N == 500_000_000, "The address space must remain fixed at 500M"
assert "constexpr u64 N=500000000ULL" in source, "CUDA address space changed"
assert len(q.REGIONS) == 8 and q.REGIONS[0] == 0 and q.REGIONS[-1] == q.N

sources = (0, 1, 1023, 1024, 224_999_423, 224_999_424,
           294_999_039, 294_999_040, 469_999_615,
           469_999_616, 499_999_998, 499_999_999)
for neuron in sources:
    a = [q.expected(neuron, i) for i in range(32)]
    b = [q.expected(neuron, i) for i in range(32)]
    assert a == b, "The edge generator must be deterministic"
    assert len(a) == 32
    assert all(0 <= e[0] < q.N for e in a)
    assert all(q.region(e[0]) >= 0 for e in a)
    assert all(neuron // q.MODULE == e[0] // q.MODULE for e in a[:24])

try:
    q.region(q.N)
except ValueError:
    pass
else:
    raise AssertionError("Out-of-bounds neuron accepted")

print(f"PASS: fixed {q.N:,} virtual neuron IDs; 12 boundary samples x 32 edges; CPU-only")
