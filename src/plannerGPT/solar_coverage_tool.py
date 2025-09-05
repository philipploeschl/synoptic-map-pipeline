import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
import spiceypy as sp

class SolarCoveragePlanner:
    def __init__(self, dlon: float = 0.5):
        """
        dlon: longitude bin size in degrees (default 0.5)
        """
        self.dlon = dlon
        self.nbins = int(360 / dlon)
        self.seen = np.zeros(self.nbins, dtype=bool)

    def _to_index(self, lon: float) -> int:
        lon = lon % 360
        return int(lon // self.dlon)

    def _mark_interval(self, center: float, half_width: float):
        L1 = (center - half_width) % 360
        L2 = (center + half_width) % 360

        def mark(Lstart, Lend):
            i1 = self._to_index(Lstart)
            i2 = self._to_index(Lend)
            for k in range(i1, i2 + 1):
                self.seen[k % self.nbins] = True

        if L1 <= L2:
            mark(L1, L2)
        else:
            mark(L1, 360 - self.dlon)
            mark(0, L2)

    def _unseen_measure(self, center: float, half_width: float) -> float:
        L1 = (center - half_width) % 360
        L2 = (center + half_width) % 360
        
        count = 0

        def count_unseen(Lstart, Lend):
            nonlocal count
            i1 = self._to_index(Lstart)
            i2 = self._to_index(Lend)
            for k in range(i1, i2 + 1):
                if not self.seen[k % self.nbins]:
                    count += 1

        if L1 <= L2:
            count_unseen(L1, L2)
        else:
            count_unseen(L1, 360 - self.dlon)
            count_unseen(0, L2)

        return count * self.dlon

    def plan_coverage(self, obsA: List[Tuple[pd.Timestamp, float, float]],
                      obsB: List[Tuple[pd.Timestamp, float, float]]) -> Tuple[pd.Timestamp, pd.DataFrame]:
        all_obs = [(t, 'A', lon, hw) for (t, lon, hw) in obsA] + \
                  [(t, 'B', lon, hw) for (t, lon, hw) in obsB]
        all_obs.sort(key=lambda x: x[0])

        timeline = []
        finish_time = None

        for t, sc, lon, hw in all_obs:
            unseen_before = self._unseen_measure(lon, hw)
            if unseen_before > 0:
                self._mark_interval(lon, hw)
            frac_seen = self.seen.sum() / self.nbins
            timeline.append((t, sc, frac_seen))
            if frac_seen >= 1.0 and finish_time is None:
                finish_time = t

        df = pd.DataFrame(timeline, columns=["time", "spacecraft", "coverage_fraction"])
        return finish_time, df

    def compute_longitudes(self, spacecraft: str, times: List[pd.Timestamp], abcorr: str = 'LT+S',
                           frame: str = 'IAU_SUN') -> List[float]:
        """
        Compute Carrington longitudes for a spacecraft at given times using SPICE.
        spacecraft: NAIF ID or name string (e.g., 'SDO' or '-144')
        times: list of pandas Timestamps
        Returns: list of Carrington longitudes in degrees
        """
        et_list = [sp.utc2et(t.strftime("%Y-%m-%dT%H:%M:%S")) for t in times]
        longitudes = []

        for et in et_list:
            spoint, trgepc, srfvec = sp.subpnt(method='Intercept: ellipsoid', target='SUN', et=et,
                                               fixref=frame, abcorr=abcorr, obsrvr=spacecraft)
            _, lon, _ = sp.reclat(spoint)
            lon_deg = np.degrees(lon) % 360
            longitudes.append(lon_deg)

        return longitudes

    def build_obs_from_spice(self, spacecraft: str, times: List[pd.Timestamp], half_width: float,
                             abcorr: str = 'LT+S', frame: str = 'IAU_SUN') -> List[Tuple[pd.Timestamp, float, float]]:
        """
        Construct observation list (time, center_longitude, half_width) from SPICE ephemeris.
        """
        longitudes = self.compute_longitudes(spacecraft, times, abcorr, frame)
        return [(t, lon, half_width) for t, lon in zip(times, longitudes)]
