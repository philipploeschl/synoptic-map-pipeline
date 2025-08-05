import subprocess
import sys, os#, getopt
import config
from misc import run_script_with_nohup, get_current_session_folder


def get_M_720s_count(data_series, period, interval):
    
    si_string = "show_info -iP %s[%s%s]" %(data_series, period, interval)
    wc_string = "%s | wc -l" % si_string
    
    wc_out = int(subprocess.check_output(wc_string, shell=True)[:-1].decode("utf-8"))
    
    return wc_out 

def get_M_720s_times(data_series, period, interval):
    
    times = []
    si_string = "show_info -iP %s[%s%s]" %(data_series, period, interval)
    
    si_out = subprocess.check_output(si_string, shell=True)[:-1].decode("utf-8")
    
    raw = si_out.split('\n') #separate data series from SUMS path
    
    for line in raw[1:]:
        i = line.find('[')
        j = line.find(']')
        times.append(line[i+1:j]) # [clong, cmLong]

    return times 

"""
def cmd_args(argv):
    
    inputfile = ''
    outputfile = ''
    
    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
        print('test.py -i <inputfile> -o <outputfile>')
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == '-h':
            print('test.py -i <inputfile> -o <outputfile>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-o", "--ofile"):
            outputfile = arg
    
    return inputfile, outputfile
"""

def main():

    # moved to config.py
    #config.output_path = '/scratch/slam/loeschl/dev/python/synop_old/LoS/output/data/phi/FDT_test_release_june_2022_defringed/drms/' # GHERARDO
    #config.id = "" #"_FDT_test_release_june_2022_defri"#"_rev00_r095" # GHERARDO
    #config.Mr = True  # Mr = False = Blos # GHERARDO
    #config.dataseries_input = "hmi.M_720s" # "mps_loeschl.hmi_m720s_nrt"
    #config.period = "2022.06.06_23:00:00_TAI-2022.06.17_23:00:00_TAI@12m" # CR2258
    #config.interval = ""#"@12m"
    #config.cr = 2258
    #config.filter_duplicates = True

    #set cwd to file directory
    #os.chdir(os.path.dirname(os.path.abspath(__file__)))
    session_folder = get_current_session_folder()
    outpath_scripts = os.path.join(session_folder, config.script_path)
    outpath_logs    = os.path.join(session_folder, config.log_path)

    logpath_rel = os.path.relpath(outpath_logs, outpath_scripts)

    # create output directory if it does not exist
    #if not os.path.isdir(config.output_path):
    #    os.mkdir(config.output_path)

    # moved to config.py    
    #if config.Mr:
    #    proj = "Mr"
    #    mcorlev = 2 # for jv2ts command line 
    #else:
    #    proj = "Ml"
    #    mcorlev = 1 # for jv2ts command line 

    #v2hout = '%s.%s_hiresmap_CR%s%s'%(config.dataseries_owner, proj, config.cr, config.id) #'mps_loeschl.Ml_hiresmap_config.cr2240_fast'
    #rmmout = '%s.%s_remap_CR%s%s'%(config.dataseries_owner, proj, config.cr, config.id) #'mps_loeschl.Ml_remap_CR2240_fast
    #v2hout = config.data_series_jv2ts
    #rmmout = config.data_series_remap

    jv2ts = 'jv2ts in=%s["%s"] v2hout=%s histlink=none TSTART="%s" TTOTAL="12m" TCHUNK="12m" \
            MAPMMAX=5402 SINBDIVS=2160 LGSHIFT=3 CARRSTRETCH=1 config.mcorlev=%s MAPRMAX=0.998 \
            MAPLGMAX=90.0 MAPLGMIN=-90 MAPBMAX=90.0 VCORLEV=0 NAN_BEYOND_RMAX=1 FORCEOUTPUT=1 >> %s' 
            #timestamp, v2hout, timestamp, config.mcorlev, logfile

    rsmapmag = 'resizemappingmag in=%s["%s"] out=%s nbin=3 >>%s' #in_ds, timestamp, out_ds, logfile
    
    times = get_M_720s_times(config.dataseries_input, config.period, config.interval)  # list with all queued time stamps
    
    if config.filter_duplicates:
        time_duplicates = get_M_720s_times(config.data_series_jv2ts, config.period, config.interval)
        
        for duplicate in time_duplicates:
            if duplicate in times:
                print("Skipping %s (duplicate)" %duplicate)
                times.remove(duplicate)

    # looks like this is unsed and obsolete   
    #wc = get_M_720s_count(config.dataseries_input, config.period, config.interval)     # line count for time stamps

    # split files after nsplit entries    
    j = 0
    for i, time in enumerate(times):

        if i % config.nsplit == 0:  # create a total of 10 batch scripts every SPLIT steps

            if i > 0: 
                batch_out.write('echo "done"')
                batch_out.close()

                # make the script is executable
                subprocess.call(['chmod', '755', os.path.join(outpath_scripts, remap_str)])

                if config.run_hmi_scripts:
                    # Run all scripts in parallel
                    run_script_with_nohup(session_folder, remap_str)
                j+=1 
       
            #jv2ts_log = os.path.join(logpath_rel, 'hmi_jv2ts_%s_%s.log'% (config.proj, j))
            #rmm_log   = os.path.join(logpath_rel, 'hmi_rmm_%s_%s.log'  % (config.proj, j))
            remap_log = os.path.join(outpath_logs, 'hmi_remap_rebin_%s_%s.log' % (config.proj, j))

            # beginning of new batch script    
            remap_str = 'hmi_remap_rebin_%s_%s.sh' % (config.proj, j)
            batch_out = open(os.path.join(outpath_scripts, remap_str), 'w')
            batch_out.write('#!/bin/bash\n')
            # add path change at the end of the script here 

        batch_out.write('\necho %s' %jv2ts %(config.dataseries_input, time, config.data_series_jv2ts, time, config.mcorlev, remap_log))
        batch_out.write("%s \n" %jv2ts %(config.dataseries_input, time, config.data_series_jv2ts, time, config.mcorlev, remap_log))

        batch_out.write('\n\necho %s' %rsmapmag %(config.data_series_jv2ts, time, config.data_series_remap, remap_log))
        batch_out.write("%s\n" %rsmapmag %(config.data_series_jv2ts, time, config.data_series_remap, remap_log))
    
    batch_out.write('echo "HMI data batch %s done"'%j)
    batch_out.close()
    
    if config.run_hmi_scripts:
        if config.verbose: print('Running %s ...' %remap_str)
        run_script_with_nohup(session_folder, remap_str)
    
    if config.verbose: 
        print('\nHMI processing script creation complete.\n')

if __name__ == "__main__":
    #main(sys.argv[1:])
    main()