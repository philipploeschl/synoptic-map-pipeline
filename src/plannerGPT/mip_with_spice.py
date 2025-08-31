#!/usr/bin/env python3
"""Enhanced MIP planner for minimum-time full-longitude coverage (SPICE-ready).

This version includes a concrete SpiceyPy-based sub-spacecraft computation that returns
the Stonyhurst longitude (from the Sun-fixed IAU_SUN frame) and then converts to Carrington
using a user-supplied `stonyhurst_to_carrington(et, stonyhurst_lon_deg)` function.

Two spacecraft pre-mapped:
 - 'A' -> SDO (use Earth ephemeris; see notes)
 - 'B' -> Solar Orbiter (NAIF name 'SOLO' or 'SolarOrbiter' depending on your SPK/CK kernels)

IMPORTANT:
- You must implement `stonyhurst_to_carrington(et, stonyhurst_lon_deg)` in this file (or import it
  from your library). This function must compute Carrington prime meridian L0 at epoch `et`
  (ephemeris seconds past J2000) and return Carrington longitude = (stonyhurst_lon + L0) mod 360.
- The code will raise NotImplementedError if `stonyhurst_to_carrington` is not provided.
- For SDO we use the Earth observer ('EARTH' or 'EARTH_BARYCENTER') for sub-point computation,
  which is a good approximation for SDO's Sun-center geometry for Carrington longitudes.

See documentation strings in functions below for guidance and references.
"""

from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Tuple, Optional
import math, csv, argparse, sys, os

# Try import spiceypy
try:
    import spiceypy as sp
    HAVE_SPICE = True
except Exception:
    HAVE_SPICE = False

try:
    import pulp
    HAVE_PULP = True
except Exception:
    HAVE_PULP = False

# ----------------------------- Configurable parameters -----------------------------
t0 = datetime(2025, 8, 18, 0, 0, tzinfo=timezone.utc)
horizon_days = 15
t_end = t0 + timedelta(days=horizon_days)

cadence_A_minutes = 60
cadence_B_minutes = 120

half_width_A = 90.0
half_width_B = 90.0

dlon = 1.0  # degree bin
nbins = int(360 / dlon)

# Minimum separation (slew) per spacecraft in minutes (must have gap >= this between starts)
min_sep_A_minutes = 15
min_sep_B_minutes = 30

# Observability windows CSV format (optional): columns - sc, start_iso, end_iso
OBS_WINDOWS_CSV = None  # e.g., 'obs_windows.csv'

# ----------------------------- Utilities -----------------------------
def as_datetime(tstr: str) -> datetime:
    return datetime.fromisoformat(tstr.replace('Z', '+00:00')).astimezone(timezone.utc)

def wrap360(x: float) -> float:
    return x % 360.0

def build_time_list(t0: datetime, t1: datetime, cadence_minutes: int) -> List[datetime]:
    times = []
    t = t0
    while t <= t1:
        times.append(t)
        t += timedelta(minutes=cadence_minutes)
    return times

def interval_bins(center: float, half_width: float, dlon: float) -> List[int]:
    a = (center - half_width) % 360.0
    b = (center + half_width) % 360.0
    bins = []
    if a <= b:
        i1 = int(math.floor(a / dlon))
        i2 = int(math.floor(b / dlon))
        bins = list(range(i1, i2 + 1))
    else:
        i1 = int(math.floor(a / dlon))
        i2 = int(math.floor((360.0 - 1e-9) / dlon))
        bins = list(range(i1, i2 + 1))
        i1 = 0
        i2 = int(math.floor(b / dlon))
        bins += list(range(i1, i2 + 1))
    return sorted(set([i % nbins for i in bins]))


# ----------------------------- SPICE carrington hook implementation -----------------------------
def stonyhurst_to_carrington(et: float, stonyhurst_lon_deg: float) -> float:
    """User MUST implement this function for accurate Carrington conversion.

    Inputs:
      - et: ephemeris time (seconds past J2000) as used by SpiceyPy (float)
      - stonyhurst_lon_deg: Stonyhurst heliographic longitude in degrees (0..360),
          measured in the IAU_SUN frame (i.e., longitude of the sub-spacecraft point
          measured relative to the IAU_SUN X-axis).

    Output:
      - carrington_lon_deg: Carrington longitude in degrees (0..360).

    Guidance / simple approximate implementation (not as accurate as site L0 routine):
    -------------------------------------------------------------------------------
    The Carrington rotation prime meridian L0(t) can be computed from a reference epoch
    and the Carrington sidereal rotation rate (approx 14.1844 deg/day). One simple
    approximation is:
        L0(t) = L0_ref + omega_carr * (t_days_since_ref)
    where t_days_since_ref is days since a reference epoch with known L0_ref.
    However, for operational accuracy use your facility's L0 routine (from solar software).
    -------------------------------------------------------------------------------

    If you have a trusted L0 routine, place it here. Otherwise, the default below raises
    NotImplementedError to force you to decide on the exact conversion method.
    """
    # === BEGIN USER IMPLEMENTATION ===
    raise NotImplementedError("Please implement stonyhurst_to_carrington(et, stonyhurst_lon_deg) for your site.\n\
                               See comments above: compute Carrington prime meridian L0(et) and return\n\
                               (stonyhurst_lon_deg + L0) % 360.\n\
                               If you want a quick approximation, implement a simple linear L0 using the\\n\
                               Carrington rotation rate; but for ops accuracy, use your facility's L0(t).")


def compute_carrington_from_spice(et: float, sc_id: str) -> float:
    """Compute Carrington longitude (deg) of the sub-spacecraft point using SpiceyPy.

    Steps implemented here:
      1) Compute the sub-spacecraft surface intercept point on the Sun expressed in IAU_SUN coords
         using sp.subpnt with method 'Near point: ellipsoid'. The returned vector is in km.
      2) Convert the rectangular coordinates to spherical (range, lon, lat) using sp.reclat.
         The 'lon' returned is the Stonyhurst-like longitude measured in IAU_SUN frame (radians).
      3) Convert to degrees and call `stonyhurst_to_carrington(et, stonyhurst_lon_deg)` to get Carrington lon.

    NOTE: This implementation assumes kernels loaded and that the IAU_SUN frame is available.
    """
    if not HAVE_SPICE:
        raise RuntimeError("spiceypy is not installed in this environment.")
    # Use 'Near point: ellipsoid' to get the intercept on the Sun's surface in IAU_SUN
    try:
        spoint, trgepc, srfvec = sp.subpnt('Near point: ellipsoid', 'SUN', et, 'IAU_SUN', sc_id)
    except Exception as e:
        # Try 'Intercept: ellipsoid' as fallback
        spoint, trgepc, srfvec = sp.subpnt('Intercept: ellipsoid', 'SUN', et, 'IAU_SUN', sc_id)
    # spoint is a 3-vector (km) in IAU_SUN coordinates
    # Convert to spherical coords (range, lon, lat) - reclat returns (radius, lon_rad, lat_rad)
    r, lon_rad, lat_rad = sp.reclat(spoint)
    stonyhurst_lon_deg = math.degrees(lon_rad) % 360.0
    # Convert Stonyhurst -> Carrington using user-provided routine
    carr = stonyhurst_to_carrington(et, stonyhurst_lon_deg)
    return carr % 360.0


def carrington_hook_spice(t: datetime, sc: str) -> float:
    """Return Carrington longitude (deg) for spacecraft 'A' or 'B' using SpiceyPy.

    Spacecraft name map (update if your kernels use different names):
      - 'A' -> 'SDO'           (we use 'EARTH' observer for SDO-like geometry)
      - 'B' -> 'SOLO' or 'SolarOrbiter' (ensure your SPK/CK uses the same observer name)
    """
    if not HAVE_SPICE:
        raise RuntimeError("spiceypy not available in this Python environment.")
    # Map 'A'/'B' to SPICE names. Update these to match your kernels.
    sc_map = {'A': 'EARTH', 'B': 'SOLO'}
    sc_id = sc_map.get(sc, sc)
    et = sp.utc2et(t.strftime('%Y-%m-%dT%H:%M:%S'))
    # For SDO approximation we used 'EARTH' as observer to get near-Earth sub-point on Sun.
    return compute_carrington_from_spice(et, sc_id) % 360.0


# ----------------------------- Demo hook (used if spice not available) -----------------------------
def demo_carrington_hook(t: datetime, sc: str) -> float:
    days = (t - t0).total_seconds() / 86400.0
    base = (10.0 + 13.0 * days) % 360.0
    if sc == 'A':
        return base
    else:
        return (base + 150.0 + 0.05*days) % 360.0

# ----------------------------- Observability windows -----------------------------
def load_obs_windows(csv_path: Optional[str]) -> Dict[str, List[Tuple[datetime, datetime]]]:
    windows = {'A': [], 'B': []}
    if not csv_path:
        # default: always available
        windows['A'].append((t0, t_end))
        windows['B'].append((t0, t_end))
        return windows
    with open(csv_path, newline='') as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            sc = row['sc']
            start = as_datetime(row['start_iso'])
            end = as_datetime(row['end_iso'])
            windows.setdefault(sc, []).append((start, end))
    # Clip to planning horizon
    for sc in windows:
        clipped = []
        for a, b in windows[sc]:
            aa = max(a, t0)
            bb = min(b, t_end)
            if aa < bb:
                clipped.append((aa, bb))
        windows[sc] = clipped if clipped else [(t0, t0)]
    return windows

def is_time_in_windows(t: datetime, windows: List[Tuple[datetime, datetime]]) -> bool:
    for a, b in windows:
        if a <= t <= b:
            return True
    return False

# ----------------------------- ILP builder (unchanged) -----------------------------
def build_and_solve_ilp(
    carrington_hook: Callable[[datetime, str], float],
    min_sep_A_minutes: float = 0.0,
    min_sep_B_minutes: float = 0.0,
    obs_windows_csv: Optional[str] = None,
    export_lp_path: Optional[str] = None,
    use_demo_if_no_spice: bool = True,
):
    # Build candidate times honoring observability windows
    times_A = build_time_list(t0, t_end, cadence_A_minutes)
    times_B = build_time_list(t0, t_end, cadence_B_minutes)
    windows = load_obs_windows(obs_windows_csv)

    # Filter candidate times by windows
    times_A = [t for t in times_A if is_time_in_windows(t, windows['A'])]
    times_B = [t for t in times_B if is_time_in_windows(t, windows['B'])]

    cand_list = []
    coverage_map = {}
    for i, t in enumerate(times_A):
        lon = carrington_hook(t, 'A')
        bins = interval_bins(lon, half_width_A, dlon)
        coverage_map[('A', i)] = bins
        cand_list.append(('A', i, t))
    for j, t in enumerate(times_B):
        lon = carrington_hook(t, 'B')
        bins = interval_bins(lon, half_width_B, dlon)
        coverage_map[('B', j)] = bins
        cand_list.append(('B', j, t))

    # TODO
    # .index(t) does a linear search through unified_time_list.
    # If your lists are large, this could be slow (O(n²) total).
    # More efficient: build a dict once mapping each time to its index:

    # create index by mapping locations from times_A and times_B to unified_time_list
    all_times = sorted(set(times_A + times_B))
    unified_time_list = all_times
    time_index_map = {}
    for i, t in enumerate(times_A):
        time_index_map[('A', i)] = unified_time_list.index(t)
    for j, t in enumerate(times_B):
        time_index_map[('B', j)] = unified_time_list.index(t)

    n_global = len(unified_time_list)
    bins_coverers = {b: [] for b in range(nbins)}
    for (sc, idx), bins in coverage_map.items():
        for b in bins:
            bins_coverers[b].append((sc, idx))

    impossible_bins = [b for b, coverers in bins_coverers.items() if len(coverers) == 0]
    if impossible_bins:
        print("Warning: some longitude bins have no possible coverage in the horizon. First few:", impossible_bins[:10])

    if HAVE_PULP:
        prob = pulp.LpProblem("min_finish_time_cover", pulp.LpMinimize)
        x_vars = {}
        for sc, idx, t in cand_list:
            x_vars[(sc, idx)] = pulp.LpVariable(f"x_{sc}_{idx}", cat="Binary")
        Tmax = pulp.LpVariable("Tmax_index", lowBound=0, upBound=max(0, n_global-1), cat="Integer")
        prob += Tmax, "Minimize_finish_time_index"
        # Coverage
        for b in range(nbins):
            coverers = bins_coverers[b]
            prob += pulp.lpSum([x_vars[(sc, idx)] for (sc, idx) in coverers]) >= 1, f"cover_bin_{b}"
        # Link Tmax
        for sc, idx, t in cand_list:
            gidx = time_index_map[(sc, idx)]
            prob += Tmax >= gidx * x_vars[(sc, idx)], f"link_Tmax_{sc}_{idx}"

        # Slew/min-separation constraints
        # probably not necessary since the observation cadence will already provide this limitation
        def add_min_sep_constraint(sc_label, min_sep_min):
            if min_sep_min <= 0: return
            if sc_label == 'A':
                times = times_A
                prefix = 'A'
            else:
                times = times_B
                prefix = 'B'
            for i in range(len(times)):
                for j in range(i+1, len(times)):
                    dt = abs((times[j]-times[i]).total_seconds())/60.0
                    if dt < min_sep_min - 1e-9:
                        if (prefix, i) in x_vars and (prefix, j) in x_vars:
                            prob += x_vars[(prefix, i)] + x_vars[(prefix, j)] <= 1, f"minsep_{prefix}_{i}_{j}"
        add_min_sep_constraint('A', min_sep_A_minutes)
        add_min_sep_constraint('B', min_sep_B_minutes)

        # Small penalty on number of shots
        # this might cause an issue with the relatively much higher cadence of SDO data
        # rework this feature to have separate penalties for SDO and HMI
        # prob += 1e-3 * pulp.lpSum([x_vars[(sc, idx)] for sc, idx, _ in cand_list])

        # Small separate penalties for A and B to avoid bias
        penalty_A = 1e-3 * pulp.lpSum([x_vars[(sc, idx)] for sc, idx, _ in cand_list if sc == 'A'])
        penalty_B = 1e-3 * pulp.lpSum([x_vars[(sc, idx)] for sc, idx, _ in cand_list if sc == 'B'])

        # Add to objective
        prob += penalty_A + penalty_B

        # penalty for far distance obesrvation
        
        if export_lp_path:
            print("Exporting LP to", export_lp_path)
            prob.writeLP(export_lp_path)

        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=120, threads=0)
        status = prob.solve(solver)
        status_str = pulp.LpStatus[status] if status is not None else "Unknown"
        print("PuLP status:", status_str)
        if status_str in ("Optimal", "Integer Feasible"):
            chosen = []
            for sc, idx, t in cand_list:
                val = pulp.value(x_vars[(sc, idx)])
                if val is not None and val > 0.5:
                    chosen.append((sc, idx, t))
            Tmax_val = int(pulp.value(Tmax))
            return {
                'finish_time': unified_time_list[Tmax_val] if Tmax_val is not None and unified_time_list else None,
                'chosen': chosen,
                'unified_time_list': unified_time_list,
                'coverage_map': coverage_map,
            }
        else:
            print("Solver returned status", status_str)
            return None
    else:
        print("PuLP not available. Running greedy set-cover with min-sep enforcement (approx)."
              " Consider installing PuLP for exact ILP solving.")
        uncovered = set(range(nbins))
        chosen = []
        flat = [(sc, idx, t, time_index_map[(sc, idx)]) for sc, idx, t in cand_list]
        def violates_min_sep(sc, t, chosen_list, min_sep):
            for (csc, cidx, ct) in chosen_list:
                if csc == sc:
                    dt = abs((ct - t).total_seconds())/60.0
                    if dt < min_sep - 1e-9:
                        return True
            return False

        while uncovered and flat:
            best = None; best_gain = -1
            for sc, idx, t, gidx in flat:
                min_sep = min_sep_A_minutes if sc=='A' else min_sep_B_minutes
                if violates_min_sep(sc, t, chosen, min_sep):
                    continue
                gain = len(set(coverage_map[(sc, idx)]) & uncovered)
                if gain > best_gain or (gain==best_gain and (best and gidx < best[3])):
                    best = (sc, idx, t, gidx); best_gain = gain
            if best is None or best_gain<=0:
                break
            sc, idx, t, gidx = best
            chosen.append((sc, idx, t))
            uncovered -= set(coverage_map[(sc, idx)])
            flat = [c for c in flat if not (c[0]==sc and c[1]==idx)]

        if uncovered:
            print("Greedy failed to cover all bins. Remaining bins:", len(uncovered))
            return None
        else:
            Tmax_val = max(time_index_map[(sc, idx)] for sc, idx, _ in chosen)
            return {
                'finish_time': unified_time_list[Tmax_val],
                'chosen': chosen,
                'unified_time_list': unified_time_list,
                'coverage_map': coverage_map,
            }

# ----------------------------- Command-line interface -----------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--demo', action='store_true', help='Run demo using built-in demo_carrington_hook')
    p.add_argument('--use-spice', type=str, default=None, help='Path to metakernel (.tm) to load')
    p.add_argument('--export-lp', type=str, default=None, help='Export ILP to this .lp file (requires PuLP)')
    p.add_argument('--obs-windows', type=str, default=None, help='CSV file with observability windows')
    args = p.parse_args()

    hook = demo_carrington_hook
    if args.use_spice:
        if not HAVE_SPICE:
            print('spiceypy not installed. Install spiceypy to use --use-spice', file=sys.stderr)
            sys.exit(1)
        print('Loading metakernel', args.use_spice)
        sp.furnsh(args.use_spice)
        hook = carrington_hook_spice

    res = build_and_solve_ilp(
        carrington_hook=hook,
        min_sep_A_minutes=min_sep_A_minutes,
        min_sep_B_minutes=min_sep_B_minutes,
        obs_windows_csv=args.obs_windows,
        export_lp_path=args.export_lp,
    )
    if res is None:
        print('No feasible plan found or solver failed.')
        sys.exit(2)

    print('Finish time (UTC):', res['finish_time'].isoformat() if res['finish_time'] else 'None')
    print('Planned observations:')
    for sc, idx, t in sorted(res['chosen'], key=lambda x: (x[2], x[0])):
        print(f'  {sc}  idx={idx}  time={t.isoformat()}')

if __name__ == '__main__':
    main()
