import os
import subprocess
import argparse

from utils.utils import run_bash_scripts, create_session_folder, create_session_structure
from synop.los.drms_preparation import main as drms_main_los
from synop.los.m720s_drms_pipe import main as hmi_data_main_los
from synop.los.phi_drms_interface import main as phi_data_main_los
from synop.los.hmiphisynoptic import main as synop_main_los
from synop.los.diagnostics import main as diagnostics_los

from synop.vect.drms_preparation_b3c import main as drms_main_b3c
from synop.vect.m720s_drms_pipe_b3c import main as hmi_data_main_b3c
from synop.vect.phi_drms_interface_b3c import main as phi_data_main_b3c
from synop.vect.hmiphisynoptic_b3c import main as synop_main_b3c
#from synop.vect.diagnostics import main as diagnostics_b3c

from config.config import Config

STATUS_OK = 0

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

    # Load config from YAML
    config = Config(config_path=args.config) if args.config else Config()

    # Determine session folder
    if args.session:
        session_folder = os.path.abspath(args.session)
        create_session_structure(config, session_folder)
    else:
        session_folder = create_session_folder(config) 
        
    config.save(output_path=session_folder)

    if config.b3c:
        # VECTOR PIPELINE
        if config.run_drms_prep:
            if config.verbose: print("Running drms_preparation_b3c.py ...")
            
            status = drms_main_b3c(config, session_folder)

            if status != STATUS_OK: 
                exit()
        

        if config.run_m720s_drms_pipe:
            if config.verbose: print("Running m720s_drms_pipe_b3c.py ...")

            status = hmi_data_main_b3c(config, session_folder)

            if status != STATUS_OK: 
                exit()
        

        if config.run_phi_drms_interface:
            if config.verbose: print("Running phi_drms_interface_b3c.py ...")

            status = phi_data_main_b3c(config, session_folder)

            if status != STATUS_OK: 
                exit()
            
            
        # This will run all / only phi/ only hmi scripts in the outpath_scripts directory 
        if config.run_hmi_scripts and config.run_phi_scripts:
            run_bash_scripts(config, session_folder, verbose=config.verbose)
        elif config.run_phi_scripts:
            run_bash_scripts(config, session_folder, verbose=config.verbose, prefix='phi')
        elif config.run_hmi_scripts:
            run_bash_scripts(config, session_folder, verbose=config.verbose, prefix='hmi')

        if config.run_hmiphisynoptic:
            if config.verbose: print("Running hmiphisynoptic_b3c.py ...")
            
            status = synop_main_b3c(config, session_folder)

            if status != STATUS_OK: 
                exit()

        #if config.run_diagnostics:
        #    if config.verbose: print("Running diagnostics_b3c.py ...")
        #    
        #    status = diagnostics_b3c(config, session_folder)
        #
        #    if status != STATUS_OK: 
        #        exit()

    else:
        # LINE OF SIGHT PIPELINE
        if config.run_drms_prep:
            if config.verbose: print("Running drms_preparation.py ...")

            status = drms_main_los(config, session_folder)

            if status != STATUS_OK: 
                exit()

        if config.run_m720s_drms_pipe:
            if config.verbose: print("Running m720s_drms_pipe.py ...")

            status = hmi_data_main_los(config, session_folder)
            
            if status != STATUS_OK: 
                exit()
            
        if config.run_phi_drms_interface:
            if config.verbose: print("Running phi_drms_interface.py ...")

            status = phi_data_main_los(config, session_folder)
            
            if status != STATUS_OK: 
                exit()
        
        # This will run all / only phi/ only hmi scripts in the outpath_scripts directory 
        if config.run_hmi_scripts and config.run_phi_scripts:
            run_bash_scripts(config, session_folder, verbose=config.verbose)
        elif config.run_phi_scripts:
            run_bash_scripts(config, session_folder, verbose=config.verbose, prefix='phi')
        elif config.run_hmi_scripts:
            run_bash_scripts(config, session_folder, verbose=config.verbose, prefix='hmi')

        if config.run_hmiphisynoptic:
            if config.verbose: print("Running hmiphisynoptic.py ...")

            status = synop_main_los(config, session_folder)

            if status != STATUS_OK: 
                exit()
            
        # Todo
        #if config.run_polefilling:
            #subprocess.call(['los/4_polfil.sh'])

        if config.run_diagnostics:
            if config.verbose: print("Running diagnostics.py ...")
            
            status = diagnostics_los(config, session_folder)

            if status != STATUS_OK: 
                exit()
            
# python src/synop_pipeline.py --config=config.yaml --session=/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/output/multi-source-test/