import numpy as np
from astropy.io import fits
import subprocess
import sys, os, getopt



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


def main(argv):
     
    # CHANGE PARAMETERS HERE
    # TODO utilise argv
    
    #path = './output/'
    path = '/scratch/slam/loeschl/dev/python/synop_old/LoS/output/data/phi/FDT_test_release_june_2022_defringed/drms/'
    #path = '/scratch/slam/loeschl/dev/python/synop_old/LoS/output/data/phi/feb2021_rev02/drms/'
    #path = '/scratch/slam/loeschl/dev/python/synop_old/LoS/output/data/phi/feb2021/drms/'
    
    rev = "_FDT_test_release_june_2022_defri"#"_rev00_r095"
    
    Mr = True
    
    if not os.path.isdir(path):
        os.mkdir(path)
        
        
    data_series = "hmi.M_720s"
    #data_series = "mps_loeschl.hmi_m720s_nrt"
    
    #period = "2021.02.19_09:00:00_TAI,2021.02.22_10:48:00_TAI,2021.02.23_06:48:00_TAI,2021.02.24_02:36:00_TAI,2021.02.24_22:36:00_TAI,2021.02.25_18:36:00_TAI,2021.02.26_14:36:00_TAI,2021.02.28_07:12:00_TAI"#"2014.05.04_14:46:00_TAI-2014.05.31_19:59:00_TAI" 
    #period="2021.01.21_06:36:00_TAI-2021.01.22_16:36:00_TAI@2h,2021.02.03_12:36:00_TAI-2021.02.19_14:36:00_TAI@2h" 
    # CENTRAL HMI WINDOW AT 12 MINUTE CADENCE
    # NO BOUNDARY DATASETS IN PREPARATION FOR PERIODIC BOUNDARIES
    #period = "2021.02.03_11:12:00_TAI-2021.02.15_18:12:00_TAI@12m"
    #period = "2022.02.04_12:00:00_TAI-2022.02.08_04:00:00_TAI@12m" # CR2254
    #period = "2022.03.23_23:12:00_TAI-2022.03.28_07:12:00_TAI@12m" # CR2255
    #period = "2014.05.10_00:00:00_TAI-2014.05.16_00:00:00_TAI@2h" # CR2150    
    #period = "2021.02.02_16:00:00_TAI-2021.02.18_14:48:00_TAI@12m" # CR2240 ideal

    #period = "2021.02.03_12:36:00_TAI-2021.02.15_16:36:00_TAI@12m" # CR2240
    period = "2022.06.06_23:00:00_TAI-2022.06.17_23:00:00_TAI@12m" # CR2258

    interval = ""#"@12m"
    cr = 2258
    
    #v2hout = 'mps_loeschl.Ml_hiresmap_720s'
    #rmmout = 'mps_loeschl.Ml_remap_720s_test'
        
    #v2hout = 'mps_loeschl.Ml_hiresmap_CR2255' #'mps_loeschl.Ml_hiresmap_CR2240_fast'
    #rmmout = 'mps_loeschl.Ml_remap_CR2255' #'mps_loeschl.Ml_remap_CR2240_fast'
    
    #v2hout = 'mps_loeschl.Ml_hiresmap_CR2240_rev02' #'mps_loeschl.Ml_hiresmap_CR2240_fast'
    #rmmout = 'mps_loeschl.Ml_remap_CR2240_rev02' #'mps_loeschl.Ml_remap_CR2240_fast    
    
    if Mr:
        v2hout = 'mps_loeschl.Mr_hiresmap_CR%s%s'%(cr, rev) #'mps_loeschl.Ml_hiresmap_CR2240_fast'
        rmmout = 'mps_loeschl.Mr_remap_CR%s%s'%(cr, rev) #'mps_loeschl.Ml_remap_CR2240_fast
        proj = 'Mr'
    else:        
        v2hout = 'mps_loeschl.Ml_hiresmap_CR%s%s'%(cr, rev) #'mps_loeschl.Ml_hiresmap_CR2240_fast'
        rmmout = 'mps_loeschl.Ml_remap_CR%s%s'%(cr, rev) #'mps_loeschl.Ml_remap_CR2240_fast
        proj = 'Ml'
    
    filter_duplicates = True
    # CHANGE PARAMETERS HERE
    
    # CODE STARTS HERE
    #jv2ts = 'jv2ts in=%s["%s"] v2hout=%s histlink=none TSTART="%s" TTOTAL="12m" TCHUNK="12m" \
    #         MAPMMAX=5402 SINBDIVS=2160 LGSHIFT=3 CARRSTRETCH=1 MCORLEV=1 MAPRMAX=0.998 \
    #         MAPLGMAX=90.0 MAPLGMIN=-90 MAPBMAX=90.0 VCORLEV=0 NAN_BEYOND_RMAX=1 FORCEOUTPUT=1 >> %s' #timestamp, v2hout, timestamp, logfile
    
    # Ml
    #jv2ts = 'jv2ts in=%s["%s"] v2hout=%s histlink=none TSTART="%s" TTOTAL="12m" TCHUNK="12m" \
    #         MAPMMAX=5402 SINBDIVS=2160 LGSHIFT=3 CARRSTRETCH=1 MCORLEV=1 MAPRMAX=0.998 \
    #         MAPLGMAX=90.0 MAPLGMIN=-90 MAPBMAX=90.0 VCORLEV=0 NAN_BEYOND_RMAX=1 FORCEOUTPUT=1 >> %s' #timestamp, v2hout, timestamp, logfile
    
    # Mr
    if Mr:
        jv2ts = 'jv2ts in=%s["%s"] v2hout=%s histlink=none TSTART="%s" TTOTAL="12m" TCHUNK="12m" \
                MAPMMAX=5402 SINBDIVS=2160 LGSHIFT=3 CARRSTRETCH=1 MCORLEV=2 MAPRMAX=0.998 \
                MAPLGMAX=90.0 MAPLGMIN=-90 MAPBMAX=90.0 VCORLEV=0 NAN_BEYOND_RMAX=1 FORCEOUTPUT=1 >> %s' #timestamp, v2hout, timestamp, logfile
    else:
        jv2ts = 'jv2ts in=%s["%s"] v2hout=%s histlink=none TSTART="%s" TTOTAL="12m" TCHUNK="12m" \
                 MAPMMAX=5402 SINBDIVS=2160 LGSHIFT=3 CARRSTRETCH=1 MCORLEV=1 MAPRMAX=0.998 \
                 MAPLGMAX=90.0 MAPLGMIN=-90 MAPBMAX=90.0 VCORLEV=0 NAN_BEYOND_RMAX=1 FORCEOUTPUT=1 >> %s' #timestamp, v2hout, timestamp, logfile
    
    rsmapmag = 'resizemappingmag in=%s["%s"] out=%s nbin=3 >>%s' #in_ds, timestamp, out_ds, logfile
    

    times = get_M_720s_times(data_series, period, interval)  # list with all queued time stamps
    
    
    if filter_duplicates:
        time_duplicates = get_M_720s_times(v2hout, period, interval)
        
        for duplicate in time_duplicates:
            if duplicate in times:
                print("Skipping %s (duplicate)" %duplicate)
                times.remove(duplicate)

        
    wc = get_M_720s_count(data_series, period, interval)     # line count for time stamps

    # split files after n entries
    split = 150
    
    j = 0
    for i, time in enumerate(times):

        if i % split == 0:  # create a total of 10 batch scripts every SPLIT steps

            if i > 0: 
                batch_out.write('echo "done"')
                batch_out.close()
                j+=1 
                
            jv2ts_log = './log/jv2ts_%s_%s.log'% (proj, j)
            rmm_log = './log/rmm_%s_%s.log' % (proj, j)

            batch_out = open(path + 'remap_rebin_%s_%s.sh' % (proj, j), 'w')
            batch_out.write('#!/bin/bash\n')

        batch_out.write("%s \n" % (jv2ts %(data_series, time, v2hout, time, jv2ts_log)))
        batch_out.write("%s \n\n" % (rsmapmag %(v2hout, time, rmmout, rmm_log)))
    
    batch_out.write('echo "batch %s done"'%j)
    batch_out.close()
    
    
    
if __name__ == "__main__":
    main(sys.argv[1:])