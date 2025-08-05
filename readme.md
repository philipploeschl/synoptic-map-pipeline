This is currently abused as a todo list

# TODO

## synop_pipeline.py
- confirm that 1_m720s_drms_pipe.py command and process output lands in the same log file

## 1_m720s_drms_pipe.py



## 2_phi_drms_interface.py
- clean up old code
- why is car_rot hard coded in calc_trec()?


## Data selection
- TBD

## Discussion points on DRMS series handling with Zhi-caho
- what happens when we delete data series?
  - will the data be deleted along with it?
  - will it stay until the retention period?
  - will it only get deleted in a data purge if the retetion period is expired?
  - will the purge still work if the data series was deleted?  

- can we download hmi.m_720s daily instead of weekly?


# File structure
output/session_path.txt stores current session path. This file is written by 0_drms_prep.py and read from all consecutive scripts.

File structure created in misc.py: create_session_folder
 - OUTPUT_PATH/
   - CR_NUMBER_YYYYMMDD_HHMMSS
       - DATA
       - SCRIPTS   
       - LOGS

