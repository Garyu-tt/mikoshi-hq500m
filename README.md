# Mikoshi HQ500M — CPU Playground

[![HQ500M Deep Ruby R08 — spatial atlas](docs/images/hq500m-r08-deep-ruby.webp)](docs/images/hq500m-r08-deep-ruby.webp)

**[Interactive Deep Ruby 3D viewer](https://garyu-tt.github.io/mikoshi-hq500m/)** · [Viewer source](docs/index.html) · [Geometry credits](docs/CREDITS.md)

The interactive R12 viewer uses **all 1,192,673 original point-cloud positions** and **520,150 sampled deterministic Q0.8 neural-address pairs**, with GPU depth occlusion (not every potential edge). 500 million virtual addresses and 16 billion potential connections describe the **synthetic HQ500M architecture**, not simultaneously simulated neurons or measured human axons.

*HQ500M R08 Deep Ruby — a computed, synthetic spatial visualization of the 500-million-address HQ500M architecture. This is **not** a measured human connectome or a simulation of 500 million simultaneously active neurons. Point-cloud geometry adapted from [Brain Point Cloud](https://sketchfab.com/3d-models/brain-point-cloud-c427ea0aee214141a78eba37bf9b76bb) by Terrie ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)); image palette and layout customized for Mikoshi.*

## Interactive 3D atlas — R12

**[Open HQ500M in 3D · rotate, zoom and inspect computed Q0.8 fibers](https://garyu-tt.github.io/mikoshi-hq500m/)**

The viewer loads **1,192,673 original point-cloud positions** and **520,150 sampled deterministic Q0.8 neural-address pairs** (not all 16 billion potential connections). Depth testing hides occluded fibers. The spatial neuron ID mapping and line paths are **synthetic**; this is not a measured human connectome. See the [R12 geometric-crest manifest](docs/assets/manifest_r12.json) · [Geometric crest method & verification](docs/R12_GEOMETRY.md) and [source credit](docs/CREDITS.md).

**A tiny, hackable neural sandbox with 500,000,000 virtual neuron addresses, named sensory/motor ports, and zero GPU requirements.**

This is the **public toy release**, not our large research installation. It runs on an ordinary computer using Python 3.11+ and the standard library only.

- **500,000,000 fixed, virtual addresses**; 32 on-demand potential outgoing edges per address.
- **896 active toy neurons by default** (7 regions × 128 cells); selectable **896 / 1,792 / 3,584 / 7,168** at runtime.
- 15 named sensory inputs, 6 motor outputs, synthetic functional bridges, spiking dynamics, simple reward-based plasticity and local checkpoint save/load.
- Compatible game-style observation keys from BrainFryGameAgent (`food`, `threat`, `obstacle`, `novelty`, `hunger`, `fatigue`, `reward`).
- Plain Python API, newline-delimited JSON or **localhost-only HTTP API** for game engines.

> **Important:** The 500 million neurons are *not simultaneously active*. This is a small **synthetic** network in a large **virtual** address space. The names cortex, thalamus, eye, spinal cord, etc. designate **hypothetical functional ports**, not biological reconstructions. It contains no human connectome, no quantum computation, and no claim of consciousness.

## Try it in under a minute

```bash
git clone https://github.com/Garyu-tt/mikoshi-hq500m.git
cd mikoshi-hq500m

python3 -m hq500m demo
python3 -m hq500m ports
python3 examples/simple_game.py
python3 -m unittest discover -s tests -v
```

**No** `pip install`, GPU, CUDA, pretrained model weights, paid API, database or network access is needed.

Try larger active windows, still with exactly 500 million virtual addresses:

```bash
python3 -m hq500m demo --cells 256
python3 -m hq500m demo --cells 1024
python3 -m hq500m query 499999999
```

The `--cells` number is **per region**. It changes RAM/CPU workload but never changes the fixed virtual network size.

## Connect to a game

**Option A: directly from Python**

```python
from hq500m import Brain

brain = Brain(cells=128, ticks=6)
reply = brain.step({
    "eye_left": 0.8,        # left-eye sensory channel
    "obstacle_left": 0.9,   # game sensor: obstacle on left
    "spinal_sensory": 0.2,  # body-state feedback
    "reward": 0.0          # feedback about the previous action
})
print(reply["action"], reply["motor_spikes"])
# Your game applies the chosen command. The model does NOT control the game itself.
```

**Option B: pipe JSON lines (one input/response per line)**

```bash
python3 -m hq500m jsonl
```

Send one line:

```json
{"observation":{"eye_left":0.8,"obstacle_left":0.9,"reward":0}}
```

Output includes `action`, `motor_spikes`, `motor_scores`, `spikes`, `step`, `resident_neurons` and `virtual_neurons`.

**Option C: localhost HTTP**

Terminal 1:

```bash
python3 -m hq500m server --port 8766 --state-file ./brain-state.json
```

Terminal 2:

```bash
curl http://127.0.0.1:8766/v1/ports
curl -s -X POST http://127.0.0.1:8766/v1/step \
  -H 'Content-Type: application/json' \
  -d '{"observation":{"food":1,"threat":0,"reward":0}}'
```

Endpoints: `GET /health`, `GET /v1/ports`, `POST /v1/step`. Server binds **only** to `127.0.0.1`. It is intentionally unauthenticated; do not reverse-proxy or expose it publicly without your own authentication and access policy.

The `reward` input is in [-1,1] and refers to the **previous** action, not the one the model is currently choosing. Omitted sensors default to 0. Sensor values must be finite numbers between -1 and 1. Motor commands are `forward`, `left`, `right`, `interact`, `retreat`, and `idle`. Your game adapter must handle physics, collisions, permissions and safety limits.

## Anatomical-style connector guide

| Role | Input / output ports | Toy region |
| --- | --- | --- |
| Vision | `eye_left`, `eye_right` | Thalamus |
| Hearing | `ear_left`, `ear_right` | Thalamus |
| Touch | `touch` | Thalamus |
| Body/spinal ascending input | `spinal_sensory` | Brainstem |
| Balance | `balance` | Cerebellum |
| Hunger, danger, smell | `hunger`, `threat`, `smell` | Limbic |
| Novelty/context | `novelty` | Hippocampus |
| Motion to game | `forward`, `left`, `right`, `retreat` | Brainstem |
| Interaction and no-op | `interact`, `idle` | Cortex / basal ganglia |

**Actual global neuron ID ranges, all 15 inputs, six outputs, bridge destinations and examples:** [EN connector map](docs/PORTS.md) · [Русская инструкция](docs/PORTS_RU.md). You can also inspect the machine-readable map using `python3 -m hq500m ports` or `GET /v1/ports`.

No spinal neurons are actually simulated: the ascending `spinal_sensory` and descending brainstem motor ports are **integration points** that game developers connect to avatar sensors and actions.

## What does this actually simulate?

The original HQ500M deterministic 32-edge address generator is implemented on CPU. Only potential edges whose endpoints are in the currently resident tiny windows participate in the toy LIF-like simulation. To make game interaction legible, **additional named sensor→motor bridges** are connected explicitly; these bridges are **not** the original procedural C5 edges or measured human pathways.

A tiny action-value table and bounded bridge gains can be modified by `reward`; this is a game-learning demonstration, **not** proof of emergent intelligence. State is saved only when `--state-file` is specified (or you call `Brain.save(path)`).

The **historical CUDA implementation** is not needed for the public CPU entrypoint. The old CUDA Q0.8 experiments do not validate the toy game-port mapping; treat them as separate research.

## License

GPL-3.0-or-later (see [LICENSE](LICENSE) and [AUTHORS.md](AUTHORS.md)). Contributions, alternative adapters, games and experiments are welcome.
