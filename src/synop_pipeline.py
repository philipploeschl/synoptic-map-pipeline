import os
import subprocess
import argparse

from src.utils.utils import run_all_scripts, get_current_session_folder
from los.drms_preparation import main as drms_main
from los.m720s_drms_pipe import main as hmi_data_main
from los.phi_drms_interface import main as phi_data_main
from los.hmiphisynoptic import main as synop_main

from config.config import Config


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the synoptic pipeline with optional config and session paths."
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config.yaml (uses default parameters if no config is provided)."
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Path to an existing session folder (creates new session if no folder is provided)."
    )
    return parser.parse_args()


if __name__ == "__main__":
    #set cwd to file directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    args = parse_args()

    # Determine session folder
    if args.session:
        session_folder = os.path.abspath(args.session)
    else:
        session_folder = get_current_session_folder() # TODO CHANGE SO IT LOADS PROVIDED SESSION

    # Load config from YAML
    config = Config(config_path=args.config) if args.config else Config()


    if config.run_drms_prep:
        if config.verbose: print("Running 0_drms_prep.py ...")
        #subprocess.call(['python', 'los/0_drms_prep.py'])
        drms_main(config, session_folder)

    if config.run_m720s_drms_pipe:
        if config.verbose: print("Running 1_m720s_drms_pipe.py ...")
        #subprocess.call(['python', 'los/1_m720s_drms_pipe.py'])
        hmi_data_main(config, session_folder)

    if config.run_phi_drms_interface:
        if config.verbose: print("Running 2_phi_drms_interface.py ...")
        #subprocess.call(['python', 'los/2_phi_drms_interface.py'])  
        phi_data_main(config, session_folder)

    # This will run all / only phi/ only hmi scripts in the outpath_scripts directory 
    if config.run_hmi_scripts and config.run_phi_scripts:
        run_all_scripts(verbose=config.verbose)
    elif config.run_phi_scripts:
        run_all_scripts(verbose=config.verbose, prefix='phi')
    elif config.run_hmi_scripts:
        run_all_scripts(verbose=config.verbose, prefix='hmi')

    if config.run_hmiphisynoptic:
        if config.verbose: print("Running 3_hmiphisynoptic.py ...")
        subprocess.call(['python', 'los/3_hmiphisynoptic.py'])
        synop_main(config, session_folder)

    # Todo
    #if config.run_polefilling:
        #subprocess.call(['los/4_polfil.sh'])
    
