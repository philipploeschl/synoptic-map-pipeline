import os, sys, subprocess
import config
import numpy as np
from scipy import interpolate
from astropy.io import fits
#from astropy.time import Time, TimeDelta, TimeDatetime
from datetime import datetime, timedelta
from sunpy.coordinates.sun import carrington_rotation_time
from misc import run_script_with_nohup, get_current_session_folder, add_script_header, add_check_continue, get_phi_filenames

# Create DRMS compatible FITS header

def calc_trec(crln_obs, car_rot, verbose=False):
    # helper function to prepare hmi data for interp_phi2hmi() interpolation

    # remap and >180 means that HMI_PAST is the previous CAR_ROT and HMI_FUTR is the current CAR_ROT
    # remap and <180 means that HMI_FUTR is the current CAR_ROT and HMI_PAST is the previous CAR_ROT
    
    # TODO WHY IS THIS HARD CODED HERE?
    car_rot = 2258
    
    # THIS IS LOGIC DOESN'T MAKE SENSE FOR THE BOTTOM LEFT QUARTER OF OBSERVATIONS (ORBIT_PLOTS)
    if False:# crln_obs > 180:
        # t defined by when HMI sees it (future/past)
        #t0 = carrington_rotation_time(car_rot-1) # past / current
        #t1 = carrington_rotation_time(car_rot)   # future
        
        t0 = carrington_rotation_time(car_rot-1) # past / current CAR_ROT
        t1 = carrington_rotation_time(car_rot)   # future
        t2 = carrington_rotation_time(car_rot+1) # future end point
        
        trec_hmi = interp_phi2hmi(crln_obs, t0, t1, verbose)
        hmi_next = interp_phi2hmi(crln_obs, t1, t2)
        hmi_prev = trec_hmi
        car_rot -= 1
        
    else:
        t0 = carrington_rotation_time(car_rot-1) # past  
        t1 = carrington_rotation_time(car_rot)   # future / current
        t2 = carrington_rotation_time(car_rot+1) # future end point

        trec_hmi = interp_phi2hmi(crln_obs, t1, t2, verbose, car_rot)
        hmi_prev = interp_phi2hmi(crln_obs, t0, t1)
        hmi_next = trec_hmi
        
    #print(trec_hmi, hmi_prev, hmi_next, crln_obs, car_rot)
    return trec_hmi, hmi_prev, hmi_next, car_rot

"""
def calc_trec_rev(crln_obs, car_rot, verbose=False):
    # helper function to prepare hmi data for interp_phi2hmi() interpolation

    # remap and >180 means that HMI_PAST is the previous CAR_ROT and HMI_FUTR is the current CAR_ROT
    # remap and <180 means that HMI_FUTR is the current CAR_ROT and HMI_PAST is the previous CAR_ROT
    
    t0 = carrington_rotation_time(car_rot-1) # past / current CAR_ROT
    t1 = carrington_rotation_time(car_rot)   # future
    t2 = carrington_rotation_time(car_rot+1) # future end point
    
    # THIS IS LOGIC DOESN'T MAKE SENSE FOR THE BOTTOM LEFT QUARTER OF OBSERVATIONS (ORBIT_PLOTS)
    if crln_obs > 180:
        # t defined by when HMI sees it (future/past)
        #t0 = carrington_rotation_time(car_rot-1) # past / current
        #t1 = carrington_rotation_time(car_rot)   # future
    
        trec_hmi = interp_phi2hmi(crln_obs, t0, t1, verbose)
        hmi_next = interp_phi2hmi(crln_obs, t1, t2)
        hmi_prev = trec_hmi
        car_rot -= 1
        
    else:
        
        trec_hmi = interp_phi2hmi(crln_obs, t1, t2, verbose)
        hmi_prev = interp_phi2hmi(crln_obs, t0, t1)
        hmi_next = trec_hmi
        
    print(trec_hmi, hmi_prev, hmi_next, crln_obs, car_rot)
    return trec_hmi, hmi_prev, hmi_next, car_rot
"""


def interp_phi2hmi(crln_obs, t0, t1, verbose=False, car_rot=None):
    # Interpolate T_REC of PHI CRLN_OBS onto HMI CRLN_OBS
    dt_hmi   = np.array([])
    trec_hmi = np.array([])
    crln_hmi = np.array([])

    hmi_times = "%s-%s" %(t0.datetime.strftime("%Y.%m.%d_%H:%M:%S_TAI"), t1.datetime.strftime("%Y.%m.%d_%H:%M:%S_TAI"))
    hmi_data, n = get_drms_keywords(hmi_times, "hmi.m_720s") #"mps_loeschl.Ml_remap_720s")
    
    #print('Mapping PHI to CR %s in HMI period %s...\n' %(car_rot, hmi_times))

    for line in hmi_data:
        # CRLN_OBS will be NaN if no observation is available for a timeslot -> nan filter required
        if np.isnan(float(line['CRLN_OBS'])): continue 
        
        trec_hmi = np.append(trec_hmi, datetime.strptime(line['T_REC'], "%Y.%m.%d_%H:%M:%S_TAI"))
        dt_hmi   = np.append(dt_hmi, ((trec_hmi[-1] - t0.datetime).days +(trec_hmi[-1] - t0.datetime).seconds/(3600*24)))    
        crln_hmi = np.append(crln_hmi, float(line['CRLN_OBS']))

    # Interpolation fails if the HMI onto which I want to map is not complete yet!
    # this will happen whenever we try to preview ongoing carrington rotations
    # the timeslot interpolation must be based on an extrapolation for the remaining HMI time slots/clrn obs
    
    # extrapolation if trec_hmi[-1]-trec_hmi[0] < 1 month
    crd = t1-t0 # carrington rotation duration
    
    hmi_end = datetime.strptime(hmi_data[-1]['T_REC'], "%Y.%m.%d_%H:%M:%S_TAI")
    dt = (hmi_end-t0.datetime).days +(hmi_end-t0.datetime).seconds/(3600*24)
    tstep = timedelta(minutes=12)
    
    # Extrapolation of T_REC/CRLN_OBS in 12 minute steps
    if dt < crd:
        crln_fit = interpolate.interp1d(dt_hmi, crln_hmi, fill_value = "extrapolate")
        nsteps = np.ceil(((crd-dt)*(24*3600)).value/720).astype(int) # difference in seconds
        
        for i in range(1, nsteps):
            #hmi_data.append({'T_REC':(hmi_end+i*tstep).strftime("%Y.%m.%d_%H:%M:%S_TAI"), 'CRLN_OBS':crln_fit[i-1], 'CAR_ROT':hmi_data[0]['CAR_ROT']})
            dt_hmi   = np.append(dt_hmi, (((hmi_end+i*tstep) - t0.datetime).days +((hmi_end+i*tstep) - t0.datetime).seconds/(3600*24)))    
            trec_hmi = np.append(trec_hmi, (hmi_end+i*tstep).strftime("%Y.%m.%d_%H:%M:%S_TAI"))
            
            crln =  crln_fit(dt_hmi[-1])
            if crln < 0: crln += 360
            crln_hmi = np.append(crln_hmi, crln)
    
    t_interp = timedelta(days=np.interp(crln_obs, crln_hmi, dt_hmi, period=360))
    trec_phi = t0.datetime+t_interp
    trec_hmi = trec_phi.strftime("%Y.%m.%d_%H:%M:%S_TAI")
    
    if verbose: print('Mapping PHI observation of CRLN %.2f to HMI T_REC %s during CR%s...\n' %(crln_obs, trec_hmi, car_rot))
    
    return trec_hmi
    

def get_drms_keywords(inRecs, input_ds):

    #inRecs = "2014.05.12_12:00:00_TAI, 2014.05.13_00:00:00_TAI, 2014.05.13_12:00:00_TAI, 2014.05.14_00:00:00_TAI" # input argument
    show_info = 'show_info %s["%s"] key="T_REC,CRLN_OBS,CAR_ROT"'
    
    #-P for path and -A for segment
    si_out = subprocess.check_output(show_info %(input_ds, inRecs) , shell=True)[:-1].decode("utf-8")
    raw = si_out.split('\n')

    formatted = [] 
    drms_param = []
    
    nRecs = 0
    keys = raw[0].split('\t')
    
    for line in raw[1:]:  
        formatted = line.split('\t') # [CALVER64, T_REC, QUALITY, FDRADIAL, CARSTRCH, DIFROT_A, DIFROT_B, DIFROT_C, CRVAL1, CRLN_OBS, CAR_ROT, MAPLGMAX, MAPLGMIN, I_DREC]

        dict_tmp = {}

        for i, key in enumerate(keys):
            
            if key == "magnetogram" or key == 'Ml':
                key = "PATH"
                
            if formatted[i].strip() == "InvalidKeyname":
                dict_tmp[key] = 0
            else:
                dict_tmp[key] = formatted[i]
   
        drms_param.append(dict_tmp)
        nRecs += 1

    return drms_param, nRecs



def main():

    #TODO 
    # - clean up old code
    # - why is car_rot hard coded in calc_trec()?

    #set cwd to file directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    session_folder = get_current_session_folder()
    outpath_scripts = os.path.join(session_folder, config.script_path)
    outpath_data    = os.path.join(session_folder, config.data_path)
    #outpath_logs    = os.path.join(session_folder, config.log_path)


    # old config.phi_datapath implementation
    #files = os.listdir(config.phi_datapath)
    #fitsfiles = [file for file in files if file.endswith(".fits") or file.endswith(".fits.gz")]

    fitsfiles = get_phi_filenames(config.phi_dbpath, config.date_start, config.date_end, config.key, config.verbose)

    if fitsfiles[0].endswith(".fits"):
        n_end = 5
    else:
        n_end = 8

    trecs = []
    clons = []

    for file in fitsfiles:
        #l2 = fits.open(config.phi_datapath+file) # old version wihtout direct fmdb access
        l2 = fits.open(os.path.join(config.phi_dbpath,file))
        if config.verbose: print("Processing %s ..." %file)
        
        prim = fits.PrimaryHDU()
        l2drms = fits.CompImageHDU(data=l2[0].data.astype(np.int32))

        # open updated source file
        l2drms.header.append(('', '', ''), end=True)
        l2drms.header.append(('', '  / HMI Compatibility', ''), end=True)
        
        # TODO TEMPORARY: Fix CAR_ROT bug, figure out what's going on for production version
        if l2[0].header['CAR_ROT'] == 2239: 
            l2[0].header['CAR_ROT'] = 2240
        
        if l2[0].header['CRLN_OBS'] == 358.80689 and l2[0].header['CAR_ROT'] == 2240:
            l2[0].header['CAR_ROT'] = 2241
        
        # T_REC / T_OBS
        #DATE-AVG= '2021-02-05T20:00:45.616' / [UTC] Average time of observation     
        #T_OBS   = '2021.02.28_07:11:55.437_TAI' / [TAI] nominal time 
        #T_REC   = '2021.02.28_07:12:00.000_TAI' / [TAI] Slot time    
        # Conversion for date format / UTC to TAI / round to the next 12 minute slot for T_REC
        #trec = datetime.strptime(l2[0].header['DATE-AVG'],   "%Y-%m-%dT%H:%M:%S.%f")
        tobs = datetime.strptime(l2[0].header['DATE-AVG'],   "%Y-%m-%dT%H:%M:%S.%f")
        
        #utc2tai = timedelta(0, 37)                 # use for utc2tai conversion
        #trec = trec + utc2tai                      # use for utc2tai conversion
        #trec = trec.strftime("%Y.%m.%d_%H:%M:%S_TAI")
        tobs = tobs.strftime("%Y.%m.%d_%H:%M:%S_TAI")

        # T_REC Interpolation     
        if config.verbose: print("True observation time during Carrington rotation %s: %s" %(l2[0].header['CAR_ROT'], tobs))  
        trec, hmi_prev, hmi_next, car_rot = calc_trec(float(l2[0].header['CRLN_OBS']), int(l2[0].header['CAR_ROT']), verbose=config.verbose)

        if config.verbose: print(trec, car_rot, l2[0].header['CRLN_OBS'])
        
        trecs.append(trec)
        clons.append(l2[0].header['CRLN_OBS'])
        
        l2drms.header.append(('T_REC', trec, ''), end=True)
        l2drms.header.append(('T_OBS', tobs, ''), end=True)  # required for JV2TS
        
        l2drms.header.append(('TRECEPOC', '1993.01.01_00:00:00_TAI', 'Time of origin'), end=True)
        l2drms.header.append(('TRECSTEP', 720.0,  'ts_eq step'), end=True)
        
        # these two keywords are redundant with T_REC and T_OBS
        l2drms.header.append(('HMI_PREV', hmi_prev, 'Previous HMI T_REC for this CRLN_OBS'), end=True) # HMI interpolated T_REC
        l2drms.header.append(('HMI_NEXT', hmi_next, 'Next HMI T_REC for this CRLN_OBS'), end=True) # real PHI observation date as backup
        
        # DATE
        l2drms.header.append(('DATE', l2[0].header['DATE'], "Date and time of FITS file creation, in UTC, in ISO-8601 format 'yyyy-mm-ddThh:mm:ss.sss'"), end=True)
        
        # DATE-OBS
        # DATE-BEG= '2021-02-05T20:00:02.906' / [UTC] Start time of observation 
        # DATE-OBS= '2021-02-28T07:10:33.400' / [ISO] Observation date {DATE__OBS}   
        # Conversion from BEG to OBS. Conversion from UTC to ISO
        date_obs = datetime.strptime(l2[0].header['DATE-BEG'],   "%Y-%m-%dT%H:%M:%S.%f")
        date_obs = date_obs.strftime("%Y.%m.%d_%H:%M:%S_TAI")
        l2drms.header.append(('DATE-OBS', date_obs, 'DATE-OBS = DATE-AVG - EXPTIME/2.0'), end=True)

        # CADENCE
        # Missing, directly copy from HMI as a dummy value or extract daily? cadence from filenames
        l2drms.header.append(('CADENCE', 720.0, '[seconds] Observation cadence - DUMMY VALUE'), end=True)
        
        # TELESCOP
        l2drms.header.append(('TELESCOP', l2[0].header['TELESCOP'], 'SOLO/PHI/FDT, SOLO/PHI/HRT, HMI: SDO/HMI'), end=True)
        
        # INSTRUME
        l2drms.header.append(('INSTRUME', l2[0].header['INSTRUME'], 'PHI, HMI_SIDE1, HMI_FRONT2, HMI_COMBINED'), end=True)
        
        # WAVELNTH
        l2drms.header.append(('WAVELNTH', 6173.341, 'For PHI/HMI: 6173.3 Angstroms'), end=True)
        
        # QUALITY
        # Missing. add as dummy value = 0. Quality index of data used to genrate fd.B_720s (0x00000000) is good quality, (any nonzero value) should be investiaged in data documentation
        l2drms.header.append(('QUALITY', 0, 'Level 1.5 Quality - DUMMY VALUE'), end=True)

        # BUNIT
        l2drms.header.append(('BUNIT', l2[0].header['BUNIT'], 'BUNIT: physical units of each data segment'), end=True)
        
        # HISTORY
        l2drms.header.append(('HISTORY', 'DRMS compatible FITS created from %s' %l2[0].header['FILENAME'], 'History of data'), end=True)
        
        # COMMENT
        #l2drms.header.append(('COMMENT', l2[0].header['COMMENT'], 'Commentary on the data'), end=True)
        
        # CTYPE1
        l2drms.header.append(('CTYPE1', l2[0].header['CTYPE1'], 'CTYPE1: HPLN-TAN (SOLARX)'), end=True)
        
        # CTYPE2
        l2drms.header.append(('CTYPE2', l2[0].header['CTYPE2'], 'CTYPE2: HPLN-TAN (SOLARY)'), end=True)
        
        #CRPIX1
        l2drms.header.append(('CRPIX1', l2[0].header['CRPIX1'], 'CRPIX1: location of the Sun center in CCD x direction'), end=True)
        
        #CRPIX2
        l2drms.header.append(('CRPIX2', l2[0].header['CRPIX2'], 'CRPIX2: location of the Sun center in CCD y direction'), end=True)
        
        #CRVAL1
        l2drms.header.append(('CRVAL1', l2[0].header['CRVAL1'], 'CRVAL1: x origin - center of the solar disk'), end=True)
        
        #CRVAL2
        l2drms.header.append(('CRVAL2', l2[0].header['CRVAL2'], 'CRVAL2: y origin - center of the solar disk'), end=True)
        
        #CDELT1
        l2drms.header.append(('CDELT1', l2[0].header['CDELT1'], 'Image scale in the x direction'), end=True)
        
        #CDELT2
        l2drms.header.append(('CDELT2', l2[0].header['CDELT2'], 'Image scale in the y direction'), end=True)
        
        #CUNIT1
        l2drms.header.append(('CUNIT1', l2[0].header['CUNIT1'], 'CUNIT1: arcsec'), end=True)
        
        #CUNIT2
        l2drms.header.append(('CUNIT2', l2[0].header['CUNIT2'], 'CUNIT2: arcsec'), end=True)
        
        # CROTA 
        # CROTA2
        # CROTA was renamed to CROTA2 in Dietmar's current L2 header. Rename here for now. CHECK IF THE ROTATION MAKES SENSE AFTER THE PROJECTION by comparing the projections of equal CRLN_OBS in PHI and HMI
        l2drms.header.append(('CROTA2', l2[0].header['CROTA'], '[deg] Rotation angle'), end=True)
        
        #CSYSER1
        #l2drms.header.append(('CSYSER1', l2[0].header['CSYSER1'], 'CSYSER1: estimate of systematic error in coordinate x'), end=True)
        
        #CSYSER2
        #l2drms.header.append(('CSYSER2', l2[0].header['CSYSER2'], 'CSYSER2: estimate of systematic error in coordinate y'), end=True)
        
        #WCSNAME
        l2drms.header.append(('WCSNAME', l2[0].header['WCSNAME'], 'WCS system name'), end=True)
        
        #DSUN_OBS
        l2drms.header.append(('DSUN_OBS', l2[0].header['DSUN_OBS'], 'Distance from SDO to Sun center.'), end=True)
        
        #RSUN_REF
        l2drms.header.append(('RSUN_REF', l2[0].header['RSUN_REF'], 'Reference radius of the Sun: 696,000,000.0 m'), end=True)
        
        #CRLN_OBS
        l2drms.header.append(('CRLN_OBS', l2[0].header['CRLN_OBS'], 'Carrington longitude of HMI'), end=True)
        
        #CRLT_OBS
        l2drms.header.append(('CRLT_OBS', l2[0].header['CRLT_OBS'], 'Carrington latitude of HMI'), end=True)
        
        #CAR_ROT        
        l2drms.header.append(('CAR_ROT', l2[0].header['CAR_ROT'], 'Carrington rotation number of CRLN_OBS'), end=True)
        l2drms.header.append(('CAR_ROT2', car_rot, 'Carrington rotation number of synoptic map'), end=True)
        
        # OBS_VW
        # OBS_VR
        # OBS_VN        
        l2drms.header.append(('OBS_VR', l2[0].header['OBS_VR'], '[m/s] Radial velocity of S/C relative to Sun   '), end=True)
        l2drms.header.append(('OBS_VW', l2[0].header['OBS_VW'], '[m/s] Westward velocity of S/C relative to Sun '), end=True)
        l2drms.header.append(('OBS_VN', l2[0].header['OBS_VN'], '[m/s] Northward velocity of S/C relative to Sun'), end=True)

        # RSUN_ARC
        # RSUN_OBS
        # Same keyword. Save RSUN_ARC as RSUN_OBS for HMI
        l2drms.header.append(('RSUN_OBS', l2[0].header['RSUN_ARC'], '[arcsec] angular radius of Sun.'), end=True)

        # DATAVALS
        # Actual number of data values in images (pixels)
        l2drms.header.append(('DATAVALS', l2[0].header['NAXIS1']*l2[0].header['NAXIS2'], 'Actual number of data values in images'), end=True)

        # MISSVALS
        # Missing values: TOTVALS - DATAVALS
        l2drms.header.append(('MISSVALS', 0, 'Missing values: TOTVALS - DATAVALS'), end=True)
        
        # DATAMIN
        l2drms.header.append(('DATAMIN', l2[0].header['DATAMIN'], 'Minimum value from pixels within 99% of solar radius'), end=True)
        
        # DATAMAX
        l2drms.header.append(('DATAMAX', l2[0].header['DATAMAX'], 'Maximum value from pixels within 99% of solar radius'), end=True)
        
        hdul = fits.HDUList([prim, l2drms])
        hdul.writeto(os.path.join(outpath_data, '%s_drms.fits' %file[11:-n_end]), overwrite=True) #ignore first 12 characters YYYY-MM-DD/ and .fits/fits.gz ending 

    if config.verbose: print('\nDRMS compatible FITS header creation complete.\n\n')


    # Create DRMS ingestions scripts
    files = os.listdir(outpath_data)
    fitsfiles = [file for file in files if file.endswith(".fits")]

    #setsid is a Linux/Unix command that runs a program in a new session and new process group. 
    #It effectively detaches the process from the current terminal’s job control (and signals like Ctrl+C).
    set_info = 'setsid set_info -c ds="%s" T_REC="%s" magnetogram=%s\n'
    jv2ts    = "setsid jv2ts in=%s['%s'] v2hout=%s histlink=none TSTART='%s' TTOTAL='12m' TCHUNK='12m' MAPMMAX=5402 SINBDIVS=2160 LGSHIFT=3 CARRSTRETCH=1 MCORLEV=%s MAPRMAX=%s MAPLGMAX=90.0 MAPLGMIN=-90 MAPBMAX=90.0 VCORLEV=0 NAN_BEYOND_RMAX=1 FORCEOUTPUT=1\n"
    set_keys = "setsid set_keys ds=%s[%s] %s=%s\n"
    rsmapmag = "setsid resizemappingmag in=%s['%s'] out=%s nbin=3\n"

    trec_out = open(outpath_scripts+'trecs.txt', 'w')

    j = 0 # nsplit counter
    for i, fname in enumerate(fitsfiles):
        
        if config.verbose: print('Processing %s...' %fname)
        
        # load with scaling to recognize blank cells -> necessary to prevent artifacts after resize
        fld = fits.open(outpath_data+fname)#, do_not_scale_image_data=True) 
        trec = fld[1].header['T_REC']
        fld.close()

        nsplit = int(np.ceil(len(fitsfiles)/config.nparallel_phi))
        
        if i % nsplit == 0:  # create a total of 10 batch scripts every SPLIT steps

            if i > 0: 
                batch_out.write('echo "PHI data batch %s done"'%j)
                batch_out.close()

                # make the script is executable
                subprocess.call(['chmod', '755', os.path.join(outpath_scripts, remap_str)])

                if False:# config.run_phi_scripts:
                    # Run all scripts in parallel
                    if config.verbose: print('Running %s ...' %remap_str)
                    run_script_with_nohup(session_folder, remap_str)

                j+=1 
    
            #jv2ts_log = os.path.join(logpath_rel, 'phi_jv2ts_%s_%s.log'% (config.proj, j))
            #rmm_log   = os.path.join(logpath_rel, 'phi_rmm_%s_%s.log'  % (config.proj, j))
            #remap_log = os.path.join(outpath_logs, 'phi_remap_rebin_%s_%s.log' % (config.proj, j))

            # beginning of new batch script    
            remap_str = 'phi_remap_rebin_%s_%s.sh' % (config.proj, j)
            batch_out = open(os.path.join(outpath_scripts, remap_str), 'w')
            add_script_header(batch_out, remap_str)


        batch_out.write('\n#%s' %fname)
        batch_out.write('\necho %s' %set_info %(config.data_series_phi, trec, os.path.join(outpath_data, fname)))
        batch_out.write(set_info %(config.data_series_phi, trec, os.path.join(outpath_data, fname)))
    
        file = fits.open(outpath_data+fname)[1]
        batch_out.write('\necho %s' %jv2ts %(config.data_series_phi, trec, config.data_series_jv2ts, trec, config.mcorlev, config.phi_maprmax))
        batch_out.write(jv2ts %(config.data_series_phi, trec, config.data_series_jv2ts, trec, config.mcorlev, config.phi_maprmax))
        batch_out.write('\necho %s' %set_keys %(config.data_series_jv2ts, trec, "CAR_ROT",  file.header['CAR_ROT2']))
        batch_out.write(set_keys %(config.data_series_jv2ts, trec, "CAR_ROT",  file.header['CAR_ROT2']))

        
        batch_out.write('\necho %s' %rsmapmag %(config.data_series_jv2ts, trec, config.data_series_remap))
        batch_out.write(rsmapmag %(config.data_series_jv2ts, trec, config.data_series_remap)) 
        add_check_continue(batch_out)
        batch_out.write('\n')

        trec_out.write("%s\n"%trec)

    batch_out.write('echo "PHI data batch %s done"'%j)
    batch_out.close()
    trec_out.close()

    if config.verbose: 
        print('\nDRMS ingestion script creation complete.\n')

    if False: #config.run_phi_scripts:
        if config.verbose: print('Running %s ...' %remap_str)
        run_script_with_nohup(session_folder, remap_str)

if __name__ == "__main__":
    #main(sys.argv[1:])
    main()

