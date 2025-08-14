import spiceypy as spice
import spiceypy.utils.support_types as stypes
import numpy as np
import os, sys

import config


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


def main():
    # Set cwd to file directory
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

    # Load meta kernel
    loaded=loadkernel(config.spice_mkpath, config.spice_mkname)
 
    AU = 149598000.0

    et_bounds=get_solo_coverage(config.spice_mkpath) # ET timestamps over entire SolO mission

    ets = np.arange(et_bounds[0],et_bounds[1],21600)
    ets[len(ets)-1]=et_bounds[1]

    # get spacecraft state vector with spkezr, returns (position [km] and velocity [km/s]) and light time (one-way light time in seconds)
    [solo_GSE_pos, ltime]    = spice.spkpos("SOLO",ets,"SOLO_GSE","NONE","EARTH")  
    [solo_HCI_state, ltime]  = spice.spkezr("SOLO",ets,"SUN_INERTIAL","NONE","SUN") 
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

    print(solo_clon[0])



if __name__ == "__main__":
    main()


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