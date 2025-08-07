This is currently abused as a todo list

# TODO
## General
- bulk data processing with jv2ts and resizemappingmag could work again after the maximum processing time on DRMS was increased to 24h 
- Do we care? Should we adapt .sh script creation accordingly or keep it for easy0 parallelization?


## synop_pipeline.py
- INTERRUPTING a script during DRMS data INGESTION with set_info will CRASH DRMS SERVERWIDE

## 1_m720s_drms_pipe.py
- python script verbose output logging?


## 2_phi_drms_interface.py
- option for .sh scripts only
- clean up old code
- why is car_rot hard coded in calc_trec()?
- reorder phi_remap.sh to cluster set_info commands in the beginning to minimize chances of crashing DRMS on interrupt
- python script verbose output logging?

## 4_hmiphisynoptic.py
- consider changing the data input to accept dedicated phi and hmi data series and do the T_REC remapping right there to allow for permanent production data series
- isolate adaptive weight function code to properly understand and document it again
- figure out why data in synoptic output is missing

## Data selection
- switch to official github kernel
- 

## Discussion points on DRMS series handling with Zhi-Chao
- deleting a data series sets the retention of the stored data to 0, which will be purged during the next cleanup
- deleting a data series immediately deletes meta data

- cancelling DRMS modules with interrupt will CRASH the ENTIRE SYSTEM if it happens during file ingestion 

- can we download hmi.m_720s daily instead of weekly?
- does drms crash independently on swan25 or this yesterday's outage affect everyone?

- HMI.M_720s is updated daily at 7am. Data release lags behind a few days.
- HMI.M_720s_NRT available locally as mps_production.hmi_m_720s_nrt and updated hourly at hh:45
- see https://www2.mps.mpg.de/projects/seismo/GDC-SDO/sums-activity.htm

- DRMS metadata might be available but actual data will be corrupted if it was downloaded from Stanford during periods with GPFS filesystem problems at MPS


# File structure
output/session_path.txt stores current session path. This file is written by 0_drms_prep.py and read from all consecutive scripts.

File structure created in misc.py: create_session_folder
 - OUTPUT_PATH/
   - CR_NUMBER_YYYYMMDD_HHMMSS
       - DATA
       - SCRIPTS   
       - LOGS

