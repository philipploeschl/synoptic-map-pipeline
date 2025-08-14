import spiceypy as spice
import spiceypy.utils.support_types as stypes
import numpy as np
import os, sys
from pathlib import Path
from config.config import Config


def loadkernel(kpath, kname):
    "This function loads a SPICE kernel (which could be a metakernel) then returns to the current working directory."
    cur_wd = os.getcwd()
    os.chdir(kpath)
    spice.furnsh(kpath+kname)
    os.chdir(cur_wd)
    nloaded = spice.ktotal("ALL")
    return(nloaded)
    
def unloadkernel(kpath,kname):
    "This function unloads a SPICE kernel (which could be a metakernel) then returns to the current working directory."
    cur_wd = os.getcwd()
    os.chdir(kpath)
    spice.unload(kname)
    os.chdir(cur_wd)
    nloaded = spice.ktotal("ALL")
    return(nloaded)
    
def get_solo_coverage(mkpath):
    "This function simply returns the coverage of the loaded Solar Orbiter orbit kernel."
    for kernel in range(0,spice.ktotal("ALL")-1):
        kernel_data=spice.kdata(kernel,"ALL")
        if "solo_ANC_soc-orbit" in kernel_data[0]:
            solo_coverage = stypes.SPICEDOUBLE_CELL(2)
            kernel_path = os.path.join(mkpath, kernel_data[0])
            #kernel_path = kernel_data[0]
            spice.spkcov(kernel_path,-144,solo_coverage) #-144 is the NAIF ID for Solar Orbiter
            coverage_out=spice.wnfetd(solo_coverage,0)
            return(coverage_out)
    else:
        raise ValueError("No Solar Orbiter orbit kernel found in loaded kernels.")

def get_orbit_coverage(kernel_path, kernel_name, obj_id):
    "This function simply returns the coverage of the given orbit kernel."
    orbit_coverage = stypes.SPICEDOUBLE_CELL(200)
    kernel_path = os.path.join(kernel_path,kernel_name)
    spice.spkcov(kernel_path,obj_id,orbit_coverage)
    coverage_out=spice.wnfetd(orbit_coverage,0)
    return(coverage_out)

def calc_relative_rotation(hci_state):
    
    omega_a = 14.713*spice.rpd()/86400.0
    omega_b = -2.316*spice.rpd()/86400.0
    omega_c = -1.787*spice.rpd()/86400.0

    delta_omega = []

    for (index, item) in enumerate(hci_state[:,0]):
        [void1,void2,lat] = spice.reclat(hci_state[index,0:3])
        omega_sun = omega_a + omega_b*(np.sin(lat)**2) + omega_c*(np.sin(lat)**4)
        omega_sun_d_per_d = omega_sun*spice.dpr()*86400.0
        (r_norm, r_mag) = spice.unorm(hci_state[index,0:3])
        omega_solo = np.cross(hci_state[index,0:3],hci_state[index,3:6])/(r_mag**2)
        omega_solo_d_per_d = omega_solo[2]*spice.dpr()*86400.0
        delta_omega.append(omega_sun_d_per_d-omega_solo_d_per_d)
    return(delta_omega)

def simple_carrington(hci_lon, ets):
    
    rotation_period = 25.38
    base_time = "20 December 2018 11:47 (UTC)"

    omega = (2*np.pi)/(rotation_period*86400.0)
    t0 = spice.str2et(base_time)
    (basepos, ltime) = spice.spkpos("EARTH", t0, "SUN_INERTIAL","NONE","SUN")
    (baserad,baselon,baselat) = spice.reclat(basepos)
    baselon2 = (baselon*spice.dpr()+360.0) % 360
    
    clon = []
    for (index, et) in enumerate(ets):
        delta_t = et - t0
        delta_phi = (delta_t*omega*spice.dpr()) % 360
        zero_lon = (baselon2+delta_phi) % 360
        solo_lon = (hci_lon[index]*spice.dpr()+360) % 360
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
        utc_string=spice.et2utc(et,"ISOC",3)
        outtime.append(np.datetime64(utc_string,"ms"))
    return(outtime)


def datetime642et(dts):
    outets = []
    timstr = np.datetime_as_string(dts,unit="ms")
    if isinstance(timstr,str):
        timstr=[timstr]
    for time in timstr:
        outet=spice.utc2et(time)
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

    t0 = sp.str2et(start_time)                  # convert start_time to et
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
    
    if False:
        print('###### RESULTS ######')
        output = np.column_stack((obs_utc, obs_clon, obs_dist))
        print(output)

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




#def main():
if __name__ == "__main__":
    # Set cwd to file directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    config = Config(config_path='/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/src/config.yaml')
    
    # Load meta kernel
    loaded=loadkernel(config.spice_mkpath, config.spice_mkname)
 
    AU = 149598000.0 #km
    et_resolution = 3600

    et_bounds=get_solo_coverage(config.spice_mkpath) # ET timestamps over entire SolO mission

    ets = np.arange(et_bounds[0],et_bounds[1],et_resolution)
    ets[len(ets)-1]=et_bounds[1]

    # get spacecraft state vector with spkezr, returns (position [km] and velocity [km/s]) and light time (one-way light time in seconds)
    [solo_GSE_pos, ltime]    = spice.spkpos("SOLO", ets,"SOLO_GSE","NONE","EARTH")  
    [solo_HCI_state, ltime]  = spice.spkezr("SOLO", ets,"SUN_INERTIAL","NONE","SUN") 
    [earth_HCI_state, ltime] = spice.spkezr("EARTH",ets,"SUN_INERTIAL","NONE","SUN")

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
        [earth_hdis[i], earth_hlon[i], earth_hlat[i]] = spice.reclat(earth_HCI_pos[i,:])
        [solo_hdis[i],  solo_hlon[i],  solo_hlat[i]]  = spice.reclat(solo_HCI_pos[i,:])

    solo_hdis = solo_hdis/AU
    solo_hlat = solo_hlat*spice.dpr()

    earth_hdis = earth_hdis/AU
    #earth_hlat = earth_hlat*spice.dpr() # unused, but could be used for further calculations

    delta_omega_solo  = calc_relative_rotation(solo_HCI_state)
    delta_omega_earth = calc_relative_rotation(earth_HCI_state)
    delta_omega = delta_omega_solo

    solo_clon = simple_carrington(solo_hlon,ets)
    earth_clon = simple_carrington(earth_hlon, ets)

    t_obs = np.datetime64("2022-06-09T09:00:39")
    et_tobs = datetime642et(t_obs)[0]
    i_tobs = np.searchsorted(ets, et_tobs)
    solo_clon[i_tobs]

    t_rec = np.datetime64("2022-06-24T06:56:58")
    et_trec = datetime642et(t_rec)[0]
    i_trec = np.searchsorted(ets, et_trec)
    earth_clon[i_trec]

    #- CONTINUE WITH UNDERSTANDING carrington_observation_coverage 

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
    objects = spice.spkobj("")  # empty string returns all loaded SPK objects

    for obj in objects:
        # Number of segments for this object in loaded kernels
        nseg = spice.spkntf("", obj)  # empty string = all loaded SPKs
        for i in range(nseg):
            # Get segment descriptor and ID
            descr, segid = spice.spkpars("", obj, i)
            start_et, stop_et = descr[0], descr[1]

            # Sample timestamps to estimate resolution
            sample_times = np.linspace(start_et, stop_et, 1000)
            deltas = np.diff(sample_times)
            min_delta = np.min(deltas)

            print(f"Object {obj}, Segment '{segid}': approx resolution = {min_delta:.3f} s")
    """


    """
    spice.furnsh("./kernels/meta_kernel.tm")

    # Define observation time
    et = spice.str2et("2025-07-10T00:00:00")

    # Get position of observer relative to Sun in J2000
    pos_earth, _ = spice.spkpos("EARTH", et, "J2000", "LT+S", "SUN")
    pos_solo, _ = spice.spkpos("SOLAR ORBITER", et, "J2000", "LT+S", "SUN")

    # Normalize to Sun's surface (unit vector * radius)
    R_sun_km = 696000.0
    sub_earth = np.array(pos_earth) / np.linalg.norm(pos_earth) * R_sun_km
    sub_solo = np.array(pos_solo) / np.linalg.norm(pos_solo) * R_sun_km

    # Compute planetographic longitude (west positive), latitude, radius
    lon_earth, lat_earth, _ = spice.reclat(sub_earth)
    lon_solo, lat_solo, _ = spice.reclat(sub_solo)

    # Convert to degrees and normalize to 0–360
    lon_earth_deg = np.degrees(lon_earth) % 360
    lon_solo_deg = np.degrees(lon_solo) % 360

    # Get Carrington longitude of central meridian at 'et'
    sun_rotation = spice.bodvrd("SUN", "LONG_AXIS", 1)  # returns [0.0]
    _, l0_arr = spice.bodvrd("SUN", "PM", 3)  # PM = [W0, W_dot, epoch]
    W0, W_dot, t_epoch = l0_arr

    # Carrington rotation rate (degrees/day): ~14.1844 deg/day
    # Convert to degrees/sec
    carr_rate_deg_per_sec = 14.1844 / (24*3600)
    d_et = et - spice.str2et("2000-01-01T12:00:00")   # seconds since J2000

    L0 = (W0 + W_dot * (et - t_epoch)) % 360

    # Carrington longitude seen by each observer = (L0 - lon_west) % 360
    # But SPICE longitudes are usually EAST positive => need to convert
    def carrington_longitude(lon_east_deg, L0_deg):
        lon_west_deg = (360 - lon_east_deg) % 360
        return (L0_deg - lon_west_deg) % 360

    lon_carr_earth = carrington_longitude(lon_earth_deg, L0)
    lon_carr_solo = carrington_longitude(lon_solo_deg, L0)

    # Output
    utc_time = spice.et2utc(et, 'ISOC', 0)
    print(f"Carrington longitude from Earth at {utc_time}: {lon_carr_earth:.2f}°")
    print(f"Carrington longitude from Solar Orbiter at {utc_time}: {lon_carr_solo:.2f}°")

    # Unload kernels after use
    spice.kclear()
    """