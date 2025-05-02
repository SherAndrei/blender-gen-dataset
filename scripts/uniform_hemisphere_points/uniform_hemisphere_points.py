#!/usr/bin/env python3
"""
Visualize samples on the positive (upper-z) hemisphere.

Usage
-------
python plot_hemisphere.py <inc_start> <inc_stop> <inc_step> <N>

* <inc_start>, <inc_stop>, <inc_step> -- any valid Python expressions
  that evaluate to numbers (e.g. "math.pi/2", "3*math.pi/6").
  They play the same role as the first three arguments of `range`
  (start, stop, step) but operate on radian inclinations.
* <N> -- integer number of points to plot.

Examples
--------
# one point at the pole (inclination 0)
python plot_hemisphere.py '0' '0' '0' 1

# three points on the 45° latitude
python plot_hemisphere.py 'math.pi/4' 'math.pi/4' '0' 3

# three latitudes (30°, 60°, 90°) - one point each
python plot_hemisphere.py 'math.pi/6' '3*math.pi/6' 'math.pi/6' 3
"""

import argparse
import math
from types import MappingProxyType

import matplotlib.pyplot as plt
import numpy as np


def safe_eval(expr: str) -> float:
    """Evaluate a numeric Python expression in a restricted namespace."""
    allowed_names = MappingProxyType({"math": math, "pi": math.pi})
    try:
        value = eval(expr, {"__builtins__": {}}, allowed_names)
    except Exception as exc:
        raise argparse.ArgumentTypeError(f"Bad expression '{expr}': {exc}")
    if not isinstance(value, (int, float)):
        raise argparse.ArgumentTypeError(f"Expression '{expr}' did not return a number")
    return float(value)


def spherical_to_cartesian(radius, inc, azi):
    """Convert spherical coords to Cartesian (x,y,z)."""
    x = radius * np.sin(inc) * np.cos(azi)
    y = radius * np.sin(inc) * np.sin(azi)
    z = radius * np.cos(inc)
    return x, y, z


def plot_positive_hemisphere(ax, radius):
    theta = np.linspace(0, math.pi / 2, 40)
    phi   = np.linspace(0, 2 * math.pi, 80)
    TH, PH = np.meshgrid(theta, phi)
    X, Y, Z = spherical_to_cartesian(radius, TH, PH)

    ax.plot_surface(X, Y, Z, alpha=0.2, color="lightgrey", linewidth=0)


def plot_bands(ax, radius, inc_start, inc_stop, inc_step):
    def plot_band(ax, radius, inc):
      phi   = np.linspace(0, 2 * math.pi, 80)
      TH, PH = np.meshgrid(inc, phi)
      X, Y, Z = spherical_to_cartesian(radius, TH, PH)
      ax.plot(X, Y, Z, color="blue")

    counter = 0
    for inc in np.arange(inc_start, inc_stop, inc_step):
        counter += 1
        plot_band(ax, radius, inc)
    return counter


def next_location_on_sphere(inc_start: float, inc_stop: float, inc_step: float, i: int, N: int):
    if not (0 <= i < N):
        raise ValueError("0 <= i < N must hold")
    if not (0 <= inc_start < (math.pi / 2)):
        raise ValueError("0 <= inc_start < (math.pi / 2) must hold")
    if not (0 < inc_stop <= (math.pi / 2)):
        raise ValueError("0 < inc_stop <= (math.pi / 2) must hold")
    if not (inc_start < inc_stop):
        raise ValueError("inc_start < inc_stop must hold")
    if not (inc_step > 0):
        raise ValueError("inc_step > 0 must hold")

    # `ceil` to include band on `inc_start` position
    n_bands = math.ceil((inc_stop - inc_start) / inc_step)
    locations_per_slice = (N + n_bands - 1) // n_bands
    current_slice = i // locations_per_slice
    inc = inc_start + inc_step * current_slice
    azi = (2 * math.pi * (i + 1)) / locations_per_slice
    return inc, azi


def main():
    p = argparse.ArgumentParser(description="Plot hemisphere sample points.")
    p.add_argument("inc_start", help="start inclination (Python expr)")
    p.add_argument("inc_stop", help="stop  inclination (Python expr)")
    p.add_argument("inc_step", help="step  inclination (Python expr)")
    p.add_argument("N", type=int, help="number of points")
    args = p.parse_args()

    inc_start = safe_eval(args.inc_start)
    inc_stop = safe_eval(args.inc_stop)
    inc_step = safe_eval(args.inc_step)
    N = args.N
    if N <= 0:
        raise SystemExit("N must be a positive integer")

    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(projection="3d")
    radius = 1.0
    plot_positive_hemisphere(ax, radius)
    n_bands = plot_bands(ax, radius, inc_start, inc_stop, inc_step)

    for idx in range(N):
        th, ph = next_location_on_sphere(inc_start, inc_stop, inc_step, idx, N)
        x, y, z = spherical_to_cartesian(radius, th, ph)

        ax.scatter(x, y, z, s=40, color="red")
        ax.text(x, y, z, f"{idx}", fontsize=8, color="blue")

    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_zlim(0, 1)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.set_title(
        f"Hemisphere sampling: bands={n_bands}, N={N}\n"
        f"inc_range=[{inc_start:.3f},{inc_stop:.3f}], step={inc_step}"
    )
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
