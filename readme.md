This is currently abused as a todo list
test
# FEATURES
## Updated session sandling
The session handling now is now done directly from the main wrapper synop_pipeline.py instead of drms_prep.py. This replaces the previous handover via session_path.txt

Full command:

   python synop_pipeline.py --config /path/to/config.yaml --session /path/to/previous/session_folder (optional)

  - required: config.yaml - uses default values for missing parameters or in case no config file is provided (defined in config.py)
  - optional: provide a previous session via --session


## Updated file structure

SYNOPTIC-MAP-PIPELINE
├─ DATA/
│  └─ DRMS/                 # JSD file templates
├─ OUTPUT/                  # set via config.output_path
│  └─ CR_NUMBER_YYYYMMDD_HHMMSS/
│     ├─ DATA/              # PHI data with updated headers for DRMS ingestion
│     ├─ JSD/               # JSD files for DRMS data series creation
│     ├─ LOGS/              # DRMS bash script log files
│     ├─ SCRIPTS/           # DRMS bash scripts
│     ├─ SYNOP/             # synoptic map output in .fits and .pdf
│     └─ config.yaml        # copy of config file of the last session rerun
└─ SRC/
   ├─ synop_pipeline.py
   ├─ data_selection.py
   ├─ CONFIG/
   │  ├─ config.py          # config parser class
   │  └─ example_config.yaml# example config, not read for defaults
   ├─ SYNOP/
   │  ├─ LOS/               # line-of-sight code
   │  └─ VECT/              # vector code (todo)
   └─ UTILS/
      ├─ solepehm.py        # ephemeris functions for hmiphisynoptic.py
      ├─ plots.py           # plotting scripts
      └─ utils.py           # formerly misc.py



## Known issues:
- phi_drms_interface.py:20 hardcodes car_rot = 2258 inside calc_trec() since the logic for the allocation to the  CR doesn't work properly 
- UNTESTED: changing output_path to something outside of the project folder - try that at your own risk if necessary.
- awf_nlim = True has an issue that introduces NaNs into the synoptic map. I already have a lead but it's fairly low on the list since we can just use it without the limiter (set to False)
- python  path/synop_pipeline.py --config=/path/to/config.yaml
  - config path must be absolute or relative to synop_pipeline.py rather than relative to cwd


# TODO

- check if create_series paramters is still necessary after moving sesssion folder handling to the main wrapper. Will I ever run drms_prep.py without creating series now?

- remove previous scripts on rerun of m720s and phi_interface scripts
- consider phi duplicate detection safeguard

- force PHI start magnetogram into data combination (probably in optimisation task)


## Error Handling
- check if DRMS series exists in m720s_drms_pipe and phi_drms_interface and return an error if missing

## Quesitnos for Zhi-Chao
- should we use mps_production or can we define and arbitrary official nmae for us?
- how many parallel processes can we push into drms
- official synoptic map ml and mr remap and maybe the final synop series


## Data Selection
- provide some form of meta data that tracks the data used for each longitude
- data selection through file list that is provided wiht a start and end date and possibly respects exceptions
- get list of carrington rotation periods (start and end time) and find the fastest combination of data for each
- continuous scan of fastest combination independent of carrington rotation (with HMI data spanning 2 CR)

### Design:
- find best combination from existing data
    - from two continously running observations (HMI and PHI)
    - constrained within a single CR to improve HMI maps
    - arbitrary start and end dates crossing CR boundaries for fastest possible combination

- find best combination at defined cadence for a future time window for mission planning
- old design considers  equal spacing in carrington longitude, but in reality we will space in equal observation time increment
  
- refactor and rename carrington_observation_times and carrington_obsrevation_deg
  - clearer name
  - some of hte code is reused and can be outsourced into a function
  - confirm it's working as intended

- figure out why interp360 exists instead of using np.interp(period=360)

- remove obsolete LLD/RSW functionality
- maybe replace it with a list of available observatoin times if the observation cadence isn't constant

- CONTINUE WITH UNDERSTANDING carrington_observation_coverage 

  ### SPICE Kernel Setup
  - git clone --depth 1 https://repos.cosmos.esa.int/socci/scm/spice_kernels/solar-orbiter.git
  - link kernel directory via config.spice_kernel


## General
- check how synptic map pipeline handles noise outliers since PHI might come wiht sqrt(3) difference for onboard averaged data. make sure we don't lose data without noticing
- understand quality bits

### Log functionality
- set up proper logging using the python logging library
- top level log for verbose output of .py scripts
- possibly set up different levels of verbose output




### Session handling
- delete output scripts from previous run when reprocessing in an existing session
- figure out some form of processing history folder, maybe using the synop_pipeline.py log

- processing history - what do I need to save to reproduce the map?
  - config
  - file list of used phi data
  - hmi time stamps
  - phi time stamps
  - phi/hmi data selection
  - most of it can probably 
  - maybe add all this to a ./history/ folder 



## synop_pipeline.py
- check if /output can be replaced wiht an absolute path elsewhere
  

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



## Notes on DRMS discussion with Zhi-Chao
- deleting a data series sets the retention of the stored data to 0, which will be purged during the next cleanup
- deleting a data series immediately deletes meta data

- cancelling DRMS modules with interrupt will CRASH the ENTIRE SYSTEM if it happens during any file ingestion process (e.g. module output writing back into data series)

- HMI.M_720s is updated daily at 7am. Data release lags behind a few days.
- HMI.M_720s_NRT available locally as mps_production.hmi_m_720s_nrt and updated hourly at hh:45
- see https://www2.mps.mpg.de/projects/seismo/GDC-SDO/sums-activity.htm

- DRMS metadata might be available but actual data will be corrupted if it was downloaded from Stanford during periods with GPFS filesystem problems at MPS


# NOTES

- identify los parameter for hmiphisynoptic.py
  - this seems to be tied to a discontinuied DRMS keyword FDRADIAL and only affects the noise thresholds of the synoptic map data selection
    if (radialFound)
          noiseLevel = noiseLevel * MIN(1 / cosrho, maxNoiseAdj);
  - noiseLevel seems to be an obsolete quantity that isn't used in the code anymore




