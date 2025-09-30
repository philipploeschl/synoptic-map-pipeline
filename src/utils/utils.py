import os, sys
from datetime import datetime
import subprocess
import glob
import signal
from datetime import timedelta
import numpy as np
from sunpy.coordinates.sun import carrington_rotation_time
from scipy import interpolate
from itertools import groupby
from astropy.io import fits


def create_session_folder(config):
    """
    Creates a session folder named CRXXXX_<timestamp>, writes the path to a file,
    and returns the full path.
    """

    # Set this to your project’s output base directory
    root_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../"))
    output_base = os.path.join(root_path, config.output_path)

    #session_path_file = os.path.join(output_base, "session_path.txt")

    cr_str = f"{config.cr:04d}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    id = f"{config.id}"
    folder_name = f"CR{cr_str}_{id}_{timestamp}"
    session_folder = os.path.join(output_base, folder_name)

    create_session_structure(config, session_folder)
    
    if config.verbose: print(f"Creating new session folder... {session_folder}")

    # Save path to session_path.txt
    #with open(session_path_file, "w") as f:
    #    f.write(session_folder)

    config.update("session", folder_name)

    return session_folder

def create_session_structure(config, session_folder):

    # Creates substructre of the session folder if it doesn't exist.
    script_folder = os.path.join(session_folder, config.script_path)
    log_folder    = os.path.join(session_folder, config.log_path)
    data_folder   = os.path.join(session_folder, config.data_path)
    jsd_folder    = os.path.join(session_folder, config.jsd_path)
    synop_folder  = os.path.join(session_folder, config.synop_path)

    os.makedirs(script_folder, exist_ok=True)       
    os.makedirs(log_folder,    exist_ok=True)
    os.makedirs(data_folder,   exist_ok=True)
    os.makedirs(jsd_folder,    exist_ok=True)
    os.makedirs(synop_folder,  exist_ok=True)

# create fits table with each data source used for synoptic map 
def create_src_fits_table(imrec):
    lines = []

    for src, group in groupby(imrec, key=lambda x: x["src"]):
        group_list = list(group)

        if src =='HMI_COMBINED':
            # get start and end of crln_obs in this HMI group
            max_lon = round(group_list[0]["crln_obs"],2)
            min_lon = round(group_list[-1]["crln_obs"],2)    
            t_rec = f"{group_list[0]['tobs']}-{group_list[-1]['tobs']}"

            # append variables in dictionary (no need to separate files of HMI)
            lines.append({"src": 'HMI',"crln_start": max_lon,"crln_obs": np.nan,"crln_end": min_lon,"t_rec": t_rec})
        else:
            # append phi lines with src and crln_obs (crln_start and crln_end computed afterwards)                                    
            for e in group_list:
                lines.append({"src": 'PHI',"crln_start": np.nan,"crln_obs": round(e["crln_obs"],2),"crln_end": np.nan,"t_rec": e["tobs"]})
    
    def mean_longitude(a, b):
        diff = abs(a - b)
        if diff > 180:return ((a + b + 360) / 2) % 360
        else:return (a + b) / 2
    
    #Compute crln_start and crln_end of each file by taking the mean of crln_obs of consecutive files (PHI case)
    #Recompute crln_start/crln_end of each HMI block by taking the mean with crln_obs of previous/next PHI file (HMI case)
    n=len(lines)
    for i, line in enumerate(lines):
        if line["src"]=='HMI':
            line["crln_start"] = mean_longitude(line["crln_start"], lines[(i-1) % n]['crln_obs'])
            line["crln_end"] = mean_longitude(line["crln_end"], lines[(i+1) % n]['crln_obs'])

            lines[(i-1) % n]["crln_end"] = line["crln_start"]
            lines[(i+1) % n]["crln_start"] = line["crln_end"]
        else:
            if lines[(i-1) % n]['src']!='HMI': line["crln_start"] = mean_longitude(line["crln_obs"], lines[(i-1) % n]["crln_obs"])
            if lines[(i+1) % n]['src']!='HMI': line["crln_end"] = mean_longitude(line["crln_obs"], lines[(i+1) % n]["crln_obs"])

    src_col = np.array([i["src"] for i in lines])
    crlnstart_col = np.array([i['crln_start'] for i in lines])
    crlnobs_col = np.array([i['crln_obs'] for i in lines])
    crlnend_col = np.array([i['crln_end'] for i in lines])
    trec_col = np.array([i['t_rec'] for i in lines])
    
    col1 = fits.Column(name='SRC', format='3A', array=src_col)
    col2 = fits.Column(name='CRLN_START', format='E', array=crlnstart_col)
    col3 = fits.Column(name='CRLN_OBS', format='E', array=crlnobs_col)
    col4 = fits.Column(name='CRLN_END', format='E', array=crlnend_col)
    col5 = fits.Column(name='T_REC', format='47A', array=trec_col)

    table_hdu = fits.BinTableHDU.from_columns([col1, col2, col3, col4, col5])

    return table_hdu


def add_script_header(batch_out, script_name="script.sh"):
    """
    Adds a check_continue function to the batch script to handle Ctrl+C gracefully.
    """
    batch_out.write('#!/bin/bash\n')
    batch_out.write("trap '' SIGINT  # <-- Ignore Ctrl+C\n\n")  
    batch_out.write('check_continue() {\n')
    batch_out.write('  if [ -f "stop_signal" ]; then\n')
    batch_out.write('    echo "[%s $$] Detected stop signal. Exiting before next command."\n'% script_name)
    batch_out.write('    exit 0\n')
    batch_out.write('  fi\n')
    batch_out.write('}\n\n')
        
def add_check_continue(batch_out):
    batch_out.write('check_continue\n')

                    
def find_sh_scripts(directory, prefix=''):
    """Find all .sh files in the given directory."""
    return sorted(glob.glob(os.path.join(directory, '%s*.sh'%prefix)))


def make_handle_sigint(stop_signal_path):
    def handle_sigint(signum, frame):

        global interrupted
        interrupted = True
        print("\n[Python] Ctrl-C detected. Signaling scripts to stop after current step.")
        # Create a file that shell scripts will check for
        with open(os.path.join(stop_signal_path, "stop_signal"), "w") as f:
            f.write("stop")
    return handle_sigint


def run_bash_scripts(config, session_folder, verbose=False, prefix=''):

    if verbose: print("Running DRMS bash scripts...")

    outpath_scripts = os.path.join(session_folder, config.script_path)
    outpath_logs    = os.path.join(session_folder, config.log_path)
    
    # Change to the script directory to detect the stop signal, change back to cwd at the end
    cwd = os.getcwd()
    os.chdir(outpath_scripts)

    # --- Find all .sh scripts in the directory ---
    scripts = find_sh_scripts(outpath_scripts, prefix)
    processes = []

    #signal.signal() is a Python function that registers a signal handler.
    #signal.SIGINT represents the interrupt signal generated by pressing Ctrl+C in the terminal.
    #handle_sigint is the function you want Python to call when SIGINT occurs.
    signal.signal(signal.SIGINT, make_handle_sigint(outpath_scripts))

    try:
        for script_path in scripts:
            script_name = os.path.basename(script_path)
            log_path = os.path.join(outpath_logs, script_name.replace('.sh', '.log'))
            #pid_path = os.path.join(outpath_logs, script_name.replace('.sh', '.pid'))

            # Make script executable
            subprocess.call(['chmod', '755', script_path])

            # Open log file
            log_file = open(log_path, 'w')

            # Launch script
            if verbose: print('Running %s... Check %s for progress.' %(script_name, config.log_path))
            p = subprocess.Popen([script_path], stdout=log_file, stderr=subprocess.STDOUT)
            processes.append(p)

            # Save PID
            #with open(pid_path, 'w') as f:
            #    f.write(str(p.pid))

        # Optional: wait for all to complete
        for p in processes:
            p.wait()

    except Exception as e:
        print(f"[Python] Exception: {e}")
    finally:
        # Cleanup
        if os.path.exists(os.path.join(outpath_scripts, "stop_signal")):
            os.remove(os.path.join(outpath_scripts, "stop_signal"))

        # Restore default behavior for Ctrl+C
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        os.chdir(cwd)
        print("[Python] Done.")


def get_phi_filenames(phi_dbpath,date_st,date_end,key,verbose=False):

    pathda=os.path.join(str(phi_dbpath), '')            # Data directory

    t0 = datetime.strptime(date_st, '%Y-%m-%d').date()
    t1 = datetime.strptime(date_end,'%Y-%m-%d').date()
    prefix = 'solo_L2_phi-fdt-'+key+'_*.fits.gz'
    files=[]
    for i in range((t1-t0).days+1):
        T=(t0 + timedelta(days=i)).strftime('%Y-%m-%d')
        date_files=glob.glob(pathda+T+'/'+prefix)
        if isinstance(date_files, str):
            files.append(os.path.join(T,os.path.basename(date_files)))
        elif isinstance(date_files, list):
            for onefile in  date_files:
                files.append(os.path.join(T,os.path.basename(onefile)))

    files = sorted(files)

    return files



def get_dataseries_count(data_series, period, interval):
    
    si_string = "show_info -iP %s[%s%s]" %(data_series, period, interval)
    wc_string = "%s | wc -l" % si_string
    
    wc_out = int(subprocess.check_output(wc_string, shell=True)[:-1].decode("utf-8"))
    
    return wc_out 


def get_dataseries_times(data_series, period, interval):
    
    times = []
    if period == "": return times

    si_string = "show_info -iP %s[%s%s]" %(data_series, period, interval)
    si_out = subprocess.check_output(si_string, shell=True)[:-1].decode("utf-8")
    
    raw = si_out.split('\n') #separate data series from SUMS path
    
    for line in raw[1:]:
        i = line.find('[')
        j = line.find(']')
        times.append(line[i+1:j]) # [clong, cmLong]

    return times 


def get_dates_from_timestring(timestring, drms=False):
    

    # return dates well before PHI or HMI mission start if no timestring is provided
    # this will return empty data lists with any database queries that can't handle None or ""
    if timestring == "": return '2000-01-01', '2000-01-01'

    # Split into all timestamps
    parts = timestring.replace("-", ",").split(",")

    # Parse into datetime objects (strip "_TAI")
    times = [datetime.strptime(p.replace("_TAI", ""), "%Y.%m.%d_%H:%M:%S") for p in parts]

    # Get min and max
    if drms:
        earliest = min(times).strftime("%Y.%m.%d_%H:%M:%S_TAI")
        latest   = max(times).strftime("%Y.%m.%d_%H:%M:%S_TAI")
    else:
        earliest = min(times).strftime("%Y-%m-%d")
        latest   = max(times).strftime("%Y-%m-%d")

    return earliest, latest

def clean_temporary_fits(outpath_data):
    # clean up temporary _drms.fits files from previous runs
    for filename in os.listdir(outpath_data):
        if filename.endswith(".fits"):
            file_path = os.path.join(outpath_data, filename)
            if os.path.isfile(file_path):  # make sure it's a file
                os.remove(file_path)

#OBSOLETE
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

#OBSOLETE
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


#OBSOLETE
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

#if __name__ == "__main__":
    # Example usage
    #create_cr_session_folder()
    #session = get_current_session_folder()
    
    #phi_dbpath = "/data/slam/valori/test_l2_fmdb/FDT_test_release_jan-sep_2022_ghost_corr_update_defringed/l2/"
    #date_st    = "2022-06-03"
    #date_end   = "2022-06-18"
    #key        = "blos"
    #files = get_phi_filenames(config.phi_dbpath, config.date_start, config.date_end, config.key, config.verbose)
    #for i, file in enumerate(files):
    #    print(i, file)
