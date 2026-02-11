import subprocess
import os
import numpy as np
from utils.utils import add_script_header, add_check_continue, get_dataseries_count, get_dataseries_times

STATUS_OK = 0
STATUS_NODATA = 1
STATUS_DISAMBIG_ERROR = 2

def main(config, session_folder):

    outpath_scripts = os.path.join(session_folder, config.script_path)
    outpath_logs    = os.path.join(session_folder, config.log_path)
    
    #setsid is a Linux/Unix command that runs a program in a new session and new process group. 
    #It effectively detaches the process from the current terminal’s job control (and signals like Ctrl+C).
    
    vectmag_random = "vectmag2helio3comp_random in='%s[%s]' v2hout=%s histlink=none TSTART=%s TTOTAL='12m' TCHUNK='12m' NAN_BEYOND_RMAX=1 DATASIGN=1 FORCEOUTPUT=1 MAPRMAX=%sMAPMMAX=5402 SINBDIVS=2160 RESCALE=0.333333\n"
    vectmag_poten  = "vectmag2helio3comp_poten  in='%s[%s]' v2hout=%s histlink=none TSTART=%s TTOTAL='12m' TCHUNK='12m' NAN_BEYOND_RMAX=1 DATASIGN=1 FORCEOUTPUT=1 MAPRMAX=%sMAPMMAX=5402 SINBDIVS=2160 RESCALE=0.333333\n"
    vectmag_radial = "vectmag2helio3comp_radial in='%s[%s]' v2hout=%s histlink=none TSTART=%s TTOTAL='12m' TCHUNK='12m' NAN_BEYOND_RMAX=1 DATASIGN=1 FORCEOUTPUT=1 MAPRMAX=%sMAPMMAX=5402 SINBDIVS=2160 RESCALE=0.333333\n"

    if config.b3c_disambig == "random":
        vectmag = vectmag_random
    elif config.b3c_disambig == "potential":
        vectmag = vectmag_poten    
    elif config.b3c_disambig == "radial":
        vectmag = vectmag_radial
    else:
        print(f'Unknown disambiguation setting in config: {config.b3c_disambig}. Select between "random", "potential", "radial"')
        return STATUS_DISAMBIG_ERROR
    
    times = get_dataseries_times(config.data_series_hmi, config.timestring_hmi, config.interval_hmi)  # list with all queued time stamps
    
    if config.filter_duplicates_hmi:
        time_duplicates = get_dataseries_times(config.data_series_remap_hmi, config.timestring_hmi, config.interval_hmi)
        
        for duplicate in time_duplicates:
            if duplicate in times:
                if config.verbose: print("Skipping %s (duplicate)" %duplicate)
                times.remove(duplicate)

    # looks like this is unsed and obsolete   
    #n_m720s = get_dataseries_count(config.data_series_hmi, config.timestring_hmi, config.interval_hmi)     # line count for time stamps
    n_m720s = len(times)

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
            remap_str = 'hmi_remap_rebin_b3c_%s_%s.sh' % (config.proj, j)
            batch_out = open(os.path.join(outpath_scripts, remap_str), 'w')
            add_script_header(batch_out, remap_str)


        # write the commands to the batch script
        batch_out.write('\necho $(date +"%Y-%m-%d %H:%M:%S")')
        batch_out.write('\necho %s' %vectmag %(config.data_series_hmi, time, config.data_series_remap_hmi, time, config.hmi_maprmax))
        batch_out.write(vectmag %(config.data_series_hmi, time, config.data_series_remap_hmi, time, config.hmi_maprmax))
        
        add_check_continue(batch_out)
        batch_out.write('\n')

    batch_out.write('echo "HMI data batch %s done"'%j)
    batch_out.close()
    
    if config.verbose: 
        print('\nHMI processing script creation complete.\n')

    return STATUS_OK


if __name__ == "__main__":
    #main(sys.argv[1:])
    import config.config as Config
    config = Config()
    main(config)