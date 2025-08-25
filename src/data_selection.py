import spiceypy as sp
import spiceypy.utils.support_types as stypes
import numpy as np
import os, sys
from pathlib import Path
from config.config import Config
from matplotlib import pyplot as plt
from sunpy.coordinates.sun import carrington_rotation_time, carrington_rotation_number
import pandas as pd

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
        outtime.append(np.datetime64(utc_string,"ms"))
    return(outtime)


def datetime642et(dts):
    outets = []
    timstr = np.datetime_as_string(dts,unit="ms")
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

    obs_utc    = np.array([])
    obs_et     = np.array([])
    obs_dist   = np.array([])
    obs_clon   = np.array([])

    rotation_period = 27.2753#25.38 # sidereal period 
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
        obs_utc = np.append(obs_utc, sp.et2utc(entry, 'c', 2))
    

    return [obs_utc, obs_et, obs_clon, obs_dist]



def interp360(clon, clons, ets):
    
    print((clons[0], clon, np.interp(clon, clons, ets, period=360)))
    # interpolate within one cycle of carrington longitues [0,360]

    # numpy interp needs the data in increasing order
    # transform decreasing uncontiguous clons to linear increment

    # find sign transitions  
    signs = np.sign(clons)
    #trans = np.ravel(np.argwhere(np.diff(signs) == 2) + 1) # for -180 to 180
    trans = np.ravel(np.argwhere(np.diff(clons)>0) + 1) # for 0 to 360
    #print(clon)
    #print(trans)
    #print(clons)
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
    print(clons[0], clon, np.interp(clon, clons_lin[::-1], ets[::-1]))

    #set_trace()
    return np.interp(clon, clons_lin[::-1], ets[::-1])


def carrington_observation_coverage(solo_obs, earth_obs, plot=False):

    # this function relies on the observation split provided by carrington_observation_times and 
    # can thus return different fast synoptic observation times than the carrington_observation_duration
    # function which directly uses the et resolution

    # unpack obs_lld and obs_rsw
    [solo_utc,  solo_ets,  solo_clon,  solo_hdis]  = solo_obs
    [earth_utc, earth_ets, earth_clon, earth_hdis] = earth_obs
    

    earth_src = np.zeros(len(earth_utc)) + 2    # src: 0 RSW, 1 LLD, 2 HMI
    solo_src  = np.zeros(len(solo_utc))  + 1    # src: 0 RSW, 1 LLD, 2 HMI


    utc   = np.concatenate([solo_utc,  earth_utc])
    ets   = np.concatenate([solo_ets,   earth_ets])
    clons = np.concatenate([solo_clon, earth_clon])
    hdis  = np.concatenate([solo_hdis, earth_hdis])
    src   = np.concatenate([solo_src,  earth_src])


    # The resulting array contains the et ordered solo values before the earth values
    # This has to be ordered for increasing et again. The new order is determined with
    # the np.argsort function and applied to all 5 arrays

    order = np.argsort(ets)

    utc   = utc[order]
    ets   = ets[order]
    clons = clons[order]
    hdis  = hdis[order]
    src   = src[order]

    #return [utc, ets, src, order]

    #start_time = "1 January 2022 00:00 (UTC)"   # LTP05 during high omega CR2256 start time
    dt = np.array([])

    coverage       = np.zeros(360)
    coverage_src   = np.zeros(360)
    coverage_track = []

    # New version cannot iterate over general ets since there are entries
    # for different INTERPOLATED ets for solo and hmi. Therefore, 
    # merge solo_obs and earth_obs while tracking the obsevation source
    # (add src array = 2 to earth_obs) and then iterate over all ets
    # until the map is full. Discard remaining data once the map is full.
    
    # Maybe save single spacecraft coverage history for separate use?
    # This also provides a temporal evolution of the synoptic map creation
    # and can be used for future animations and the clon source plot
    # Then create a nice clon source plot and a script for the temporal
    # evolution with single frames for each observation

    prev_eclon = None # tracks the last observed carrington longitude from earth
    prev_sclon = None # tracks the last observed carrington longitude from solo

    for i, et in enumerate(ets):
        #print(i, clons[i], src[i])
        coverage_src   = np.zeros(360)-1

        clon = int(clons[i])
        if src[i] < 2:
            prev_clon = prev_sclon
        else:
            prev_clon = prev_eclon

        #print(i, et, coverage)

        if prev_clon is None:
            coverage[clon] = 1
            coverage_src[clon] = src[i]
            coverage_track.append(coverage_src)

            #print(i, et, eclon, eclon, sclon, sclon, np.sum(coverage))
            if src[i] < 2:
                prev_sclon = clon
            else:
                prev_eclon = clon

        else:
            # observation in decreasing clon. prev_clon > clon
            # prev_clon - clon < 0 indicates a jump from low to high longitudes
            if prev_clon - clon < 0:
                coverage[0:prev_clon] = 1       # fill up the lower longitudes since previous clon
                coverage[clon:] = 1             # fill up the high lontitudes from the current clon to the end
                                                # this can probably be converage[clon:] instead of :361

                coverage_src[0:prev_clon] = src[i] # I don't think +1 is required: coverage_src[0:prev_clon+1] = src[i]
                coverage_src[clon:] = src[i]
                coverage_track.append(coverage_src)

                if src[i] < 2:
                    prev_sclon = clon
                else:
                    prev_eclon = clon
            
            # WRONG! hitting zero completes the entire map
            #elif prev_clon == 0: # this would probably work wiht the previous case as long as [0:0] doesn't raise an error
            #    coverage[clon:] = 1

            #    coverage_src[clon:] = src[i]
            #    coverage_track.append(coverage_src)

            #    if src[i] < 2:
            #        prev_sclon = clon
            #    else:
            #        prev_eclon = clon

            else:
                coverage[clon:prev_clon] = 1

                coverage_src[clon:prev_clon] = src[i]
                coverage_track.append(coverage_src)

                if src[i] < 2:
                    prev_sclon = clon
                else:
                    prev_eclon = clon
                    
        # prev_sclon and prev_eclon separation is kinda pointless in here
        print(i, et, clon, prev_eclon, clon, prev_sclon, np.sum(coverage))


        if np.sum(coverage) == 360:
            dt = np.append(dt, (et - ets[0])/86400) # days
            print('FSM Creation Time: %s days'% np.round(dt[0],2))
            nobs =len(coverage_track)
            return coverage, coverage_track, utc, ets, clons, hdis, src, order, nobs


        
    nobs =len(coverage_track)
    return coverage, coverage_track, utc, ets, clons, hdis, src, order, nobs


    if False:
        fig, ax = plt.subplots()
        ax.scatter(range(len(coverage_src)), coverage_src)#, label='HMI')
        #ax.scatter(range(len(coverage_solo)),  coverage_solo,  label='PHI')
        ax.set_xlabel('Carrington Longitude')
        ax.set_ylabel('Coverage')
        
        #handles, labels = ax.get_legend_handles_labels()
        #ax.legend(handles, labels)
        plt.show()
    
    

def carrington_observation_duration(solo_clon, earth_clon, ets):

    # carrington_observation_coverage concatenates solo and earth data and then
    # processes everything in one go instead of doing it separately for earth
    # and solo like in here

    #start_time = "1 January 2022 00:00 (UTC)"   # LTP05 during high omega CR2256 start time
    dt = np.array([])
    dt_date = np.array([], dtype='datetime64[s]')
    
    for t0_index, t0 in enumerate(ets):

        coverage = np.zeros(360)
        
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

                else:
                    coverage[sclon:prev_sclon] = 1
                    prev_sclon = sclon
                
            else:
                coverage[eclon] = 1
                coverage[sclon] = 1

                prev_eclon = eclon
                prev_sclon = sclon

            #print(i, et2datetime64(et), eclon, prev_eclon, sclon, prev_sclon, np.sum(coverage))

            if np.sum(coverage) == 360:
                t = ets[t0_index+i]
                dt = np.append(dt, (t - t0)/86400) # days
                dt_date = np.append(dt_date, et2datetime64(t0)[0]) #sp.et2utc(t0, 'C', 3))
                #return dt, dt_date
                break # leave inner for and continue with outer for

    print('min creation time: ', np.min(dt))
    print('max creation time: ', np.max(dt))
    print('avg creation time: ', np.average(dt))
    
    #fsm_dates = np.where(dt < 16.5)[0]

    """
    #fsm_dates = np.where(dt[fsm_dates] >14)[0]
    
    #for i in fsm_dates:
        #print(dt_date[i], dt[i])
    # 5+ to start at ltp 5 / *2 since ltp are half yearly
    ltp = 5+(ets[ii:ii+len(dt)]-ets[ii])/86400/365 * 2

    fig, ax = plt.subplots(figsize=(16,9), linewidth=20, edgecolor='#930534')
    ax.plot(ltp, dt, color='#003247', linewidth=4)  #003247 930534

    text_style = dict(fontsize=14)

    ax.set_title('Synoptic Map Observation Duration', y=1.05, fontsize=20)
    ax.set_xlabel('LTP Period',**text_style)
    ax.set_ylabel('Completion Time [Days]',**text_style)

    ax.tick_params(labelsize=12)

    ax.xaxis.labelpad=10
    ax.yaxis.labelpad=10

    fig.subplots_adjust(left=0.1,right=0.9,top=0.85,bottom=0.15)
    #plt.savefig('./plots/fsm_observation_duration.png', dpi=120, edgecolor=fig.get_edgecolor())
    #np.savetxt('./plots/fsm_observation_duration.txt', np.array([ltp, dt]).T, delimiter=',', comments='# LTP, DT')
    
    """

    return dt, dt_date


def optimise_carringtion_observation(et_bounds, ets, dt_date, dt):

    # calculate the start date for the fastest carrington map for each carrington rotation

    #single index and integer et to prevent ERFA warnings for astropy time objects used in carrington_rotation_number()
    crot_start = int(carrington_rotation_number(et2datetime64(int(et_bounds[0]))[0]))
    crot_end   = int(carrington_rotation_number(et2datetime64(int(et_bounds[1]))[0]))
    crots      = np.arange(crot_start, crot_end+1)

    crot_times = [np.datetime64(time) for time in carrington_rotation_time(crots).datetime]
    crot_ets   = [datetime642et(time) for time in crot_times]
    diff = len(ets)-len(dt)

    # test = {}
    # test[2240] = {"date": 123, "clon": 1234, "src": "hmi"}

    opt_obs = pd.DataFrame(index=range(crot_start, crot_end), columns=["start_date", "obs_time"])
    opt_obs.index.name = "carrington rotation"

    for t0, t1, crot in zip(crot_ets[:-1], crot_ets[1:], crots):
        # Boolean mask for values between t0 and t1
        # ets interval at same cadence ::cad as used in carrington_rotation_coverage()
        mask = (ets[:-diff] >= t0) & (ets[:-diff] <= t1)

        # Extract indices of current crot
        indices = np.where(mask)[0]

        # find minimum in the current crot range
        imin = np.argwhere(dt[indices] == np.min(dt[indices]))[0][0]

        opt_obs.loc[crot] = [dt_date[indices][imin], np.round(np.min(dt[indices]),2)]

    return opt_obs


#def main():
if __name__ == "__main__":
    # List of config parameters
    # et_resolution
    # 
    # Set cwd to file directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    #config = Config(config_path='/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/src/config.yaml')
    config = Config(config_path='config.yaml')

    # Load meta kernel
    loaded=loadkernel(config.spice_mkpath, config.spice_mkname)
 
    AU = 149598000.0 #km
    et_resolution = 3600

    et_bounds=get_solo_coverage(config.spice_mkpath) # ET timestamps over entire SolO mission

    ets = np.arange(et_bounds[0],et_bounds[1],et_resolution)
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
    #earth_hlat = earth_hlat*sp.dpr() # unused, but could be used for further calculations

    #delta_omega_solo  = calc_relative_rotation(solo_HCI_state)
    #delta_omega_earth = calc_relative_rotation(earth_HCI_state)
    #delta_omega = delta_omega_solo

    solo_clon  = simple_carrington(solo_hlon, ets)
    earth_clon = simple_carrington(earth_hlon, ets)


    #t_obs = np.datetime64("2022-06-09T09:00:39")
    #et_tobs = datetime642et(t_obs)[0]
    #i_tobs = np.searchsorted(ets, et_tobs)
    #solo_clon[i_tobs]

    #t_rec = np.datetime64("2022-06-24T06:56:58")
    #et_trec = datetime642et(t_rec)[0]
    #i_trec = np.searchsorted(ets, et_trec)
    #earth_clon[i_trec]

    solo_cad  = 4 # observation cadence in hours
    earth_cad = 4
    #dt, dt_date = carrington_observation_duration(solo_clon, earth_clon, solo_hdis, ets, et_bounds[0], cad)
    dt, dt_date = carrington_observation_duration(solo_clon, earth_clon, ets)  

    opt_obs = optimise_carringtion_observation(et_bounds, ets, dt_date, dt)

    print(opt_obs)

    # times are only for a single carrington rotation
    #fsm_start = "2024-01-01T00:00:00"
    fsm_start = opt_obs.loc[2239]["start_date"]
    earth_obs = carrington_observation_times(earth_clon, earth_hdis, ets, fsm_start, earth_cad)
    solo_obs  = carrington_observation_times(solo_clon,   solo_hdis, ets, fsm_start, solo_cad)
    [coverage, track, utc, et, clons, hdis, src, order, n] = carrington_observation_coverage(solo_obs, earth_obs, plot=False)


    # TODO 
    # - create separate DRMS timestrings for HMI and PHI part
    # - make sure to do the TAI conversion 
    #
    # - refactor carrington observation functions and export the clon linearisation
    # - add centi clon support for coverage calculation for compatibility with MIP implementation
    # - use observation duration output and find best combination for each carrington rotation
    # - identify config parameters for export

    # - current workflow:
    #   - run carrington_observation_duration to find best start date
    #   - run carrington_observation_coverage for that start date

    #   - convert solo2earth_times in prepartion for DRMS
    #   - convert obs2drms_times for UTC to TAI conversion with DRMS compatible time string format



#if __name__ == "__main__":
#    main()

    """
    Design:
    - find best combination from existing data
        - from two continously running observations (HMI and PHI)
        - constrained within a single CR to improve HMI maps
        - arbitrary start and end dates crossing CR boundaries for fastest possible combination

    - find best combination at defined cadence for a future time window for mission planning

    
    t_obs = datetime642et(np.datetime64('2022-06-09T09:00:39'))
    iclon = np.searchsorted(ets, t_obs)[0]
    solo_clon[iclon]

    # Get all objects (targets) in loaded SPK kernels
    objects = sp.spkobj("")  # empty string returns all loaded SPK objects

    for obj in objects:
        # Number of segments for this object in loaded kernels
        nseg = sp.spkntf("", obj)  # empty string = all loaded SPKs
        for i in range(nseg):
            # Get segment descriptor and ID
            descr, segid = sp.spkpars("", obj, i)
            start_et, stop_et = descr[0], descr[1]

            # Sample timestamps to estimate resolution
            sample_times = np.linspace(start_et, stop_et, 1000)
            deltas = np.diff(sample_times)
            min_delta = np.min(deltas)

            print(f"Object {obj}, Segment '{segid}': approx resolution = {min_delta:.3f} s")
    """


    """
    sp.furnsh("./kernels/meta_kernel.tm")

    # Define observation time
    et = sp.str2et("2025-07-10T00:00:00")

    # Get position of observer relative to Sun in J2000
    pos_earth, _ = sp.spkpos("EARTH", et, "J2000", "LT+S", "SUN")
    pos_solo, _ = sp.spkpos("SOLAR ORBITER", et, "J2000", "LT+S", "SUN")

    # Normalize to Sun's surface (unit vector * radius)
    R_sun_km = 696000.0
    sub_earth = np.array(pos_earth) / np.linalg.norm(pos_earth) * R_sun_km
    sub_solo = np.array(pos_solo) / np.linalg.norm(pos_solo) * R_sun_km

    # Compute planetographic longitude (west positive), latitude, radius
    lon_earth, lat_earth, _ = sp.reclat(sub_earth)
    lon_solo, lat_solo, _ = sp.reclat(sub_solo)

    # Convert to degrees and normalize to 0–360
    lon_earth_deg = np.degrees(lon_earth) % 360
    lon_solo_deg = np.degrees(lon_solo) % 360

    # Get Carrington longitude of central meridian at 'et'
    sun_rotation = sp.bodvrd("SUN", "LONG_AXIS", 1)  # returns [0.0]
    _, l0_arr = sp.bodvrd("SUN", "PM", 3)  # PM = [W0, W_dot, epoch]
    W0, W_dot, t_epoch = l0_arr

    # Carrington rotation rate (degrees/day): ~14.1844 deg/day
    # Convert to degrees/sec
    carr_rate_deg_per_sec = 14.1844 / (24*3600)
    d_et = et - sp.str2et("2000-01-01T12:00:00")   # seconds since J2000

    L0 = (W0 + W_dot * (et - t_epoch)) % 360

    # Carrington longitude seen by each observer = (L0 - lon_west) % 360
    # But SPICE longitudes are usually EAST positive => need to convert
    def carrington_longitude(lon_east_deg, L0_deg):
        lon_west_deg = (360 - lon_east_deg) % 360
        return (L0_deg - lon_west_deg) % 360

    lon_carr_earth = carrington_longitude(lon_earth_deg, L0)
    lon_carr_solo = carrington_longitude(lon_solo_deg, L0)

    # Output
    utc_time = sp.et2utc(et, 'ISOC', 0)
    print(f"Carrington longitude from Earth at {utc_time}: {lon_carr_earth:.2f}°")
    print(f"Carrington longitude from Solar Orbiter at {utc_time}: {lon_carr_solo:.2f}°")

    # Unload kernels after use
    sp.kclear()
    """