import subprocess
import os
import numpy as np
from utils.utils import add_script_header, add_check_continue, get_dataseries_count, get_dataseries_times


def main(config, session_folder):

    outpath_scripts = os.path.join(session_folder, config.script_path)
    outpath_logs    = os.path.join(session_folder, config.log_path)
    
    #setsid is a Linux/Unix command that runs a program in a new session and new process group. 
    #It effectively detaches the process from the current terminal’s job control (and signals like Ctrl+C).
    jv2ts = 'setsid jv2ts in=%s["%s"] v2hout=%s histlink=none TSTART="%s" TTOTAL="12m" TCHUNK="12m" MAPMMAX=5402 SINBDIVS=2160 LGSHIFT=3 CARRSTRETCH=1 config.mcorlev=%s MAPRMAX=%s MAPLGMAX=90.0 MAPLGMIN=-90 MAPBMAX=90.0 VCORLEV=0 NAN_BEYOND_RMAX=1 FORCEOUTPUT=1\n' 
            #timestamp, v2hout, timestamp, config.mcorlev, logfile

    rsmapmag = 'setsid resizemappingmag in=%s["%s"] out=%s nbin=3\n' #in_ds, timestamp, out_ds, logfile
    
    times = get_dataseries_times(config.data_series_hmi, config.timestring_hmi, config.interval)  # list with all queued time stamps
    
    if config.filter_duplicates_hmi:
        time_duplicates = get_dataseries_times(config.data_series_jv2ts, config.timestring_hmi, config.interval)
        
        for duplicate in time_duplicates:
            if duplicate in times:
                if config.verbose: print("Skipping %s (duplicate)" %duplicate)
                times.remove(duplicate)

    # looks like this is unsed and obsolete   
    n_m720s = get_dataseries_count(config.data_series_hmi, config.timestring_hmi, config.interval)     # line count for time stamps

    nsplit = int(np.ceil(n_m720s/config.nparallel_hmi))

    # split files after nsplit entries    
    j = 0
    for i, time in enumerate(times):

        if i % nsplit == 0:  # create a total of 10 batch scripts every SPLIT steps

            if i > 0: 
                batch_out.write('echo "HMI data batch %s done"'%j)
                batch_out.close()

                # make the script is executable
                subprocess.call(['chmod', '755', os.path.join(outpath_scripts, remap_str)])
                j+=1 
       
            # define the log file for the next batch script
            #remap_log = os.path.join(outpath_logs, 'hmi_remap_rebin_%s_%s.log' % (config.proj, j))

            # beginning of new batch script    
            remap_str = 'hmi_remap_rebin_%s_%s.sh' % (config.proj, j)
            batch_out = open(os.path.join(outpath_scripts, remap_str), 'w')
            add_script_header(batch_out, remap_str)


        # write the commands to the batch script
        batch_out.write('\necho %s' %jv2ts %(config.data_series_hmi, time, config.data_series_jv2ts, time, config.mcorlev, config.hmi_maprmax))
        batch_out.write(jv2ts %(config.data_series_hmi, time, config.data_series_jv2ts, time, config.mcorlev, config.hmi_maprmax))
        
        batch_out.write('\necho %s' %rsmapmag %(config.data_series_jv2ts, time, config.data_series_remap))
        batch_out.write(rsmapmag %(config.data_series_jv2ts, time, config.data_series_remap))
        add_check_continue(batch_out)
        batch_out.write('\n')

    batch_out.write('echo "HMI data batch %s done"'%j)
    batch_out.close()
    
    if config.verbose: 
        print('\nHMI processing script creation complete.\n')

if __name__ == "__main__":
    #main(sys.argv[1:])
    import config.config as Config
    config = Config()
    main(config)