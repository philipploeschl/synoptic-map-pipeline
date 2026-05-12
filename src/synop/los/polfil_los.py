import os,subprocess

STATUS_OK = 0

def main(config, session_folder):

    # Ingest los maps stored in session folder /synop into data series
    print("Ingesting $path/synopMr.fits ..\n")
    set_info = 'set_info -c ds="%s" CAR_ROT="%s" magnetogram=%s\n'
    
    outpath_synop = os.path.join(session_folder, config.synop_path)

    print("Running:")
    print(set_info %(config.data_series_synop, config.cr, os.path.join(outpath_synop, "synopMr.fits")))

    subprocess.run(set_info %(config.data_series_synop, config.cr, os.path.join(outpath_synop, "synopMr.fits")), shell=True, check=True)

    # Fill poles with HMI polar database using polcorr module 
    # default for polcorr in=in_data_series[CAR_ROT] out=out_data_series poldb=polar_data_series method=TEMP_SPAT lat0=60 latfil=75 latfil1=62 nflag=1 sflag=1

    pol_corr = 'polcorr in="%s"["%s"] out="%s" poldb=mps_santosf.polar_db method=TEMP_SPAT lat0="%s" latfil="%s" latfil1="%s" nflag="%s" sflag="%s"'
    
    print("Running:")
    print(pol_corr %(config.data_series_synop, config.cr, config.data_series_polfil, 60, 65, 60, 1, 1))

    return STATUS_OK