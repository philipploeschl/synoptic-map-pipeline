# The SO/PHI & SDO/HMI Synoptic Map Pipeline



This project is based on the [SDO/HMI synoptic map pipeline](http://jsoc.stanford.edu/doxygen_html/main.html) and [NetDRMS](http://jsoc.stanford.edu/jsocwiki/DRMSSetup)

## Table of Contents

- [The SO/PHI \& SDO/HMI Synoptic Map Pipeline](#the-sophi--sdohmi-synoptic-map-pipeline)
  - [Table of Contents](#table-of-contents)
  - [Installation (WIP)](#installation-wip)
    - [1. Clone the Repository](#1-clone-the-repository)
    - [2. Set Up a Virtual Environment (Optional but Recommended)](#2-set-up-a-virtual-environment-optional-but-recommended)
    - [3. Install Dependencies](#3-install-dependencies)
    - [4. Activate NetDRMS (MPS specific)](#4-activate-netdrms-mps-specific)
  - [Usage](#usage)
  - [Directory Structure](#directory-structure)
  - [Configuration](#configuration)
    - [Pipeline Main Function](#pipeline-main-function)
    - [DRMS Data Series Setup](#drms-data-series-setup)
    - [Data Processing](#data-processing)
      - [SDO/HMI Data Processing](#sdohmi-data-processing)
      - [SO/PHI Data Processing](#sophi-data-processing)
    - [Synoptic Map Processing](#synoptic-map-processing)
    - [Data Selection](#data-selection)
  - [Known issues](#known-issues)
  - [Citations / References](#citations--references)
  - [Acknowledgements](#acknowledgements)
  - [License](#license)
  


## Installation (WIP)
TODO: confirm that this section works (ChatGPT output)

To get started with the **synoptic-map-pipeline**, follow these steps:

### 1. Clone the Repository
Use Git to clone the repository to your local machine:

```bash
git clone https://gitlab.gwdg.de/philipp.loeschl/synoptic-map-pipeline.git
cd synoptic-map-pipeline
```

### 2. Set Up a Virtual Environment (Optional but Recommended)
Creating a virtual environment helps manage dependencies and avoid conflicts with other projects:

```bash
python -m venv venv
```

Activate the virtual environment:

- Windows:

```bash
.\venv\Scripts\activate
```

- macOS/Linux:

```
source venv/bin/activate
```

### 3. Install Dependencies
TODO: actually provide requirements.txt file

Install the required Python packages:
```bash
pip install -r requirements.txt
```

Note: If you encounter issues with pip, ensure it's up to date:
```
python -m pip install --upgrade pip
```

### 4. Activate NetDRMS (MPS specific)

```
module load intel-compilers/2023.1.0
module load impi/2021.9.0
module load NetDRMS/2024.02.1-1
```

NetDRMS path and relevant directories
```
/sw/eb/NetDRMS/2024.02.1-1-intel-2023.03/

/sw/eb/NetDRMS/2024.02.1-1-intel-2023.03/src/mag/synop/apps/
/sw/eb/NetDRMS/2024.02.1-1-intel-2023.03/src/globalhs/libs/projection/
/sw/eb/NetDRMS/2024.02.1-1-intel-2023.03/src/mag/remapmags/apps/

/sw/eb/NetDRMS/2024.02.1-1-intel-2023.03/src/mag/pfss/apps/
/sw/eb/NetDRMS/2024.02.1-1-intel-2023.03/src/mag/polcorr/apps/
```


## Usage
  Direct lauch from terminal with compatible active python environment:

   _python synop_pipeline.py --config /path/to/config.yaml --session /path/to/previous/or/current/session_folder (optional)_

  - config (required)
    - accepts absolute path to config.yaml or relative path wrt to synop_pipeline.py
    - uses default values (defined in config.py) for missing parameters or in case no config file is provided 

  - session (optional)
    - functions as output path and works as either
      - path to a previous session/simulation with existing output folder structure
      - path to a new session/simulation for which the output folder structure is created
    - recommended use:
      - provide --session /absolute/path/to/output/directory/


## Directory Structure

```yaml
SYNOPTIC-MAP-PIPELINE
├─ DATA/
│  └─ DRMS/                  # JSD file templates
├─ OUTPUT/                   # set via config.output_path
│  └─ SESSION_FOLDER_NAME/
│     ├─ DATA/               # PHI data with updated headers for DRMS ingestion
│     ├─ JSD/                # JSD files for DRMS data series creation
│     ├─ LOGS/               # DRMS bash script log files
│     ├─ SCRIPTS/            # DRMS bash scripts
│     ├─ SYNOP/              # synoptic map output in .fits and .pdf
│     └─ config.yaml         # copy of config file of the last session rerun
└─ SRC/
   ├─ synop_pipeline.py
   ├─ data_selection.py
   ├─ CONFIG/
   │  ├─ config.py           # config parser class
   │  └─ example_config.yaml # example config, not read for defaults
   ├─ SYNOP/
   │  ├─ LOS/                # line-of-sight code
   │  │  ├─ drms_preparation.py
   │  │  ├─ m720s_drms_pipe.py
   │  │  ├─ phi_drms_interface.py
   │  │  └─ hmiphisynoptic.py
   │  └─ VECT/               # vector code (todo)
   └─ UTILS/
      ├─ solepehm.py         # ephemeris functions for hmiphisynoptic.py
      ├─ plots.py            # plotting scripts
      └─ utils.py            # formerly misc.py
```




## Configuration
### Pipeline Main Function
_src/los/synop_pipeline.py_


TODO DESCRIPTION


```yaml
###########################################################
################# Pipeline Configuration ##################
###########################################################

run_drms_prep:           True  # run drms_prep.py to create JSD files and data series in DRMS
run_m720s_drms_pipe:     True  # run m720s_drms_pipe.py to create the hiresmap and remap
run_phi_drms_interface:  True  # run phi_drms_interface.py to create the phi data series

run_hmi_scripts:         True  # run all HMI scripts in the outpath_scripts directory 
run_phi_scripts:         True  # run all PHI scripts in the outpath_scripts directory 

run_hmiphisynoptic:      True  # run hmiphisynoptic.py to create the synoptic maps
run_polefilling:         False # run all synoptic map pole filling


###########################################################
#################### Global parameters ####################
###########################################################

# Enable verbose output
verbose: True

# Session ID, also used as data series appendix e.g. "FDT_test_release_june_2022_defri" for FDT test release june 2022 defringed      
id: "pipeline_test" # DEPCRECATED 

# database path for new implementation
#phi_dbpath: "/data/solo/phi/data/fmdb/public/l2" # public fmdb
phi_dbpath: "/data/slam/valori/test_l2_fmdb/polar_2025/v01/l2" # experimental fmdb branch

#date_start: "2022-06-03" # YYYY-MM-DD # PROBABLY OBSOLETE, NOW USING TIMESTRING_PHI --IGNORE--
#date_end  : "2022-06-18" # YYYY-MM-DD # PROBABLY OBSOLETE, NOW USING TIMESTRING_PHI --IGNORE--
key       : "blos"       # data segment


# Output path for DRMS scripts relative (relative to synop/)- e.g. synop/output/CR_NUMBER_SESSION_ID/
output_path: 'output/'

script_path: 'scripts/' # path to bash scripts, relative to synop/output/CR_NUMBER_SESSION_ID/
log_path   : 'logs/'    # path to log files, relative to synop/output/CR_NUMBER_SESSION_ID/
data_path  : 'data/'    # path to data files, relative to synop/output/CR_NUMBER_SESSION_ID/
jsd_path   : 'jsd/'     # path to JSD files, relative to synop/output/CR_NUMBER_SESSION_ID/
synop_path : 'synop/'   # path to synoptic maps, relative to synop/output/CR_NUMBER_SESSION_ID/
obsplan_path: 'observation_plan/' # path to data selection output

# File structure created in misc.py: create_session_folder
# - OUTPUT_PATH/
#   - CR_NUMBER_YYYYMMDD_HHMMSS
#       - DATA
#       - SCRIPTS   
#       - LOGS
#       - JSD
#       - SYNOP

# path to JSD templates, relative to synop/
template_path: "data/drms/templates/" 

```

### DRMS Data Series Setup 
_src/los/drms_preparation.py_

```yaml
###########################################################
################# Data series definition ##################
###########################################################

# Ml/Mr selection -> False: Blos, True: Mr
Mr: False 

# Carrington rotation number (primary key for synoptic maps)
cr: 2297 # POSSIBLY OBSOLETE, NOW USING MOST COMMON CR FROM TIMESTRING_HMI/PHIs

# owner of temporary data series, used for output file names
dataseries_owner: "mps_loeschl"

data_series_phi      : "mps_loeschl.phi_M"           #  mps_phi.something
data_series_jv2ts_phi: "mps_loeschl.phi_Ml_hiresmap"  # "mps_loeschl.Ml_hiresmap_720s_test"
data_series_remap_phi: "mps_loeschl.phi_Ml_remap"     # "mps_loeschl.Ml_remap_720s_test"

data_series_hmi      : "hmi.M_720s"                   # "mps_production.hmi_m_720s_nrt"
data_series_jv2ts_hmi: "mps_loeschl.hmi_Ml_hiresmap"  # "mps_loeschl.Ml_hiresmap_720s_test"
data_series_remap_hmi: "mps_loeschl.hmi_Ml_remap"     # "mps_loeschl.Ml_remap_720s_test"

data_series_synop :    "mps_loeschl.synoptic_Ml"         # synoptic data series name
data_series_polfil:    "mps_loeschl.synoptic_Mr_polfil"  # synoptic Mr polfil data series name


# toggle creation jsd files for data series
create_jsd_phi         : True 
create_jsd_hiresmap_phi: True
create_jsd_remap_phi   : True

create_jsd_hiresmap_hmi: True
create_jsd_remap_hmi   : True

create_jsd_synoptic    : True 
create_jsd_polfil      : False

remap_template   : "remap_template.jsd"              # template for remap data series
hiresmap_template: "hiresmap_template.jsd"           # template for hiresmap data series
phi_template     : "phi_template.jsd"                # template for phi data series            
synoptic_template: "synoptic_template.jsd"           # template for synoptic data series
polfil_template  : "synoptic_mr_polfil_template.jsd" # template for polfil data series

# Toggle data series creation from above JSD files in DRMS
create_series: True

# Use temporary data series based on ID and CR number
use_temp_series: False
```


### Data Processing


```yaml
###########################################################
################### HMI & PHI Processing ##################
###########################################################

# HMI source data series 
#dataseries_input: "hmi.M_720s" # "mps_production.hmi_m_720s_nrt" # OBSOLETE MOVED TO data_series_hmi  

# HMI cadence for the M_720s data series - default/nothing: @12min, change HMI cadence for fast prototyping
interval_hmi: "@12m"
interval_phi: "@12m"

# Exclude already processed datasets
filter_duplicates_hmi: False
filter_duplicates_phi: True

# split batch scripts after nsplit entries
nparallel_hmi: 10  # number of parallel HMI DRMS shell scripts
nparallel_phi: 1   # number of parallel PHI DRMS shell scripts

hmi_maprmax: 0.998  # HMI default value
phi_maprmax: 0.9925 # maximum radius for the synoptic map
```

#### SDO/HMI Data Processing 
_src/los/m720s_drms_pipe.py_


#### SO/PHI Data Processing 
_src/los/phi_drms_interface.py_




### Synoptic Map Processing 
_src/los/hmiphisynoptic.py_

```yaml
###########################################################
################# Synoptic Map Processing #################
###########################################################

# Timestrings or HMI and PHI data selection, don't add interval "@12m" here
# it's added automatically from "interval_hmi" and "intervaL_phi" parameters
# and will crash if you add it here
# cr2297
timestring_hmi: "2025.04.27_00:56:26_TAI-2025.05.10_12:56:26_TAI"
timestring_phi: "2025.05.09_12:56:26_TAI-2025.05.10_08:56:26_TAI,2025.04.26_04:56:26_TAI-2025.05.09_08:56:26_TAI"


# Adjacent Meridian Contribution for Weight Function Shape
awf_nimg: 5  # UNEVEN number of images considered by the weight function default:5: central image +2 on each side
awf_cmin: 5  # minimum contribution %
awf_cmax: 5  # maximum contribution %
awf_dmin: 25 # latitude border until which minimum contribution is used
awf_dmax: 60 # latitude border from which maximum contribution is used
awf_lim : False  # TODO DO NOT USE FOR NOW. Unexpected behaviour with NaN in synop.fits output when using awf_nlim: 25
awf_nlim: 25 # default: 25, TODO understand this parameter again, there might be a factor 2 missing/too much in the code using this

# rebinning
bin: True
xbin: 5 # HMI default 5
ybin: 4 # HMI default 4

# classic hmisynoptic parameters
nsig        : 3.0  # TODO: not sure what the difference to noiseS is
mapmmax     : 1800 # determines mapcols (default: 1800)
sinbdivs    : 720  # number of increments in sin latitude from 0 to 1 (default: 720)
lgmin       : -90  # longitude minimum, degrees (default: -90)
lgmax       : +90  # longitude maximum, degrees (default: +90)
checkqual   : 0    # un
center      : 0.0  # relative offset to central meridian for magnetogram slice data selection
#los        : 0   # OBSOLETE, scheduled to be removed
dlog        : 0    # log flag for the c code. currently unused
nEquivPtsReq: 20   # number of HMI magnetograms for averaged pixels
noiseS      : 3.0  # std dev of noise
maxNoiseAdj : 3.0  # maximum adjustment due to increases with latitude of the noise level (radial data only) 
minOutPts   : 4.0  # minimum number of points that must exist before outliers can be  discarded when calulating summary statistics
```


### Data Selection 
_src/data_selection.py_s

```yaml
###########################################################
###################### Data selection #####################
###########################################################

# GENERAL PARAMETERS

# Solar Orbiter spice kernel https://www.cosmos.esa.int/web/spice/solar_orbiter
# https://repos.cosmos.esa.int/socci/scm/spice_kernels/solar-orbiter.git
spice_mkpath: '/scratch/slam/loeschl/spice/solar-orbiter/kernels/mk/'  # path to meta kernel
spice_mkname: 'solo_ANC_soc-flown-mk.tm' # meta kernel name

et_resolution: 3600 # default: 3600 = 1h in seconds

earth_cad: 14400  # defaut: 14400 = 4h in seconds
solo_cad:  14400  # defaut: 14400 = 4h in seconds

start_cad: 14400 # simulate synoptic maps starting every {start_cat} seconds, default = 43200 = 12h

# LONG TERM DATA SELECTION
detailed_output: True
# Use ISO 8601 compatible format for numpy datetime: 'YYYY-MM-DDTHH:MM:SS'
cr_date_start: '2021-11-01T00:00:00' #'2024-04-01T00:00:00' #
cr_date_end:   '2030-11-20T04:00:00' #'2024-08-01T00:00:00' #

# INDIVIDUAL DATA SELECTION
single_carrington: False

# overlapping priority periods will prioritise PHI for now
priority_phi: 'YYYY-MM-DDTHH:MM:SS' # timestring
priority_hmi: 'YYYY-MM-DDTHH:MM:SS' # timestring
```







## Known issues
- Synoptic map processing cannot be aborted if launched together with run_bash_scripts()
- WARNING: hmisynoptic.py needs data at the same Carrington rotation number which will not always be the case for arbitrary combinations of PHI and HMI. There a common number is forced based on the majority of data. As a result nonsensical combinations like HMI from one year and PHI from another will currently work and not raise any errors! 
- UNTESTED: changing output_path to something outside of the project folder - try that at your own risk if necessary.
- awf_nlim = True has an issue that introduces NaNs into the synoptic map. I already have a lead but it's fairly low on the list since we can just use it without the limiter (set to False)
- python  path/synop_pipeline.py --config=/path/to/config.yaml
  - config path must be absolute or relative to synop_pipeline.py rather than relative to cwd




## Citations / References
- Liu, Y., Hoeksema, J. T., Sun, X., Hayashi, K., & Hayashi, T. (2017). Vector Magnetic Field Synoptic Charts from the Helioseismic and Magnetic Imager (HMI). *Solar Physics*, 292(1), 29. https://doi.org/10.1007/s11207-017-1056-9

- Loeschl, P., Hirzberger, J., Solanki, S. K., Schou, J., & Valori, G. (2024). Synoptic maps from two viewpoints. Preparing for maps from SDO/HMI and SO/PHI data. *Astronomy & Astrophysics*, 682, A108. [https://doi.org/10.1051/0004-6361/202346044](https://doi.org/10.1051/0004-6361/202346044)

- Scherrer, P. H., Schou, J., Bush, R. I., Kosovichev, A. G., Bogart, R. S., Hoeksema, J. T., Liu, Y., Duvall, T. L., Zhao, J., Title, A. M., Schrijver, C. J., Tarbell, T. D., & Tomczyk, S. (2012). The Helioseismic and Magnetic Imager (HMI) Investigation for the Solar Dynamics Observatory (SDO). *Solar Physics*, 275(1–2), 207–227. [https://doi.org/10.1007/s11207-011-9834-2](https://doi.org/10.1007/s11207-011-9834-2)

- Schou, J., Scherrer, P. H., Bush, R. I., Wachter, R., Couvidat, S., Rabello-Soares, M. C., Bogart, R. S., Hoeksema, J. T., Liu, Y., Duvall, T. L., Akin, D. J., Allard, B. A., Miles, J. W., Rairden, R., Shine, R. A., Tarbell, T. D., Title, A. M., Wolfson, C. J., Elmore, D. F., Norton, A. A., & Tomczyk, S. (2012). Design and Ground Calibration of the Helioseismic and Magnetic Imager (HMI) Instrument on the Solar Dynamics Observatory (SDO). *Solar Physics*, 275(1–2), 229–259. [https://doi.org/10.1007/s11207-011-9842-2](https://doi.org/10.1007/s11207-011-9842-2)

- Solanki, S. K., del Toro Iniesta, J. C., Woch, J., et al. (2020). The Polarimetric and Helioseismic Imager on Solar Orbiter. *Astronomy & Astrophysics*, 642, A11. [https://doi.org/10.1051/0004-6361/201935325](https://doi.org/10.1051/0004-6361/201935325)



## Acknowledgements 
We would like to thank Yang Liu, Art Amezcua and Zhi-Chao Liang for their endless patience and guidance on the \HMI\ pipeline and DRMS. This work was carried out in the framework of the International Max Planck Research School (IMPRS) for Solar System Science at the University of Göttingen. Solar Orbiter is a space mission of international collaboration between ESA and NASA, operated by ESA. We are grateful to the ESA SOC and MOC teams for their support. The German contribution to SO/PHI is funded by the BMWi through DLR and by MPG central funds. The HMI data are courtesy of NASA/SDO and the HMI science team. The data were processed at the German Data Center for SDO (GDC-SDO), funded by the German Aerospace Center (DLR).

## License
This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.  
You can view the full license text here: [GPLv3 License](https://www.gnu.org/licenses/gpl-3.0.txt)