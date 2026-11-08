# HQ500M functional connector map

**A developer IO schematic, not a neuroanatomical atlas.** These are fixed virtual neuron IDs from an experimental synthetic network. A port is **12 addressable cells**, with the default toy simulation activating 128 cells in each of the seven regions.

## Seven hypothetical regions (global address space)

| Region label | First virtual ID | Last virtual ID | Intended software role |
| --- | ---: | ---: | --- |
| Cortex | 0 | 224999423 | voluntary commands |
| Cerebellum | 224999424 | 294999039 | balance |
| Hippocampus | 294999040 | 344999935 | novelty |
| Thalamus | 344999936 | 394999807 | sensory relay |
| Basal ganglia | 394999808 | 434999295 | action inhibition |
| Brainstem | 434999296 | 469999615 | body relay / descending motor output |
| Limbic | 469999616 | 499999999 | salience, hunger, threat |

**These labels are functional metaphors.** The sizes and routes were selected for the project, not sourced from a real human connectome.

## Input ports: wire game sensors here

| Key | Global neuron IDs, inclusive | Game data to provide |
| --- | --- | --- |
| `eye_left` | 344999936–344999947 | left eye brightness, pixels reduced to a scalar, or left-side target probability |
| `eye_right` | 344999948–344999959 | right-side vision summary |
| `ear_left` | 344999960–344999971 | sound intensity or direction from left |
| `ear_right` | 344999972–344999983 | right-ear audio summary |
| `touch` | 344999984–344999995 | collision / haptic intensity |
| `obstacle_left` | 344999996–345000007 | obstruction on left |
| `obstacle_right` | 345000008–345000019 | obstruction on right |
| `food` | 345000020–345000031 | food or target cue |
| `spinal_sensory` | 434999296–434999307 | proprioception / injury / joint-state feedback |
| `fatigue` | 434999308–434999319 | energy/fatigue level |
| `balance` | 224999424–224999435 | tilt, falling, vestibular signal |
| `novelty` | 294999040–294999051 | new location or event |
| `smell` | 469999616–469999627 | odor-style cue |
| `hunger` | 469999628–469999639 | internal hunger meter |
| `threat` | 469999640–469999651 | enemy proximity / damage risk |

**Where to connect eyes:** provide `eye_left` and `eye_right` values. The adapter injects these into the *toy thalamus port*. It does **not** render or process raw retinal pixels. Your game extracts the features.

**Where to connect the spinal cord:** `spinal_sensory` is an **ascending body feedback input** located in the software *brainstem* window. The reverse path is implemented as abstract commands emitted from brainstem motor ports below. **There is no simulated spinal cord, reflex arc, human motor cortex or spinal tract** in this release.

## Output ports: read motor commands here

| Output action | Global neuron IDs | Suggested game-side behavior |
| --- | --- | --- |
| `forward` | 434999344–434999355 | advance |
| `left` | 434999356–434999367 | turn left |
| `right` | 434999368–434999379 | turn right |
| `interact` | 0–11 | use / pick up / interact |
| `retreat` | 434999380–434999391 | move backward / withdraw |
| `idle` | 394999808–394999819 | do nothing |

One motor response contains both the chosen `action` and all `motor_spikes` and `motor_scores`. The game decides **how** to apply it.

## Synthetic functional pathways

The public sandbox adds inspectable deterministic bridges from input groups to output groups. See `BRIDGES` in `hq500m/core.py` and `GET /v1/ports` -> `pathways`. Example pathways:

- `eye_left` → `left`; `eye_right` → `right`
- `obstacle_left` → `right`; `obstacle_right` → `left`
- `threat`, `touch`, `spinal_sensory` → `retreat`
- `food`, `novelty` → `interact`; `hunger`, `balance` → `forward`
- `fatigue` → `idle`

These are illustrative engineering wiring decisions, **not** evidence of actual anatomical pathways or validated emergent behavior. You can replace `BRIDGES` and the game-side observation adapter to experiment.

## Connect via direct Python

```python
from hq500m import Brain, describe_ports

brain = Brain(cells=128)
print(describe_ports()["inputs"]["eye_left"]["neuron_ids"])

observation = {
    "eye_left": 0.75, "eye_right": 0.1,
    "touch": 0.0, "spinal_sensory": 0.3,
    "threat": 0.1, "reward": 0.0
}
motor = brain.step(observation)
game.apply_command(motor["action"]) # Replace with your engine API
```

The last line is a **placeholder**: provide the game-specific `game.apply_command` implementation. For an actual runnable example use `python3 examples/simple_game.py`.

## Machine-to-machine protocol

```json
{"observation":{"eye_left":0.7,"obstacle_left":0.5,"spinal_sensory":0.2,"reward":0}}
```

Inputs are finite real numbers in [-1,1]. Extra keys are rejected. In particular, `reward` describes **the previous action**. You can also send the familiar `obstacle` alias, which feeds both obstacle ports.

Outputs:

```json
{"schema":"mikoshi-hq500m-game-v1","action":"right","motor_spikes":{"forward":0,"left":0,"right":24,"interact":0,"retreat":0,"idle":0},"neural_ticks":6,"resident_neurons":896,"virtual_neurons":500000000}
```

Values shown are an illustrative example; actual results depend on the current input and learned state. Read the full response schema from `python3 -m hq500m jsonl` or the local HTTP server. 
