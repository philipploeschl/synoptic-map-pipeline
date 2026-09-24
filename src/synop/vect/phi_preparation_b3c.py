import os, sys, subprocess
import numpy as np
from astropy.io import fits
#from astropy.time import Time, TimeDelta, TimeDatetime
from datetime import datetime, timedelta
from utils.utils import add_script_header, add_check_continue, get_phi_filenames, clean_temporary_fits, get_dataseries_count, get_dataseries_times, get_dates_from_timestring, get_fits_extension_name

STATUS_OK = 0
STATUS_NODATA = 1
STATUS_DISAMBIG_ERROR = 2

def main(config, session_folder):
    #set cwd to file directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    outpath_scripts = os.path.join(session_folder, config.script_path)
    outpath_data    = os.path.join(session_folder, config.data_path)
    #outpath_logs    = os.path.join(session_folder, config.log_path)

    clean_temporary_fits(outpath_data)

    date_start, date_end = get_dates_from_timestring(config.timestring_phi)

    #times = get_dataseries_times(config.data_series_phi, config.timestring_phi, config.interval_phi)  # list with all queued time stamps
    existing_timestamps = get_dataseries_times(config.data_series_remap_phi, config.timestring_phi, config.interval_phi)

    fitsfiles = []
    for key in config.key:
        fitsfiles.append(get_phi_filenames(config.phi_dbpath, date_start, date_end, key, config.verbose))
    
    fitsfiles = [x for sublist in fitsfiles for x in sublist]

    if len(fitsfiles) == 0:
        print(f"No PHI files found for the given time range {date_start}-{date_end}. Aborting run...")
        return STATUS_NODATA

    trecs = []
    clons = []
    
    for file in fitsfiles:

        n_end = get_fits_extension_name(file)

        #l2 = fits.open(config.phi_datapath+file) # old version wihtout direct fmdb access
        l2 = fits.open(os.path.join(config.phi_dbpath,file))
        if config.verbose: print("Processing %s ..." %file)
        
        prim = fits.PrimaryHDU()
        l2drms = fits.CompImageHDU(data=l2[0].data.astype(np.int32))

        # open updated source file
        l2drms.header.append(('', '', ''), end=True)
        l2drms.header.append(('', '  / HMI Compatibility', ''), end=True)
        
        # OBSOLETE
        # TODO TEMPORARY: Fix CAR_ROT bug, figure out what's going on for production version
        #if l2[0].header['CAR_ROT'] == 2239: 
        #    l2[0].header['CAR_ROT'] = 2240
        #
        #if l2[0].header['CRLN_OBS'] == 358.80689 and l2[0].header['CAR_ROT'] == 2240:
        #    l2[0].header['CAR_ROT'] = 2241
        
        # T_REC / T_OBS
        #DATE-AVG= '2021-02-05T20:00:45.616' / [UTC] Average time of observation     
        #T_OBS   = '2021.02.28_07:11:55.437_TAI' / [TAI] nominal time 
        #T_REC   = '2021.02.28_07:12:00.000_TAI' / [TAI] Slot time    
        # Conversion for date format / UTC to TAI / round to the next 12 minute slot for T_REC
        #trec = datetime.strptime(l2[0].header['DATE-AVG'],   "%Y-%m-%dT%H:%M:%S.%f")
        tobs = datetime.strptime(l2[0].header['DATE-OBS'],   "%Y-%m-%dT%H:%M:%S.%f")
        
        #TODO T_TOBS TAI CONVERSION?
        utc2tai = timedelta(0, 37)                 # use for utc2tai conversion
        tobs = tobs + utc2tai                      # use for utc2tai conversion
        tobs = tobs.strftime("%Y.%m.%d_%H:%M:%S_TAI")

        # skip file if tobs already exists in phi dataseries
        if config.filter_duplicates_phi:
            if tobs in existing_timestamps:
                if config.verbose: print("Skipping %s (duplicate)" %tobs)
                continue


        # T_REC Interpolation     
        #if config.verbose: print("True observation time during Carrington rotation %s: %s" %(l2[0].header['CAR_ROT'], tobs))  
        #trec, hmi_prev, hmi_next, car_rot = calc_trec(float(l2[0].header['CRLN_OBS']), int(l2[0].header['CAR_ROT']), verbose=config.verbose)

        #if config.verbose: print(trec, car_rot, l2[0].header['CRLN_OBS'])
        
        # Use T_OBS as T_REC 
        trec = tobs

        trecs.append(trec)
        clons.append(l2[0].header['CRLN_OBS'])
        
        l2drms.header.append(('T_REC', trec, ''), end=True)
        l2drms.header.append(('T_OBS', tobs, ''), end=True)  # required for JV2TS
        
        l2drms.header.append(('TRECEPOC', '1993.01.01_00:00:00_TAI', 'Time of origin'), end=True)
        l2drms.header.append(('TRECSTEP', 720.0,  'ts_eq step'), end=True)
        
        # OBSOLETE
        # these two keywords are redundant with T_REC and T_OBS
        #l2drms.header.append(('HMI_PREV', hmi_prev, 'Previous HMI T_REC for this CRLN_OBS'), end=True) # HMI interpolated T_REC
        #l2drms.header.append(('HMI_NEXT', hmi_next, 'Next HMI T_REC for this CRLN_OBS'), end=True) # real PHI observation date as backup
        
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
        crln_obs = l2[0].header['CRLN_OBS'] if l2[0].header['CRLN_OBS'] >= 0 else l2[0].header['CRLN_OBS'] + 360.0
        l2drms.header.append(('CRLN_OBS', crln_obs, 'Carrington longitude of PHI'), end=True)
        
        #CRLT_OBS
        l2drms.header.append(('CRLT_OBS', l2[0].header['CRLT_OBS'], 'Carrington latitude of PHI'), end=True)
        
        #CAR_ROT        
        l2drms.header.append(('CAR_ROT', l2[0].header['CAR_ROT'], 'Carrington rotation number of CRLN_OBS'), end=True)
        #l2drms.header.append(('CAR_ROT2', car_rot, 'Carrington rotation number of synoptic map'), end=True)
        
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
        
        # FILENAME
        l2drms.header.append(('FILENAME', file[11:27]+'bmag'+file[31:] , 'Source PHI filename'), end=True)
        
        if ("bamb" in file):
            components=['disamb','configd','confmap'] #three components of 3D array of bamb files: disamb, config_disamb, confid_map
            for i in range(l2drms.data.shape[0]): 
                temp = fits.CompImageHDU(data=l2drms.data[i,:,:], header=l2drms.header)
                hdul = fits.HDUList([prim, temp])
                hdul.writeto(os.path.join(outpath_data, '%s%s%s_drms.fits' %(file[11:27], components[i], file[31:-n_end])), overwrite=True) #ignore first 12 characters YYYY-MM-DD/ and .fits/fits.gz ending 
        else:
            hdul = fits.HDUList([prim, l2drms])
            hdul.writeto(os.path.join(outpath_data, '%s_drms.fits' %file[11:-n_end]), overwrite=True) #ignore first 12 characters YYYY-MM-DD/ and .fits/fits.gz ending 

    if config.verbose: print('\nDRMS compatible FITS header creation complete.\n\n')


    # Create DRMS ingestions scripts
    files = os.listdir(outpath_data)
    fitsfiles = [file for file in files if file.endswith(".fits")]

    bmag_fitsfiles = [f for f in fitsfiles if "bmag" in f]
    binc_fitsfiles = [f for f in fitsfiles if "binc" in f]
    bazi_fitsfiles = [f for f in fitsfiles if "bazi" in f]
    disamb_fitsfiles = [f for f in fitsfiles if "disamb" in f]
    configd_fitsfiles = [f for f in fitsfiles if "configd" in f]
    confmap_fitsfiles = [f for f in fitsfiles if "confmap" in f]

    #setsid is a Linux/Unix command that runs a program in a new session and new process group. 
    #It effectively detaches the process from the current terminal’s job control (and signals like Ctrl+C).

    #when disambig data avail
    
    set_info = 'setsid set_info -c ds="%s" T_REC="%s" field=%s inclination=%s azimuth=%s disambig=%s conf_disambig=%s confid_map=%s\n'
    #set_info = 'setsid set_info -c ds="%s" T_REC="%s" field=%s inclination=%s azimuth=%s disambig=%s\n'

    #jv2ts    = "setsid jv2ts in=%s['%s'] v2hout=%s histlink=none TSTART='%s' TTOTAL='12m' TCHUNK='12m' MAPMMAX=5402 SINBDIVS=2160 LGSHIFT=3 CARRSTRETCH=1 MCORLEV=%s MAPRMAX=%s MAPLGMAX=90.0 MAPLGMIN=-90 MAPBMAX=90.0 VCORLEV=0 NAN_BEYOND_RMAX=1 FORCEOUTPUT=1\n"
    vectmag_random = 'setsid vectmag2helio3comp_random in=%s[%s] v2hout=%s histlink=none TSTART=%s TTOTAL="12m" TCHUNK="12m" NAN_BEYOND_RMAX=1 DATASIGN=1 FORCEOUTPUT=1 MAPRMAX=%s MAPMMAX=%s SINBDIVS=%s RESCALE=%s\n'
    vectmag_poten  = 'setsid vectmag2helio3comp_poten  in=%s[%s] v2hout=%s histlink=none TSTART=%s TTOTAL="12m" TCHUNK="12m" NAN_BEYOND_RMAX=1 DATASIGN=1 FORCEOUTPUT=1 MAPRMAX=%s MAPMMAX=%s SINBDIVS=%s RESCALE=%s\n'
    vectmag_radial = 'setsid vectmag2helio3comp_radial in=%s[%s] v2hout=%s histlink=none TSTART=%s TTOTAL="12m" TCHUNK="12m" NAN_BEYOND_RMAX=1 DATASIGN=1 FORCEOUTPUT=1 MAPRMAX=%s MAPMMAX=%s SINBDIVS=%s RESCALE=%s\n'

    if config.b3c_disambig == "random":
        vectmag = vectmag_random
    elif config.b3c_disambig == "potential":
        vectmag = vectmag_poten    
    elif config.b3c_disambig == "radial":
        vectmag = vectmag_radial
    else:
        print(f'Unknown disambiguation setting in config: {config.b3c_disambig}. Select between "random", "potential", "radial"')
        return STATUS_DISAMBIG_ERROR
    
    xdim = (config.mapmmax * config.rescale_phi) + config.rescale_phi
    ydim = config.sinbdivs * config.rescale_phi
    rescale = np.round(1/config.rescale_phi, 6) # default value at 6 decimal precison: 0.333333

    #set_keys = "setsid set_keys ds=%s[%s] %s=%s\n" #OBSOLETE
    #rsmapmag = "setsid resizemappingmag in=%s['%s'] out=%s nbin=3\n"

    trec_out = open(outpath_scripts+'trecs.txt', 'w')

    j = 0 # nsplit counter
    for i, (fname_bmag, fname_binc, fname_bazi, fname_disamb, fname_configd, fname_confmap) in enumerate(zip(bmag_fitsfiles, binc_fitsfiles, bazi_fitsfiles, disamb_fitsfiles, configd_fitsfiles, confmap_fitsfiles)):#, disambig_fitsfiles)):
        
        if config.verbose: print('Processing %s...' %fname_bmag)
        
        # load with scaling to recognize blank cells -> necessary to prevent artifacts after resize
        fld = fits.open(outpath_data+fname_bmag)#, do_not_scale_image_data=True) 
        trec = fld[1].header['T_REC']
        fld.close()

        nsplit = int(np.ceil(len(bmag_fitsfiles)/config.nparallel_phi))
        
        if i % nsplit == 0:  # create a total of 10 batch scripts every SPLIT steps

            if i > 0: 
                batch_out.write('echo "PHI data batch %s done"'%j)
                batch_out.close()

                # make the script is executable
                subprocess.call(['chmod', '755', os.path.join(outpath_scripts, remap_str)])
                j+=1 
    
            #jv2ts_log = os.path.join(logpath_rel, 'phi_jv2ts_%s_%s.log'% (config.proj, j))
            #rmm_log   = os.path.join(logpath_rel, 'phi_rmm_%s_%s.log'  % (config.proj, j))
            #remap_log = os.path.join(outpath_logs, 'phi_remap_rebin_%s_%s.log' % (config.proj, j))

            # beginning of new batch script    
            remap_str = 'phi_remap_rebin_%s_%s.sh' % (config.proj, j)
            batch_out = open(os.path.join(outpath_scripts, remap_str), 'w')
            add_script_header(batch_out, remap_str)

        batch_out.write('\necho $(date +"%Y-%m-%d %H:%M:%S")')
        batch_out.write('\n#%s' %fname_bmag)
        # set_info = 'setsid set_info -c ds="%s" T_REC="%s" field=%s inclination=%s azimuth=%s disambig=%s\n'
        
        #when disambig data avail
        
        #batch_out.write('\necho %s' %set_info %(config.data_series_phi, trec, os.path.join(outpath_data, fname_bmag), os.path.join(outpath_data, fname_binc), os.path.join(outpath_data, fname_bazi)))
        #batch_out.write(set_info %(config.data_series_phi, trec, os.path.join(outpath_data, fname_bmag), os.path.join(outpath_data, fname_binc), os.path.join(outpath_data, fname_bazi)))

        batch_out.write('\necho %s' %set_info %(config.data_series_phi, trec, os.path.join(outpath_data, fname_bmag), os.path.join(outpath_data, fname_binc), os.path.join(outpath_data, fname_bazi), os.path.join(outpath_data, fname_disamb), os.path.join(outpath_data, fname_configd), os.path.join(outpath_data, fname_confmap)))
        batch_out.write(set_info %(config.data_series_phi, trec, os.path.join(outpath_data, fname_bmag), os.path.join(outpath_data, fname_binc), os.path.join(outpath_data, fname_bazi), os.path.join(outpath_data, fname_disamb), os.path.join(outpath_data, fname_configd), os.path.join(outpath_data, fname_confmap)))
        
        vectmag_random = 'setsid vectmag2helio3comp_random in=%s[%s] v2hout=%s histlink=none TSTART=%s TTOTAL="12m" TCHUNK="12m" NAN_BEYOND_RMAX=1 DATASIGN=1 FORCEOUTPUT=1 MAPRMAX=%s MAPMMAX=%s SINBDIVS=%s RESCALE=%s\n'

        batch_out.write('\necho %s' %vectmag %(config.data_series_phi, trec, config.data_series_remap_phi, trec, config.phi_maprmax, xdim, ydim, rescale))
        batch_out.write(vectmag %(config.data_series_phi, trec, config.data_series_remap_phi, trec, config.phi_maprmax, xdim, ydim, rescale))
        
        add_check_continue(batch_out)
        batch_out.write('\n')

        trec_out.write("%s\n"%trec)

    batch_out.write('echo "PHI data batch %s done"'%j)
    batch_out.close()
    trec_out.close()

    if config.verbose: 
        print('\nDRMS ingestion script creation complete.\n')

    return STATUS_OK

if __name__ == "__main__":
    #main(sys.argv[1:])
    main()

