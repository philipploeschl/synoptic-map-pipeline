import os
import subprocess
import config
from src.misc import run_all_scripts, get_current_session_folder

# ToDo:
# - Move session creation logic into this file and replace python file calls with direct function calls
#   - python synop_pipeline.py --config=/path/to/config.py -> creates new session folder and saves the config into that folder
#   - python synop_pipeline.py --session=/path/to/session_folder/ loads a previous session and uses the config from that folder
#   - python synop_pipeline.py without command line arguments will default to config.py in sim/los/
# - load config in synop_pipeline.py and pass it to sub routine calls along with the session folder
# - direct execution of python sub routines will continued to be supported via their respective "if __name__ = "__main__":" structures
# - session_path.txt obsolete due to replacing inter-script communication with direct calls
# - ./script/ output cleanup advisable for repeated processing in a single session
# - split up config.py into pipeline speciifc pipeline_config.py and Carrington rotation specific session_config.py?
#   - possibly only for previous session calls where configs are loaded from /session_path/config/


if __name__ == "__main__":

    #set cwd to file directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if config.run_drms_prep:
        if config.verbose: print("Running 0_drms_prep.py ...")
        subprocess.call(['python', './src/los/0_drms_prep.py'])
        # 0_drms_prep.main(config, session_folder)

    if config.run_m720s_drms_pipe:
        if config.verbose: print("Running 1_m720s_drms_pipe.py ...")
        subprocess.call(['python', './src/los/1_m720s_drms_pipe.py'])
        # 1_m720s.drms_pipe.main(config, session_folder)

    if config.run_phi_drms_interface:
        if config.verbose: print("Running 2_phi_drms_interface.py ...")
        subprocess.call(['python', './src/los/2_phi_drms_interface.py'])  
        # 2_phi_drms_interface.main(config, session_folder)

    # This will run all / only phi/ only hmi scripts in the outpath_scripts directory 
    if config.run_hmi_scripts and config.run_phi_scripts:
        run_all_scripts(verbose=config.verbose)
    elif config.run_phi_scripts:
        run_all_scripts(verbose=config.verbose, prefix='phi')
    elif config.run_hmi_scripts:
        run_all_scripts(verbose=config.verbose, prefix='hmi')

    if config.run_hmiphisynoptic:
        if config.verbose: print("Running 3_hmiphisynoptic.py ...")
        subprocess.call(['python', './src/los/3_hmiphisynoptic.py'])
        # 3_hmiphisynoptic.main(config, session_folder)

    # Todo
    #if config.run_polefilling:
        #subprocess.call(['./src/los/4_polfil.sh'])
    


