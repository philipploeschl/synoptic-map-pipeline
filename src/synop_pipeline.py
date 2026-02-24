import os
import subprocess
import argparse

from utils.utils import run_bash_scripts, create_session_folder, create_session_structure
from config.config import Config

from synop.los.drms_preparation_los import main as drms_main_los
from synop.los.hmi_preparation_los import main as hmi_data_main_los
from synop.los.phi_preparation_los import main as phi_data_main_los
from synop.los.hmiphisynoptic_los import main as synop_main_los
from synop.los.polfil_los import main as polfil_los
from synop.los.diagnostics_los import main as diagnostics_los

from synop.vect.drms_preparation_b3c import main as drms_main_b3c
from synop.vect.hmi_preparation_b3c import main as hmi_data_main_b3c
from synop.vect.phi_preparation_b3c import main as phi_data_main_b3c
from synop.vect.hmiphisynoptic_b3c import main as synop_main_b3c
from synop.vect.polfil_b3c import main as polfil_b3c
from synop.vect.diagnostics_b3c import main as diagnostics_b3c


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
        

        if config.run_hmi_prep:
            if config.verbose: print("Running hmi_preparation_b3c.py ...")

            status = hmi_data_main_b3c(config, session_folder)

            if status != STATUS_OK: 
                exit()
        

        if config.run_phi_prep:
            if config.verbose: print("Running phi_preparation_b3c.py ...")

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


        if config.run_polefilling:
            if config.verbose: print("Running polfil_b3c.py ...")

            status = polfil_los(config, session_folder)

            if status != STATUS_OK: 
                exit()


        if config.run_diagnostics:
            if config.verbose: print("Running diagnostics_b3c.py ...")
            
            status = diagnostics_b3c(config, session_folder)
        
            if status != STATUS_OK: 
                exit()

        

    else:
        # LINE OF SIGHT PIPELINE
        if config.run_drms_prep:
            if config.verbose: print("Running drms_preparation_los.py ...")

            status = drms_main_los(config, session_folder)

            if status != STATUS_OK: 
                exit()


        if config.run_hmi_prep:
            if config.verbose: print("Running hmi_preparation_los.py ...")

            status = hmi_data_main_los(config, session_folder)
            
            if status != STATUS_OK: 
                exit()
            

        if config.run_phi_prep:
            if config.verbose: print("Running phi_preparation_los.py ...")

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
            if config.verbose: print("Running hmiphisynoptic_los.py ...")

            status = synop_main_los(config, session_folder)

            if status != STATUS_OK: 
                exit()
            

        if config.run_polefilling:
            if config.verbose: print("Running polfil_los.py ...")

            status = polfil_los(config, session_folder)

            if status != STATUS_OK: 
                exit()


        if config.run_diagnostics:
            if config.verbose: print("Running diagnostics_los.py ...")
            
            status = diagnostics_los(config, session_folder)

            if status != STATUS_OK: 
                exit()
            
# python src/synop_pipeline.py --config=config.yaml --session=/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/output/multi-source-test/