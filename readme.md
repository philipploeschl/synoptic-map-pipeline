
# TODO

## misc.py
- update nohup script to communicate when all PIDs are done

## 1_m720s_drms_pipe.py



## 2_phi_drms_interface.py
- adapt script paths to new file structure
- add compatibility with config.run_phi_scripts
- clean up old code
- why is car_rot hard coded in calc_trec()?

## Data selection
- TBD


# File structure
output/session_path.txt stores current session path. This file is written by 0_drms_prep.py and read from all consecutive scripts.

File structure created in misc.py: create_session_folder
 - OUTPUT_PATH/
   - CR_NUMBER_YYYYMMDD_HHMMSS
       - DATA
       - SCRIPTS   
       - LOGS

