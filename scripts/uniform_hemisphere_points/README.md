# plot\_hemisphere.py

A Python helper that **visualises arbitrary latitude‑band sampling** produced by

```python
next_location_on_sphere(start, end, step, i, N)
```

It renders the positive (upper‑z) hemisphere of the unit sphere and scatters **N** sample points whose *inclinations* follow a **range‑style** triple `(start, stop, step)`.

---

## Features

* Translucent 3‑D upper hemisphere drawn with **matplotlib**.
* Optional latitude rings at every automatically‑derived inclination.
* Cartesian conversion of the spherical coordinates returned by `next_location_on_sphere`.
* Index label over every dot for easy sanity checks.
* Accepts any valid Python expression for the three inclination arguments
  (e.g. `'math.pi/4'`, `'3*math.pi/6'`, `'0'`).

---

## Installation

```bash
# recommended: isolate dependencies
python3.11 -m venv .venv
source .venv/bin/activate
pip install numpy matplotlib
```

or, if you use **poetry**:

```bash
poetry install
```

---

## Usage

```text
usage: plot_hemisphere.py [-h] inc_start inc_stop inc_step N

Plot N points on the positive hemisphere.

positional arguments:
  inc_start   Python expression → first inclination θ (radians)
  inc_stop    Python expression → last  inclination θ (radians)
  inc_step    Python expression → step  between bands
  N           Integer > 0, total number of points

options:
  -h, --help  show this help message and exit
```

### Semantics

`(inc_start, inc_stop, inc_step)` mimic `range`:

Points are then spread **as evenly as possible** across those bands; within each band the azimuth is uniform over `0 … 2π`.

---

## Examples

| What is expected                                               | What to type                                                                  |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| **One pole point**                                             | `python uniform_hemisphere_points.py '0' 'math.pi/2' 'math.pi/2' 1`           |
| **Three dots on 45° latitude**                                 | `python uniform_hemisphere_points.py 'math.pi/4' 'math.pi/2' 'math.pi/2' 3`   |
| **Three dots on three bands (30°, 60°, 90°)**                  | `python uniform_hemisphere_points.py 'math.pi/6' '3*math.pi/6' 'math.pi/6' 3` |
| **Dense grid** – 5 bands between 0 and 90° step 18°, 30 points | `python uniform_hemisphere_points.py 0 'math.pi/2' 'math.pi/10' 30`           |

Each command pops up an interactive window showing

1. A semi‑transparent hemisphere.
2. Latitude rings at every generated inclination.
3. Sample points, each tagged with its index.

Close the window to quit.
