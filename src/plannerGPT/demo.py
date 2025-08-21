#!/usr/bin/env python3
"""
Demo for Solar Coverage Planner
"""
from datetime import datetime, timedelta, timezone
from solar_coverage_planner import Obs, fuse_observations, greedy_plan

# --- Demo 1: Data-driven fusion with synthetic observations ---
t0 = datetime(2025, 8, 18, 0, 0, 0, tzinfo=timezone.utc)
obs = []
# Spacecraft A takes two full-disk images (effective half-width 90 deg) at t0 and t0+2 days
obs.append(Obs(t=t0, lon_center_deg=10.0, half_width_deg=90.0, sc='A'))
obs.append(Obs(t=t0 + timedelta(days=2), lon_center_deg=190.0, half_width_deg=90.0, sc='A'))
# Spacecraft B takes one in between, offset to close the largest gap
obs.append(Obs(t=t0 + timedelta(days=1), lon_center_deg=100.0, half_width_deg=90.0, sc='B'))

res = fuse_observations(obs)
print("=== Demo 1: Data-driven ===")
print("Finish time:", res.finish_time)
print("Last contributor:", res.last_contributor)
print("Timeline points:", len(res.coverage_timeline))
if res.finish_time is not None:
    print("Completed at:", res.finish_time.isoformat())

# --- Demo 2: Planning with a dummy Carrington hook (no SPICE) ---
def dummy_carrington_hook(t, sc):
    # Simple model: A and B are fixed-separation observers with slowly changing longitudes
    # A advances 13 deg/day; B is A+150 deg
    days = (t - t0).total_seconds() / 86400.0
    lamA = (10.0 + 13.0*days) % 360.0
    if sc == 'A':
        return lamA
    else:
        return (lamA + 150.0) % 360.0

def always_true(_): return True

res2 = greedy_plan(
    t0=t0,
    t1=t0 + timedelta(days=15),
    dt_minutes=60,
    half_width_A=90.0,
    half_width_B=90.0,
    can_obs_A=always_true,
    can_obs_B=always_true,
    carrington_hook=dummy_carrington_hook,
)

print("\n=== Demo 2: Planning (dummy hook) ===")
print("Finish time:", res2.finish_time)
print("Last contributor:", res2.last_contributor)
print("Timeline points:", len(res2.coverage_timeline))
if res2.finish_time is not None:
    print("Completed at:", res2.finish_time.isoformat())
