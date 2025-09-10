import spiceypy as sp
import spiceypy.utils.support_types as stypes
import numpy as np
import os, sys
from pathlib import Path
from config.config import Config
from matplotlib import pyplot as plt
from sunpy.coordinates.sun import carrington_rotation_time, carrington_rotation_number
import pandas as pd
import argparse
from datetime import datetime, timedelta

def loadkernel(kpath, kname):
    "This function loads a SPICE kernel (which could be a metakernel) then returns to the current working directory."
    cur_wd = os.getcwd()
    os.chdir(kpath)
    sp.furnsh(os.path.join(kpath,kname))
    os.chdir(cur_wd)
    nloaded = sp.ktotal("ALL")
    return(nloaded)
    
def unloadkernel(kpath,kname):
    "This function unloads a SPICE kernel (which could be a metakernel) then returns to the current working directory."
    cur_wd = os.getcwd()
    os.chdir(kpath)
    sp.unload(kname)
    os.chdir(cur_wd)
    nloaded = sp.ktotal("ALL")
    return(nloaded)
    
def get_solo_coverage(mkpath):
    "This function simply returns the coverage of the loaded Solar Orbiter orbit kernel."
    for kernel in range(0,sp.ktotal("ALL")-1):
        kernel_data=sp.kdata(kernel,"ALL")
        if "solo_ANC_soc-orbit" in kernel_data[0]:
            solo_coverage = stypes.SPICEDOUBLE_CELL(2)
            kernel_path = os.path.join(mkpath, kernel_data[0])
            #kernel_path = kernel_data[0]
            sp.spkcov(kernel_path,-144,solo_coverage) #-144 is the NAIF ID for Solar Orbiter
            coverage_out=sp.wnfetd(solo_coverage,0)
            return(coverage_out)
    else:
        raise ValueError("No Solar Orbiter orbit kernel found in loaded kernels.")

def get_orbit_coverage(kernel_path, kernel_name, obj_id):
    "This function simply returns the coverage of the given orbit kernel."
    orbit_coverage = stypes.SPICEDOUBLE_CELL(200)
    kernel_path = os.path.join(kernel_path,kernel_name)
    sp.spkcov(kernel_path,obj_id,orbit_coverage)
    coverage_out=sp.wnfetd(orbit_coverage,0)
    return(coverage_out)

def calc_relative_rotation(hci_state):
    
    omega_a = 14.713*sp.rpd()/86400.0
    omega_b = -2.316*sp.rpd()/86400.0
    omega_c = -1.787*sp.rpd()/86400.0

    delta_omega = []

    for (index, item) in enumerate(hci_state[:,0]):
        [void1,void2,lat] = sp.reclat(hci_state[index,0:3])
        omega_sun = omega_a + omega_b*(np.sin(lat)**2) + omega_c*(np.sin(lat)**4)
        omega_sun_d_per_d = omega_sun*sp.dpr()*86400.0
        (r_norm, r_mag) = sp.unorm(hci_state[index,0:3])
        omega_solo = np.cross(hci_state[index,0:3],hci_state[index,3:6])/(r_mag**2)
        omega_solo_d_per_d = omega_solo[2]*sp.dpr()*86400.0
        delta_omega.append(omega_sun_d_per_d-omega_solo_d_per_d)
    return(delta_omega)

def simple_carrington(hci_lon, ets):
    
    rotation_period = 25.38
    base_time = "20 December 2018 11:47 (UTC)"

    omega = (2*np.pi)/(rotation_period*86400.0)
    t0 = sp.str2et(base_time)
    (basepos, ltime) = sp.spkpos("EARTH", t0, "SUN_INERTIAL","NONE","SUN")
    (baserad,baselon,baselat) = sp.reclat(basepos)
    baselon2 = (baselon*sp.dpr()+360.0) % 360
    
    clon = []
    for (index, et) in enumerate(ets):
        delta_t = et - t0
        delta_phi = (delta_t*omega*sp.dpr()) % 360
        zero_lon = (baselon2+delta_phi) % 360
        solo_lon = (hci_lon[index]*sp.dpr()+360) % 360
        clon_buffer = (360+(solo_lon-zero_lon)) % 360
        if clon_buffer > 180:
            clon_buffer = clon_buffer - 360
        clon.append(clon_buffer)
    return(clon)


def et2datetime64(ets):
    outtime = []
    try:
        iterator = iter(ets)
    except TypeError:
        ets2=[ets]
    else:
        ets2=ets
    for et in ets2:
        utc_string=sp.et2utc(et,"ISOC",3)
        outtime.append(np.datetime64(utc_string,"s"))
    return(outtime)


def datetime642et(dts):
    outets = []
    timstr = np.datetime_as_string(dts,unit="s")
    if isinstance(timstr,str):
        timstr=[timstr]
    for time in timstr:
        outet=sp.utc2et(time)
        outets.append(outet)
    return(outets)

def carrington_observation_deg(clon, hdis, ets, delta_phi, lld_start, lld_end=None, rsw_start=None, rsw_end=None):
    
    # This function assumes an observation program that is equally space in Carrington longitudes and 
    # calculates the respective observation times. The viewpoint is defined by the supplied clon/hdis of
    # the respective spacecraft/obsrevatory.

    # clon      ....... carrington longitude for et timesteps
    # hdis      ....... heliospheric distance
    # ets       ....... timestamps for clon/hdis in ephermeris time (spice)
    # lld_start ....... start time for synoptic maps observations (can be within RSW)
    # rsw_start ....... start time for RSW observations
    # rsw_end   ....... end time for RSW observations
    # delta_phi ....... interval between observations in hours

    obs_utc    = np.array([])
    obs_et     = np.array([])
    obs_dist   = np.array([])
    obs_clon   = np.array([])

    #rotation_period = 25.38 # sidereal period 
    #delta_phi = 360/(rotation_period * 24) * interval
    n_obs = int(np.ceil(360. / delta_phi))

    if rsw_start:
        t0 = max([sp.str2et(rsw_start), sp.str2et(lld_start)]) # select later time (eg lld_start within RSW)
        t1 = sp.str2et(rsw_end)                    # convert end_time to et
    else:
        # no RSW specified, use LLD start time
        t0 = sp.str2et(lld_start)   
        t1 = sp.str2et(lld_end)

    #TODO THIS CAN PROBABLY BE DONE FASTER WITH NP.SEARCHSORTED
    t0_index = np.ravel(np.argwhere(ets == t0)) # find the et index of start_time
 
    if t0_index.size > 0:                       # check if exact timestamp was found
        t0_index = t0_index[0]                  
    else:                                       # first timestamp after time t0
        t0_index = np.ravel(np.argwhere(ets > t0))[0]

    #TODO MIGHT BE A GOOD IDEA TO ADJUST T0 IF T0_INDEX IS MOVED TO DIFFERENT ET
    #TODO LOOKS LIKE THIS IS CONSIDERED BELOW WITH DELTA_CLON

    clon_t0 = np.interp(t0, ets, clon)          # interpolate clon at time t0
    delta_clon = clon[t0_index] - clon_t0       # clon offset between t0 and nearest entry


    # numpy interp needs the data in increasing continuous order
    # transform alternating clon to linear increment

    # clon mapped from -180° to 180°
    # find sign transitions  
    signs = np.sign(clon)
    trans = np.ravel(np.argwhere(np.diff(signs) == 2) + 1)
    
    # linearise between transition points
    clon_linear = np.copy(clon)                 # tracks the clon angle that has elapsed since t0 (positive, increasing)
    for i, pos in enumerate(trans):
        if i == len(trans)-1: 
            clon_linear[trans[i]:] -= np.zeros(len(clon_linear)-trans[i]) + 360 * (i+1)  
        else:
            clon_linear[trans[i] : trans[i+1]] -= np.zeros(trans[i+1]-trans[i]) + 360 * (i+1)            

    clon_linear = clon_linear * -1

    obs_et   = np.append(obs_et, t0)
    obs_dist = np.append(obs_dist, hdis[t0_index])
    
    # TODO CONFIRM IF THIS IS REALLY 360 OR 180 INSTEAD
    if clon_t0 < 0:
        obs_clon = np.append(obs_clon, clon_t0+360)
    else:
        obs_clon = np.append(obs_clon, clon_t0)

    i = 1    
    current_et = obs_et[0]   # initial value is t0 as set above by obs_et = np.append(obs_et, t0)
    
    
    while current_et < t1:
        # must be +delta_clon since clon_linear is always increasing
        # the original delta was measured on a decreasing slope
        clon_obs_lin = clon_linear[t0_index] + delta_clon + delta_phi * i

        current_et   = np.interp(clon_obs_lin, clon_linear, ets)
        current_hdis = np.interp(clon_obs_lin, clon_linear, hdis)

        obs_et   = np.append(obs_et,   current_et)
        obs_dist = np.append(obs_dist, current_hdis)
        
        clon_obs = clon[t0_index] - delta_clon - delta_phi * i
        
        # make sure clon_obs does not exceed 360 deg. Sign adjusted later
        clon_obs = (abs(clon_obs) % 360) * np.sign(clon_obs)

        if clon_obs < 0: clon_obs += 360    
        obs_clon = np.append(obs_clon, clon_obs)
        #obs_clon = np.append(obs_clon, clon_obs-clon_linear[t0_index]+clon_t0) # observed clon in linear increasing longitude (>360°)

        i += 1


    for entry in obs_et:
        obs_utc = np.append(obs_utc, sp.et2utc(entry, 'c', 2))
    

    if False:
        print('###### RESULTS ######')
        print(np.column_stack((obs_utc, obs_clon, obs_dist)))

    return [obs_utc, obs_et, obs_clon, obs_dist]


def carrington_observation_times(clon, hdis, ets, start_time, interval):

    # This function assumes an observation program that is equally space in time and 
    # calculates the respective carrington longitudes. The viewpoint is defined by the
    #  supplied clon/hdis of the respective spacecraft/obsrevatory.

    # Calculating the observation times in 4h intervals on earth
    # requires the synodic carrington rotation period as we don't iterate
    # over the (hopefully) correctly calculated carrington longitudes!

    # clon      ....... carrington longitude for et timesteps
    # hdis      ....... heliospheric distance
    # ets       ....... timestamps for clon/hdis in ephermeris time (spice)
    # start_time....... start time for observations
    # interval  ....... interval between observations in hours

    obs_utc    = np.array([], dtype="datetime64[s]")
    obs_et     = np.array([])
    obs_dist   = np.array([])
    obs_clon   = np.array([])

    interval = interval / 3600 # convert seconds to hours

    rotation_period = 28 # add some grace period for cadence spacing#  27.2753#25.38 # sidereal period 
    n_obs = int(np.ceil(rotation_period*24)/interval)

    #t0 = sp.str2et(start_time)                  # convert start_time to et
    t0 = datetime642et(start_time)[0]
    t0_index = np.ravel(np.argwhere(ets == t0)) # find the et index of start_time

    if t0_index.size > 0:                       # check if exact timestamp was found
        t0_index = t0_index[0]                  
    else:                                       # first timestamp after time t0
        t0_index = np.ravel(np.argwhere(ets > t0))[0]
    
    clon_t0 = np.interp(t0, ets, clon)          # interpolate clon at time t0
    delta_clon = clon[t0_index] - clon_t0       # clon offset between t0 and nearest entry


    #TODO THE LINEARISATION CAN BE EXPORTED TO A FUNCTION
    # numpy interp needs the data in increasing order
    # transform alternating clon to linear increment

    # find sign transitions  
    signs = np.sign(clon)
    trans = np.ravel(np.argwhere(np.diff(signs) == 2) + 1)
    
    # linearise between transition points
    clon_lin = np.copy(clon)                 # tracks the clon angle that has elapsed since t0 (positive, increasing)
    for i, pos in enumerate(trans):
        if i == len(trans)-1: 
            clon_lin[trans[i]:] -= np.zeros(len(clon_lin)-trans[i]) + 360 * (i+1)  
        else:
            clon_lin[trans[i] : trans[i+1]] -= np.zeros(trans[i+1]-trans[i]) + 360 * (i+1)            

    clon_lin = clon_lin * -1
    
    # initialise first element of output arrays
    if clon_t0 < 0:
        obs_clon = np.append(obs_clon, clon_t0+360)
    else:
        obs_clon = np.append(obs_clon, clon_t0)

    obs_et   = np.append(obs_et, t0)
    obs_dist = np.append(obs_dist, hdis[t0_index])

    for i in range(1,n_obs):
        
        t = t0 + i*interval*3600 #s
        obs_et = np.append(obs_et, t)
        
        clon_lin_crnt = np.interp(t, ets, clon_lin)                     # current linear clon
        clon_crnt = ((abs(clon_lin_crnt) % 360) -360)*-1 # currenct clon transformed from linear

        #if clon_crnt < 0: clon_crnt += 360   

        obs_clon = np.append(obs_clon, clon_crnt)
        obs_dist = np.append(obs_dist, np.interp(t, ets, hdis))


    for entry in obs_et:
        obs_utc = np.append(obs_utc, et2datetime64(entry)[0])#sp.et2utc(entry, 'c', 2))
    

    return [obs_utc, obs_et, obs_clon, obs_dist]



def interp360(clon, clons, ets):
    
    # interpolate within one cycle of carrington longitues [0,360]

    # numpy interp needs the data in increasing order
    # transform decreasing uncontiguous clons to linear increment

    # find sign transitions  
    signs = np.sign(clons)
    #trans = np.ravel(np.argwhere(np.diff(signs) == 2) + 1) # for -180 to 180
    trans = np.ravel(np.argwhere(np.diff(clons)>0) + 1) # for 0 to 360

    # linearise between transition points
    clons_lin = np.copy(clons)                 # tracks the clon angle that has elapsed since t0 (positive, increasing)
    for i, pos in enumerate(trans):
        if i == len(trans)-1: 
            #clon_lin[:trans[i]] += np.zeros(len(clon_lin)-trans[i]) + 360 * (i+1)  
            clons_lin[trans[i]:] -= np.zeros(len(clons_lin)-trans[i]) + 360 * (i+1)  

    # correct clon if within range that was mapped to negative numbers
    if clon > clons[0]:
        #clon -= 360 
        # eg 321 -> (321-(170-360)) % 180 * -1 = -151
        clon = (clon-(clons[0]-360)) % 180 * -1

    #print(clons_lin)

    #set_trace()
    return np.interp(clon, clons_lin[::-1], ets[::-1])



def carrington_observation_coverage(solo_obs, earth_obs):

    # this function relies on the observation split provided by carrington_observation_times and 
    # can thus return different fast synoptic observation times than the carrington_observation_duration
    # function which directly uses the et resolution

    # unpack obs_lld and obs_rsw
    [solo_utc,  solo_ets,  solo_clon,  solo_hdis]  = solo_obs
    [earth_utc, earth_ets, earth_clon, earth_hdis] = earth_obs
    
    earth_src = np.full(len(earth_utc), "HMI", dtype='<U3')  
    solo_src  = np.full(len(earth_utc), "PHI", dtype='<U3')  

    utc   = np.concatenate([solo_utc,  earth_utc])
    ets   = np.concatenate([solo_ets,   earth_ets])
    clons = np.concatenate([solo_clon, earth_clon])
    hdis  = np.concatenate([solo_hdis, earth_hdis])
    src   = np.concatenate([solo_src,  earth_src])


    # The resulting array contains the et ordered solo values before the earth values
    # This has to be ordered for increasing et again. The new order is determined with
    # the np.argsort function and applied to all 5 arrays. ET spacing is identical for
    # both sources, so each ET will appear twice in the merged array.

    order = np.argsort(ets)

    utc   = utc[order]
    ets   = ets[order]
    clons = clons[order]
    hdis  = hdis[order]
    src   = src[order]

    coverage       = np.zeros(360, dtype=bool)

    coverage_phi   = np.zeros(360, dtype=bool)
    coverage_hmi   = np.zeros(360, dtype=bool)

    coverage_time_phi  = np.empty(360, dtype="datetime64[s]")
    coverage_time_hmi  = np.empty(360, dtype="datetime64[s]")

    coverage_clon_phi = np.zeros(360, dtype=float)
    coverage_clon_hmi = np.zeros(360, dtype=float)

    coverage_src   = np.empty(360, dtype='<U3')
    coverage_clon  = np.zeros(360, dtype=float)
    coverage_time  = np.empty(360, dtype="datetime64[s]")


    # New version cannot iterate over general ets since there are entries
    # for different INTERPOLATED ets for solo and hmi. Therefore, 
    # merge solo_obs and earth_obs while tracking the obsevation source
    # (add src array = 2 to earth_obs) and then iterate over all ets
    # until the map is full. Discard remaining data once the map is full
    # and resolve duplicate observations by selecting the most recent one.

    prev_eclon = None # tracks the last observed carrington longitude from earth
    prev_sclon = None # tracks the last observed carrington longitude from solo

    for i, et in enumerate(ets):

        clon = int(clons[i])

        if src[i] == "PHI": prev_clon = prev_sclon
        if src[i] == "HMI": prev_clon = prev_eclon
        

        if prev_clon is None: # first iteration for each spacecraft
            coverage[clon] = True

            if src[i] == "PHI": 
                coverage_phi[clon] = True
                coverage_time_phi[clon] = et2datetime64(et)[0]
                coverage_clon_phi[clon] = clons[i]
                prev_sclon = clon

            elif src[i] == "HMI": 
                coverage_hmi[clon] = True
                coverage_time_hmi[clon] = et2datetime64(et)[0]
                coverage_clon_hmi[clon] = clons[i]
                prev_eclon = clon


        else:
            # observation in decreasing clon. prev_clon > clon
            # prev_clon - clon < 0 indicates a jump from low to high longitudes
            # hmiphisynoptic.py does not wrap from left to right end!
            # remove this case for now and find a workaround
            if False:#prev_clon - clon < 0:
                # with wrap around: jump over zero fill in both sides of the coverage array
                coverage[0:prev_clon] = True    # fill up the lower longitudes since previous clon
                coverage[clon:] = True          # fill up the high lontitudes from the current clon to the end
                                                # this can probably be converage[clon:] instead of :361

                if src[i] == "PHI": 
                    coverage_phi[0:prev_clon] = True
                    coverage_phi[clon:] = True

                    coverage_time_phi[0:prev_clon] = et2datetime64(et)[0]
                    coverage_time_phi[clon:]       = et2datetime64(et)[0]

                    coverage_clon_phi[0:prev_clon] = clons[i]
                    coverage_clon_phi[clon:]       = clons[i]
                    prev_sclon = clon

                elif src[i] == "HMI": 
                    coverage_hmi[0:prev_clon] = True
                    coverage_hmi[clon:] = True

                    coverage_time_hmi[0:prev_clon] = et2datetime64(et)[0]
                    coverage_time_hmi[clon:]       = et2datetime64(et)[0]

                    coverage_clon_hmi[0:prev_clon] = clons[i]
                    coverage_clon_hmi[clon:]       = clons[i]
                    prev_eclon = clon
            elif prev_clon - clon < 0:
                # wrap around disabled
                # use previous clon to fill until zero
                # use current clon to fill 360 to current clon
                # TODO
                coverage[0:prev_clon] = True    # fill up the lower longitudes since previous clon
                coverage[clon:] = True          # fill up the high lontitudes from the current clon to the end
                                                # this can probably be converage[clon:] instead of :361

                if src[i] == "PHI": 
                    coverage_phi[0:prev_clon] = coverage_phi[prev_clon]
                    coverage_phi[clon:] = True
                    
                    coverage_time_phi[0:prev_clon] = coverage_time_phi[prev_clon] # fill with the previous clon
                    coverage_time_phi[clon:]       = et2datetime64(et)[0]

                    coverage_clon_phi[0:prev_clon] = coverage_clon_phi[prev_clon] 
                    coverage_clon_phi[clon:]       = clons[i]
                    prev_sclon = clon

                elif src[i] == "HMI": 
                    coverage_hmi[0:prev_clon] = coverage_hmi[prev_clon]
                    coverage_hmi[clon:] = True

                    coverage_time_hmi[0:prev_clon] = coverage_time_hmi[prev_clon]
                    coverage_time_hmi[clon:]       = et2datetime64(et)[0]

                    coverage_clon_hmi[0:prev_clon] = coverage_clon_hmi[prev_clon]
                    coverage_clon_hmi[clon:]       = clons[i]
                    prev_eclon = clon
            else:
                coverage[clon:prev_clon] = True                

                if src[i] == "PHI": 
                    coverage_phi[clon:prev_clon] = True
                    coverage_time_phi[clon:prev_clon] = et2datetime64(et)[0]
                    coverage_clon_phi[clon:prev_clon] = clons[i]
                    prev_sclon = clon

                elif src[i] == "HMI": 
                    coverage_hmi[clon:prev_clon] = True
                    coverage_time_hmi[clon:prev_clon] = et2datetime64(et)[0]
                    coverage_clon_hmi[clon:prev_clon] = clons[i]
                    prev_eclon = clon
            
                    

        if np.all(coverage) == True:
            dt = (et - ets[0])/86400 # days
            print('FSM Creation Time: %s days'% np.round(dt,2))

            # resolve duplicates by selecting the most recent observation
            # find indices where both spacecraft have coverage
            for j in np.argwhere(coverage_phi & coverage_hmi).flatten():
                if coverage_time_phi[j] > coverage_time_hmi[j]:
                    coverage_phi[j] = True
                    coverage_hmi[j] = False
                else:
                    coverage_phi[j] = False
                    coverage_hmi[j] = True

            # prepare return arrays
            coverage_src[coverage_phi] = "PHI"
            coverage_src[coverage_hmi] = "HMI"

            coverage_clon[coverage_phi] = coverage_clon_phi[coverage_phi]
            coverage_clon[coverage_hmi] = coverage_clon_hmi[coverage_hmi]

            coverage_time[coverage_phi] = coverage_time_phi[coverage_phi]
            coverage_time[coverage_hmi] = coverage_time_hmi[coverage_hmi]

            #break
            return coverage_time, coverage_clon, coverage_src
    
    raise ValueError("Coverage not complete within given observation times.")


def calc_observation_durations(solo_clon, earth_clon, solo_hdis, ets):

    # carrington_observation_coverage concatenates solo and earth data and then
    # processes everything in one go instead of doing it separately for earth
    # and solo like in here

    #start_time = "1 January 2022 00:00 (UTC)"   # LTP05 during high omega CR2256 start time
    dt = np.array([])
    dt_date = np.array([], dtype='datetime64[s]')
    dt_hdis = np.array([])
    
    for t0_index, t0 in enumerate(ets):

        coverage = np.zeros(360)
        hdis = np.array([])

        for i, et in enumerate(ets[t0_index:]):

            eclon = int(earth_clon[t0_index+i])
            sclon = int(solo_clon[t0_index+i])

            # eclon and sclon are always decreasing after this operation
            # -180 < clon < 180
            if eclon < 0:
                eclon = eclon + 360

            if sclon < 0:
                sclon = sclon + 360
            
            if i > 0:
                if prev_eclon - eclon < 0:
                    # if we jump over zero fill in both sides of the coverage array
                    # 3xx:360 and 0:xx
                    coverage[0:prev_eclon] = 1
                    coverage[eclon:] = 1
                    prev_eclon = eclon
                    
                else:
                    coverage[eclon:prev_eclon] = 1
                    prev_eclon = eclon
                
                if prev_sclon - sclon < 0:
                    coverage[0:prev_sclon] = 1
                    coverage[sclon:] = 1
                    prev_sclon = sclon
                    hdis = np.append(hdis, solo_hdis[t0_index+i])

                else:
                    coverage[sclon:prev_sclon] = 1
                    prev_sclon = sclon
                    hdis = np.append(hdis, solo_hdis[t0_index+i])
                
            else:
                coverage[eclon] = 1
                coverage[sclon] = 1

                prev_eclon = eclon
                prev_sclon = sclon
                hdis = np.append(hdis, solo_hdis[t0_index+i])

            #print(i, et2datetime64(et), eclon, prev_eclon, sclon, prev_sclon, np.sum(coverage))

            if np.sum(coverage) == 360:
                t = ets[t0_index+i]
                dt = np.append(dt, (t - t0)/86400) # days
                dt_date = np.append(dt_date, et2datetime64(t0)[0]) #sp.et2utc(t0, 'C', 3))
                dt_hdis = np.append(dt_hdis, np.round(np.average(hdis), 6))
                break # leave inner for and continue with outer for


    return dt, dt_date, dt_hdis


def optimise_carringtion_rotation(start_date, end_date, ets, dt_date, dt, dt_hdis):

    # calculate the start date for the fastest carrington map for each carrington rotation

    #single index and integer et to prevent ERFA warnings for astropy time objects used in carrington_rotation_number()
    crot_start = int(carrington_rotation_number(start_date))
    crot_end   = int(carrington_rotation_number(end_date))
    crots      = np.arange(crot_start, crot_end+1)

    crot_times = [np.datetime64(time) for time in carrington_rotation_time(crots).datetime]
    crot_ets   = [datetime642et(time) for time in crot_times]
    diff = len(ets)-len(dt) # dt will be shorter due to incomplete ets for last carrington period in the series

    opt_obs = pd.DataFrame(index=range(crot_start, crot_end), columns=["start_date", "obs_time", "avg_hdis"])
    opt_obs.index.name = "carrington rotation"

    for t0, t1, crot in zip(crot_ets[:-1], crot_ets[1:], crots):
        # Boolean mask for values between t0 and t1
        # ets interval at same cadence ::cad as used in carrington_rotation_coverage()
        mask = (ets[:-diff] >= t0) & (ets[:-diff] <= t1)

        # Extract indices of current crot
        indices = np.where(mask)[0]

        # find minimum in the current crot range
        imin = np.argwhere(dt[indices] == np.min(dt[indices]))[0][0]

        opt_obs.loc[crot] = [dt_date[indices][imin], np.round(dt[indices][imin],2), dt_hdis[indices][imin]]

    return opt_obs


def obs2drms_times(obs_utc):

    "Converts input UTC to TAI and Spice compatible time string into a DRMS time string"

    months = dict([('JAN', '01'), ('FEB', '02'), ('MAR', '03'), ('APR', '04'), ('MAY', '05'), ('JUN', '06'), 
                   ('JUL', '07'), ('AUG', '08'), ('SEP', '09'), ('OCT', '10'), ('NOV', '11'), ('DEC', '12')]) 
    
    # TAI is exactly 37 seconds ahead of UTC. The 37 seconds results from the initial difference 
    # of 10 seconds at the start of 1972, plus 27 leap seconds in UTC since 1972. 
    obs_tai = obs_utc + np.timedelta64(37, 's')

    drms_times = [d.strftime('%Y.%m.%d_%H:%M:%S_TAI') for d in obs_tai.astype('O')]

    return drms_times


def create_drms_timestring(tai_str, coverage_src, cad_hmi, cad_phi):
    
    # Shortens the list of DRMS compatible TAIs to a single time period string
    skip = False
    src = np.zeros(len(coverage_src))
    src[coverage_src=='PHI'] = 1
    src[coverage_src=='HMI'] = 2

    # +1 PHI->HMI, first HMI entry after PHI
    # -1 HMI->PHI, first PHI entry after HMI

    # index of transition between observatories
    idx_trans = np.ravel(np.argwhere(np.diff(src)!=0)+1) # count from 0 to trans[0] for first set
    idx_trans = np.insert(idx_trans, 0, 0)               # cover entries between start and first transition
                     
    tstr_phi = ''
    tstr_hmi = ''

    # timestamps in decending order, reverse idx_trans and start at last entry
    start = len(src)-1

    for end in idx_trans[::-1]:

        # skip single entries at the beginning and end of the list if they accidentally made it in
        if start == end: 
            skip = True
            start = end-1
            continue

        if skip:
            # start timestring from previous entry to fill in data for the skipped longitudes
            dt = datetime.strptime(tai_str[start], "%Y.%m.%d_%H:%M:%S_TAI")
            offset_seconds = cad_hmi if coverage_src[start] == "HMI" else cad_phi
            dt = dt - timedelta(seconds=offset_seconds)
            tai_str[start] = dt.strftime("%Y.%m.%d_%H:%M:%S_TAI")
            skip = False
        
        if coverage_src[start] == "HMI":
            tstr_hmi  += tai_str[start] + '-' + tai_str[end] + ','

        elif coverage_src[start] == "PHI":
            tstr_phi  += tai_str[start] + '-' + tai_str[end] + ','
                
        start = end-1 # next entry to process is one before the current end
        

    # remove ',' after last entry
    tstr_hmi  = tstr_hmi[:-1]  
    tstr_phi  = tstr_phi[:-1]  

    return tstr_hmi, tstr_phi


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the synoptic pipeline with optional config and session paths."
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config.yaml (uses default parameters if no config is provided)."
    )
    return parser.parse_args()



if __name__ == "__main__":

    # Set cwd to file directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    AU = 149598000.0 #km

    # Load config from YAML
    #args = parse_args()
    #config = Config(config_path=args.config) if args.config else Config()
    config = Config(config_path='/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/src/config.yaml')

    # Load meta kernel
    loaded=loadkernel(config.spice_mkpath, config.spice_mkname)
 
    
    # get Ephemeris Time (et) range for SolO mission
    et_bounds=list(get_solo_coverage(config.spice_mkpath)) # ET timestamps over entire SolO mission
    
    if et_bounds[0] > datetime642et(np.datetime64(config.cr_date_start))[0]:
        raise ValueError("Start date is before start of SolO mission.")
    else:
        et_bounds[0] = datetime642et(np.datetime64(config.cr_date_start))[0]
    
    if et_bounds[1] < datetime642et(np.datetime64(config.cr_date_end))[0]:
        raise ValueError("End date is after end of SolO mission.")
    else:
        et_bounds[1] = datetime642et(np.datetime64(config.cr_date_end))[0]

    
    ets = np.arange(et_bounds[0],et_bounds[1], config.et_resolution)
    ets[len(ets)-1]=et_bounds[1]

    # get spacecraft state vector with spkezr, returns (position [km] and velocity [km/s]) and light time (one-way light time in seconds)
    #[solo_GSE_pos, ltime]    = sp.spkpos("SOLO", ets,"SOLO_GSE","NONE","EARTH")  
    [solo_HCI_state, ltime]  = sp.spkezr("SOLO", ets,"SUN_INERTIAL","NONE","SUN") 
    [earth_HCI_state, ltime] = sp.spkezr("EARTH",ets,"SUN_INERTIAL","NONE","SUN")

    solo_HCI_state = np.array(solo_HCI_state)
    solo_HCI_pos = solo_HCI_state[:,0:3]

    solo_hdis = np.zeros(len(ets))
    solo_hlon = np.zeros(len(ets))
    solo_hlat = np.zeros(len(ets))    

    earth_HCI_state = np.array(earth_HCI_state)
    earth_HCI_pos = earth_HCI_state[:,0:3]

    earth_hdis = np.zeros(len(ets))
    earth_hlon = np.zeros(len(ets))
    earth_hlat = np.zeros(len(ets))

    # reclat performs a rectangular to spherical conversion, returning distance, longitude and latitude
    # output in radians
    for i, void in enumerate(ets):
        [earth_hdis[i], earth_hlon[i], earth_hlat[i]] = sp.reclat(earth_HCI_pos[i,:])
        [solo_hdis[i],  solo_hlon[i],  solo_hlat[i]]  = sp.reclat(solo_HCI_pos[i,:])

    
    solo_hdis = solo_hdis/AU
    solo_hlat = solo_hlat*sp.dpr()
    earth_hdis = earth_hdis/AU


    # Calculate carrington longitudes as seen from Earth and SolO
    solo_clon  = simple_carrington(solo_hlon, ets)
    earth_clon = simple_carrington(earth_hlon, ets)

    # calculate observation durations for all possible start times
    crobs_duration, crobs_start, crobs_hdis = calc_observation_durations(solo_clon, earth_clon, solo_hdis, ets)  
    

    # save output here to file to speed up future processing

    # find the optimal start time for each carrington rotation for the fastest synoptic map creation
    crobs_opt = optimise_carringtion_rotation(config.cr_date_start, config.cr_date_end, ets, crobs_start, crobs_duration, crobs_hdis)


    # produce output list with optimised observation start date for each carrington rotation

    # pick a specific carrington rotation for further processing
    # load output from optimise_carringtion_observation and pick a specific CR
    if os.path.isabs(config.output_path):
        output_path = os.join(config.output_path, config.obsplan_path)
    else:   
        root_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))
        output_path = os.path.join(root_path, config.output_path, config.obsplan_path)
    
    os.makedirs(output_path, exist_ok=True)

    tstr_hmi = []
    tstr_phi = []
    for cr, obs in crobs_opt.iterrows():
        earth_obs = carrington_observation_times(earth_clon, earth_hdis, ets, obs["start_date"], config.earth_cad)
        solo_obs  = carrington_observation_times(solo_clon,   solo_hdis, ets, obs["start_date"], config.solo_cad)

        coverage_time, coverage_clon, coverage_src = carrington_observation_coverage(solo_obs, earth_obs)

        clons_obs, idx = np.unique(coverage_clon, return_index=True)
        obs_utc = coverage_time[idx]
        obs_src = coverage_src[idx]

        drms_tai = obs2drms_times(obs_utc)
        
        timestring_hmi, timestring_phi = create_drms_timestring(drms_tai, obs_src, config.earth_cad, config.solo_cad)
        
        tstr_hmi.append(timestring_hmi)
        tstr_phi.append(timestring_phi) 
        
        os.makedirs(os.path.join(output_path, f'CR{cr}'), exist_ok=True)
        with open(os.path.join(output_path, f'CR{cr}', f'carrington_observation_times_CR{cr}.txt'), 'w') as f:
            f.write('DRMS_TAI_TIMESTRING_HMI\n')
            f.write(f'{timestring_hmi}\n')
            f.write('\n')
            f.write('DRMS_TAI_TIMESTRING_PHI\n')
            f.write(f'{timestring_phi}\n')
            f.write('\n')
            f.write('UTC\tCARRINGTON_LONGITUDE\tSOURCE\n')
            for u, c, s in zip(obs_utc, clons_obs, obs_src):
                f.write(f'{u}\t{c:.6f}\t{s}\n')
            f.write('\n')


    crobs_opt['timestr_hmi'] = tstr_hmi
    crobs_opt['timestr_phi'] = tstr_phi


    # Write overview plan
    crobs_opt["obs_time"] = pd.to_numeric(crobs_opt["obs_time"], errors="coerce")
    crobs_opt["avg_hdis"] = pd.to_numeric(crobs_opt["avg_hdis"], errors="coerce") 
    crobs_opt["obs_time"] = crobs_opt["obs_time"].map(lambda x: f"{x:.2f}")
    crobs_opt["avg_hdis"] = crobs_opt["avg_hdis"].map(lambda x: f"{x:.6f}")
    crobs_opt.to_csv(os.path.join(output_path,'carrington_observation_plan_' + str(config.cr_date_start).replace(' ', '_') + '_' + str(config.cr_date_end).replace(' ', '_') + '.csv'), sep="\t", index=True)  
       
            # add phi and hmi timestrings to crobs_opt and save to file in output_path/planning
    # save full coverage and timestrings to dedicated files in dedicated folders
    #sp.kclear()

    # TODO 
    # - add main control functionality
    # - save carrington_observation_duration output to file to speed things up
    # - identify config parameters for export

    # - refactor code
    #   - refactor carrington observation functions and export the clon linearisation
    # - try chatgpt stuff
    #   - add centi clon support for coverage calculation for compatibility with MIP implementation


    # - current workflow:
    #   - run carrington_observation_duration to find best start date
    #   - run carrington_observation_coverage for that start date

    #   - convert obs2drms_times for UTC to TAI conversion with DRMS compatible time string format
    #   - create timestring for HMI and PHI part with create_drms_timestring



