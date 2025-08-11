This is currently abused as a todo list

# TODO

## up next
- implement new_session/load_session functionality
- identify los parameter for hmiphisynoptic.py
  - this seems to be tied to a discontinuied DRMS keyword FDRADIAL and only affects the noise thresholds of the synoptic map data selection
    if (radialFound)
          noiseLevel = noiseLevel * MIN(1 / cosrho, maxNoiseAdj);
  - noiseLevel seems to be an obsolete quantity that isn't used in the code anymore
- figure out ./history folder



## General

### Log functionality
- set up proper logging using the python logging library
- top level log for verbose output of .py scripts
- possibly set up different levels of verbose output

### Config updates
- split config into user_config.py and pipeline_config.py
- provide config as argv to synop_pipeline.py?
- read config from session_path/config/ if previous session is provided?

- what do I need to save to reproduce the map
  - config
  - file list of used phi data
  - hmi time stamps
  - phi time stamps
  - phi/hmi data selection
  - most of it can probably 
  - maybe add all this to a ./history/ folder 

### Session handling
- implement new_session/load_session functionality
  - change synop_pipeline.py to directly call each steps main() file and pass main(config, session_folder)
  - new_session = True creates new session folder
  - new_session = False loads session defined in output_path+prev_session
  - OR just providing a config creates a new session, and providing a sessoin reads an old config -> no extra config parameters required
  - removal of inter-python communication makes session_path.txt obsolete

- delete output scripts from previous run when reprocessing in an existing session


## synop_pipeline.py
- check if /output can be replaced wiht an absolute path elsewhere
- implement new_session/load_session functionality
  

## 1_m720s_drms_pipe.py
- python script verbose output logging?
- add functionality for separate bash scripts created from nrt


## 2_phi_drms_interface.py
- option for .sh scripts only
- clean up old code
- python script verbose output logging?
- why is car_rot hard coded in calc_trec()?
  - logic doesn't seem to work in current implementation
  - Hard coding 2258 makes sure that the 0-86° data is assigned to 2258 instead of 2257.
  - not using this will result in missing data for lower longitudes for the 2258 test data



## 4_hmiphisynoptic.py
- consider changing the data input to accept dedicated phi and hmi data series and do the T_REC remapping right there to allow for permanent production data series
- isolate adaptive weight function code to properly understand and document it again
- figure out why data in synoptic output is missing
- write synop.fits back into drms

- debug runtime warning on CR2258 synoptic processing:
  /scratch/slam/loeschl/dev/python/synop/sim/los/4_hmiphisynoptic.py:1087: RuntimeWarning: invalid value encountered in scalar divide
  synVal = sumfinal / wtfinal #nptsfinal          #float synVal = sumfinal / nptsfinal;


## Data selection
- switch to official github kernel
- 


## Notes on DRMS discussion with Zhi-Chao
- deleting a data series sets the retention of the stored data to 0, which will be purged during the next cleanup
- deleting a data series immediately deletes meta data

- cancelling DRMS modules with interrupt will CRASH the ENTIRE SYSTEM if it happens during any file ingestion process (e.g. module output writing back into data series)

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

