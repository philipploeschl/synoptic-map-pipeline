"""
Solar Coverage Planner
----------------------
Fuse observations from two spacecraft (A, B) to find the earliest time when
the full 360° of Carrington longitudes is covered.

Two modes:
1) Data-driven: you provide observations for A and B as (time, lon_center_deg, half_width_deg).
2) SPICE-assisted (hook): provide a function that returns the sub-spacecraft Carrington longitude
   for a given spacecraft and time; the planner will schedule observations on a time grid
   and greedily trigger when marginal gain is high.

Notes
-----
- Times are ISO 8601 strings (UTC) or Python datetimes. Internally converted to datetime (naive, UTC).
- Longitudes are in [0, 360). Wrap-around is handled.
- For SPICE: we intentionally keep the dependency optional. You likely already have routines
  that compute Carrington longitudes from SPICE (as you noted). Plug them into the hook.
- Meta-kernel symbol usage reminder: entries in KERNELS_TO_LOAD should use "$" before symbols,
  e.g., "$LSK/naif0012.tls".

Author: ChatGPT (NASA-style helper)
License: MIT
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Tuple, Dict
import math
import bisect
import csv
from datetime import datetime, timezone, timedelta

# -----------------------------
# Utilities
# -----------------------------

def as_datetime(t) -> datetime:
    if isinstance(t, datetime):
        if t.tzinfo is None:
            return t.replace(tzinfo=timezone.utc)
        return t.astimezone(timezone.utc)
    if isinstance(t, (int, float)):
        # Treat as POSIX seconds
        return datetime.fromtimestamp(t, tz=timezone.utc)
    if isinstance(t, str):
        # Try ISO 8601
        return datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(timezone.utc)
    raise TypeError(f"Unsupported time type: {type(t)}")


def wrap360(x: float) -> float:
    return x % 360.0


def interval_union_1d(intervals: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Union of intervals on a circle [0, 360). Assumes intervals are normalized so that
    each (a, b) satisfies 0 <= a < 360, 0 <= b < 360, and handles wrap by splitting.
    Returns a list of non-overlapping intervals covering the union, with a<=b and within [0,360).
    """
    if not intervals:
        return []
    # Split wrap-around intervals
    linear = []
    for a, b in intervals:
        a = wrap360(a)
        b = wrap360(b)
        if a <= b:
            linear.append((a, b))
        else:
            linear.append((a, 360.0))
            linear.append((0.0, b))
    # Sort and merge
    linear.sort()
    out = []
    cur_a, cur_b = linear[0]
    for a, b in linear[1:]:
        if a <= cur_b + 1e-9:
            cur_b = max(cur_b, b)
        else:
            out.append((cur_a, cur_b))
            cur_a, cur_b = a, b
    out.append((cur_a, cur_b))
    return out


def interval_measure(intervals: List[Tuple[float, float]]) -> float:
    """Total length (deg) of union intervals that are normalized and non-overlapping in [0,360)."""
    return sum(max(0.0, b - a) for a, b in intervals)


def subtract_intervals(U: List[Tuple[float, float]], V: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Return U \ V (set difference) for linear, non-overlapping sorted lists within [0,360).
    Assume each list contains intervals (a<=b), non-overlapping, sorted, within 0..360.
    """
    out = []
    i, j = 0, 0
    while i < len(U):
        a, b = U[i]
        cur = a
        while j < len(V) and V[j][1] <= a:
            j += 1
        k = j
        while k < len(V) and V[k][0] < b:
            va, vb = V[k]
            if va > cur:
                out.append((cur, min(b, va)))
            cur = max(cur, vb)
            if cur >= b:
                break
            k += 1
        if cur < b:
            out.append((cur, b))
        i += 1
    return out


def interval(center: float, half_width: float) -> List[Tuple[float, float]]:
    """Return normalized interval(s) (possibly wrapping) representing [center-half_width, center+half_width] on the circle."""
    a = wrap360(center - half_width)
    b = wrap360(center + half_width)
    if a <= b:
        return [(a, b)]
    else:
        return [(a, 360.0), (0.0, b)]


# -----------------------------
# Data classes
# -----------------------------

@dataclass(order=True)
class Obs:
    t: datetime
    lon_center_deg: float
    half_width_deg: float
    sc: str  # 'A' or 'B'


@dataclass
class CoverageResult:
    finish_time: Optional[datetime]
    coverage_timeline: List[Tuple[datetime, float]]  # (time, covered_fraction_0_1)
    last_contributor: Optional[str]


# -----------------------------
# Core: data-driven fusion
# -----------------------------

def fuse_observations(observations: Iterable[Obs], dlon: float = 0.5) -> CoverageResult:
    """
    Given a single iterable of Obs (from A and B), compute the earliest time when
    coverage reaches 360°.
    Returns CoverageResult with timeline.
    """
    obs_sorted = sorted(observations, key=lambda o: o.t)
    # Maintain union of covered intervals (linearized in [0, 360))
    covered: List[Tuple[float, float]] = []
    timeline: List[Tuple[datetime, float]] = []
    last_sc: Optional[str] = None

    for o in obs_sorted:
        V = interval(o.lon_center_deg, o.half_width_deg)
        new_union = interval_union_1d(covered + V)
        covered = new_union
        frac = interval_measure(covered) / 360.0
        timeline.append((o.t, frac))
        if frac >= 0.999999:
            last_sc = o.sc
            return CoverageResult(finish_time=o.t, coverage_timeline=timeline, last_contributor=last_sc)

    return CoverageResult(finish_time=None, coverage_timeline=timeline, last_contributor=last_sc)


# -----------------------------
# Planning (SPICE-assisted hook)
# -----------------------------

CarringtonHook = Callable[[datetime, str], float]
# Expected to return sub-spacecraft Carrington longitude (deg) for the given spacecraft id and UTC datetime.


def greedy_plan(
    t0: datetime,
    t1: datetime,
    dt_minutes: int,
    half_width_A: float,
    half_width_B: float,
    can_obs_A: Callable[[datetime], bool],
    can_obs_B: Callable[[datetime], bool],
    carrington_hook: CarringtonHook,
) -> CoverageResult:
    """
    Greedy planning on a fixed time grid [t0, t1] with cadence dt_minutes.
    At each grid time, compute marginal gain and "fire" any spacecraft with positive gain.
    """
    assert t1 > t0
    covered: List[Tuple[float, float]] = []
    timeline: List[Tuple[datetime, float]] = []
    last_sc: Optional[str] = None

    t = t0
    while t <= t1:
        actions = []
        if can_obs_A(t):
            lonA = carrington_hook(t, 'A')
            Va = interval(lonA, half_width_A)
            gainA = interval_measure(subtract_intervals(interval_union_1d(Va), covered))
            actions.append(('A', Va, gainA))
        if can_obs_B(t):
            lonB = carrington_hook(t, 'B')
            Vb = interval(lonB, half_width_B)
            gainB = interval_measure(subtract_intervals(interval_union_1d(Vb), covered))
            actions.append(('B', Vb, gainB))

        # Sort by gain, descending; fire any with positive gain
        actions.sort(key=lambda x: -x[2])
        fired = False
        for sc, V, g in actions:
            if g > 1e-6:
                covered = interval_union_1d(covered + V)
                frac = interval_measure(covered) / 360.0
                timeline.append((t, frac))
                last_sc = sc
                fired = True
                if frac >= 0.999999:
                    return CoverageResult(finish_time=t, coverage_timeline=timeline, last_contributor=last_sc)
        # If nobody fired, still record timeline point for monitoring
        if not fired:
            timeline.append((t, interval_measure(covered) / 360.0))
        t += timedelta(minutes=dt_minutes)

    return CoverageResult(finish_time=None, coverage_timeline=timeline, last_contributor=last_sc)


# -----------------------------
# CSV I/O helpers
# -----------------------------

def read_observations_csv(path: str, sc_label: str) -> List[Obs]:
    """
    CSV columns: time_iso, lon_center_deg, half_width_deg
    """
    out = []
    with open(path, newline='') as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            out.append(Obs(
                t=as_datetime(row['time_iso']),
                lon_center_deg=float(row['lon_center_deg']),
                half_width_deg=float(row['half_width_deg']),
                sc=sc_label,
            ))
    return out


def write_timeline_csv(path: str, timeline: List[Tuple[datetime, float]]):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['time_iso', 'covered_fraction'])
        for t, frac in timeline:
            w.writerow([t.isoformat(), f"{frac:.6f}"])


# -----------------------------
# Carrington hook template (SPICE)
# -----------------------------

def carrington_hook_template(t: datetime, sc: str) -> float:
    """
    Template function for computing sub-spacecraft Carrington longitude.
    Replace the body of this function with your own implementation.
    Example using SpiceyPy (pseudo-code):
        import spiceypy as sp
        # load kernels once at module import time using a furnished meta-kernel (.tm)
        et = sp.utc2et(t.strftime("%Y-%m-%dT%H:%M:%S"))
        # Get sub-solar / sub-spacecraft surface point in IAU_SUN and then convert to Carrington
        # 1) subpnt/subslr with TARGET='SUN', FIXREF='IAU_SUN', OBSRVR='SCID'
        # 2) Convert surface point to heliographic (Stonyhurst) lon/lat
        # 3) Convert Stonyhurst -> Carrington using your L0(t) routine
        # return carrington_longitude_deg % 360.0
    """
    raise NotImplementedError("Provide your SPICE-based Carrington longitude function.")
