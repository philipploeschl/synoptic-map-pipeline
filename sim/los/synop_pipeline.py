# call 0_drms_prep.py to create JSD files and data series in DRMS
# call 1_m720s_drms_pipe.py to create the hiresmap and remap
# call 2_phi_drms_interface.py to create the phi data series
# call 4_hmisynoptic.py to create the synoptic maps

# 0 -> 1,2 in parallel -> 4
# scripts 1, 2 need pid id monitoring to know when they are finished
# 4 needs to wait for 1,2 to finish

import os
import time
import subprocess
import config
import glob
from misc import run_all_scripts, get_current_session_folder



if __name__ == "__main__":

    #set cwd to file directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if config.run_drms_prep:
        subprocess.call(['python', '0_drms_prep.py'])

    if config.run_m720s_drms_pipe:
        subprocess.call(['python', '1_m720s_drms_pipe.py'])

    if config.run_phi_drms_interface:
        subprocess.call(['python', '2_phi_drms_interface.py'])  

    # This will run all / only phi/ only hmi scripts in the outpath_scripts directory 
    if config.run_hmi_scripts and config.run_phi_scripts:
        run_all_scripts(verbose=config.verbose)
    elif config.run_phi_scripts:
        run_all_scripts(verbose=config.verbose, prefix='phi')
    elif config.run_hmi_scripts:
        run_all_scripts(verbose=config.verbose, prefix='hmi')

    if config.run_hmiphisynoptic:
        subprocess.call(['python', '4_hmisynoptic.py'])


