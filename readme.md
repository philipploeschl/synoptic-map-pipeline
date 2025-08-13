This is currently abused as a todo list

# TODO

## Known issues:
- 2_phi_drms_interface.py:20 hardcodes car_rot = 2258 inside calc_trec() since the logic for the allocation to the  CR doesn't work properly 
- I've never tested changing output_path to something outside of the project folder yet so try that at your own risk if necessary.
- awf_nlim = True has an issue that introduces NaNs into the synoptic map. I already have a lead but it's fairly low on the list since we can just use it without the limiter (set to False)



## General
- check how synptic map pipeline handles noise outliers since PHI might come wiht sqrt(3) difference for onboard averaged data. make sure we don't lose data without noticing
- understand quality bits

### Log functionality
- set up proper logging using the python logging library
- top level log for verbose output of .py scripts
- possibly set up different levels of verbose output

### Config updates
- split config into user_config.py and pipeline_config.py
- provide config as argv to synop_pipeline.py?
- read config from session_path/config/ if previous session is provided?

- what do I need to save to reproduce the map?
  - config
  - file list of used phi data
  - hmi time stamps
  - phi time stamps
  - phi/hmi data selection
  - most of it can probably 
  - maybe add all this to a ./history/ folder 


### Session handling
- Move session creation logic into this file and replace python file calls with direct function calls
  - python synop_pipeline.py --config=/path/to/config.py -> creates new session folder and saves the config into that folder
  - python synop_pipeline.py --session=/path/to/session_folder/ loads a previous session and uses the config from that folder
  - python synop_pipeline.py without command line arguments will default to config.py in sim/los/
- load config in synop_pipeline.py and pass it to sub routine calls along with the session folder
- direct execution of python sub routines will continued to be supported via their respective "if __name__ = "__main__":" structures
- session_path.txt obsolete due to replacing inter-script communication with direct calls
- ./script/ output cleanup advisable for repeated processing in a single session
- split up config.py into pipeline speciifc pipeline_config.py and Carrington rotation specific user/session_config.py?
  - possibly only for previous session calls where configs are loaded from /session_path/config/

- delete output scripts from previous run when reprocessing in an existing session

- figure out some form of processing history folder, maybe using the synop_pipeline.py log


- the above concept won't work with importing a config python file
- there is some general fuckery with the file structure and imports
- config.py currently can't cleanly be imported from src/los/ if it is located in the root directory
- the project has to properly be rearranged as a package -> talk to Johannes
- where will I put synop_pipeline.py, data_selection.py? leave in src or move up to root?
- moving the file structure around fucks up all the file pat definitions -> always make a full test run and see if the outputs land in the right locations


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



## 3_hmiphisynoptic.py
- change the data input to accept dedicated phi and hmi data series and do the T_REC remapping right there to allow for permanent production data series
  - this will require adaptations in 2_phi_drms_interface.py
  - no need to save phi.fits with updated header if it's possible to directly ADD keywords with set_info
    -> ingest and add keywords instead

    
- isolate adaptive weight function code to properly understand and document it again
- figure out why data in synoptic output is missing
- write synop.fits back into drms

- debug runtime warning on CR2258 synoptic processing:
  /scratch/slam/loeschl/dev/python/synop/sim/los/3_hmiphisynoptic.py:1087: RuntimeWarning: invalid value encountered in scalar divide
  synVal = sumfinal / wtfinal #nptsfinal          #float synVal = sumfinal / nptsfinal;


- identify los parameter for hmiphisynoptic.py
  - this seems to be tied to a discontinuied DRMS keyword FDRADIAL and only affects the noise thresholds of the synoptic map data selection
    if (radialFound)
          noiseLevel = noiseLevel * MIN(1 / cosrho, maxNoiseAdj);
  - noiseLevel seems to be an obsolete quantity that isn't used in the code anymore

- Adaptive Weight Function
  - code relies on images taken from the ecliptic
  - latitude specific weight function control needs to consider out of ecliptic observations
  - understand awf_lim and describe it properly
  - force uneven number for awf_nimg


## Data selection
- switch to official github kernel
- provide some form of meta data that tracks the data used for each longitude
- data selection through file list that is provided wiht a start and end date and possibly respects exceptions


## Gherardo talking points
- old and new 3_hmiphisynoptic.py scripts are confirmed to be identical
- plan to move to python based function calls in synop_pipeline.py for new session handling
- current limitations with awf_lim parameter - don't use for now (leave it False)
- identify los parameter for hmiphisynoptic.py
  - this seems to be tied to a discontinuied DRMS keyword FDRADIAL and only affects the noise thresholds of the synoptic map data selection
    if (radialFound)
          noiseLevel = noiseLevel * MIN(1 / cosrho, maxNoiseAdj);
  - noiseLevel seems to be an obsolete quantity that isn't used in the code anymore
- carrot = 2258 currently hardcoded in 2_phi_drms_interface.py
  - this will be fixed once the automatic data_selection is operational
- direct fmdb access implemented
- separate nparallel parameters for phi and hmi since it doesn't make sense to split both 1500 (hmi) and 50 (phi) files into the same amount of processes


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



# SPICE Kernel Setup
- git clone --depth 1 https://repos.cosmos.esa.int/socci/scm/spice_kernels/solar-orbiter.git
- link kernel directory via config.spice_kernel