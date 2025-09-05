
Solar Coverage Planner – Quickstart
===================================

Files:
- solar_coverage_planner.py  -> library
- demo.py                    -> small runnable demo without SPICE
- observations_A.csv / observations_B.csv -> CSV templates

Usage (data-driven fusion)
--------------------------
from solar_coverage_planner import Obs, fuse_observations, read_observations_csv
A = read_observations_csv("observations_A.csv", "A")
B = read_observations_csv("observations_B.csv", "B")
res = fuse_observations(A+B)
print(res.finish_time, res.last_contributor)

Usage (SPICE-assisted planning)
-------------------------------
1) Implement carrington_hook(t: datetime, sc: str) -> float (deg in [0,360)), which returns
   the sub-spacecraft Carrington longitude at time t for spacecraft 'A' or 'B'. You likely
   already have this routine based on SPICE and your Carrington converter.
2) Call greedy_plan() over the interval you care about and with your observability windows.

Meta-kernel note
----------------
When building your meta-kernel KERNELS_TO_LOAD list, remember that symbolic paths require '$':
   KERNELS_TO_LOAD = ( '$LSK/naif0012.tls', '$SPK/your_spks.bsp', ... )

