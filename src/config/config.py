import yaml
from pathlib import Path
import warnings

class Config:
    # Default values
    _DEFAULTS = {

        ###########################################################
        ################# Pipeline Configuration ##################
        ###########################################################

        "run_drms_prep":           True, # run 0_drms_prep.py to create JSD files and data series in DRMS
        "run_m720s_drms_pipe":     False,  # run 1_m720s_drms_pipe.py to create the hiresmap and remap
        "run_phi_drms_interface":  False, # run 2_phi_drms_interface.py to create the phi data series

        "run_hmi_scripts":         False, # run all HMI scripts in the outpath_scripts directory 
        "run_phi_scripts":         False, # run all PHI scripts in the outpath_scripts directory 

        "run_hmiphisynoptic":      False, # run 3_hmisynoptic.py to create the synoptic maps
        "run_polefilling":         False, # run all synoptic map pole filling

        ###########################################################
        #################### Global parameters ####################
        ###########################################################

        # Enable verbose output
        "verbose": True,

        # Create new session, reads session_path.txt to access 
        "new_session": True, # PLACEHOLDER
        "prev_session": "CR2258_pipeline_test_20250808_140902", # PLACEHOLDER

        # Session ID, also used as data series appendix e.g. "FDT_test_release_june_2022_defri" for FDT test release june 2022 defringed      
        "id": "pipeline_test",

        # Data path to PHI data for DRMS ingestion
        # direct path for old implementation NOT FUNCTIONAL
        "phi_datapath": '/scratch/slam/loeschl/dev/python/synop_old/LoS/output/data/phi/FDT_test_release_june_2022_defringed/',

        # database path for new implementation
        "phi_dbpath": "/data/slam/valori/test_l2_fmdb/FDT_test_release_jan-sep_2022_ghost_corr_update_defringed/l2/",
        "date_start": "2022-06-03", # YYYY-MM-DD
        "date_end"  : "2022-06-18", # YYYY-MM-DD
        "key"       : "blos",       # data segment

        # Output path for DRMS scripts relative (relative to synop/)- e.g. synop/output/CR_NUMBER_SESSION_ID/
        "output_path": 'output/',

        "script_path": 'scripts/', # path to bash scripts, relative to synop/output/CR_NUMBER_SESSION_ID/
        "log_path"   : 'logs/',    # path to log files, relative to synop/output/CR_NUMBER_SESSION_ID/
        "data_path"  : 'data/',    # path to data files, relative to synop/output/CR_NUMBER_SESSION_ID/
        "jsd_path"   : 'jsd/',     # path to JSD files, relative to synop/output/CR_NUMBER_SESSION_ID/
        "synop_path" : 'synop/',   # path to synoptic maps, relative to synop/output/CR_NUMBER_SESSION_ID/

        # File structure created in misc.py: create_session_folder
        # - OUTPUT_PATH/
        #   - CR_NUMBER_YYYYMMDD_HHMMSS
        #       - DATA
        #       - SCRIPTS   
        #       - LOGS
        #       - JSD
        #       - SYNOP

        # path to JSD templates, relative to synop/
        "template_path": "data/drms/templates/", 


        # Solar Orbiter spice kernel https://www.cosmos.esa.int/web/spice/solar_orbiter
        # https://repos.cosmos.esa.int/socci/scm/spice_kernels/solar-orbiter.git
        "spice_mkpath": '/scratch/slam/loeschl/spice/solar-orbiter/kernels/mk/',  # path to meta kernel
        "spice_mkname": 'solo_ANC_soc-flown-mk.tm', # meta kernel name

        ###########################################################
        ################# Data series definition ##################
        ###########################################################

        # owner of temporary data series, used for output file names
        "dataseries_owner": "mps_loeschl", 

        # Ml/Mr selection -> False: Blos, True: Mr
        "Mr": True, 

        # Carrington rotation number (primary key for synoptic maps)
        "cr": 2258,

        # toggle creation jsd files for data series
        "create_jsd_phi"     : True, 
        "create_jsd_hiresmap": True,
        "create_jsd_remap"   : True,
        "create_jsd_synoptic": False, 
        "create_jsd_polfil"  : False,

        "remap_template"   : "remap_template.jsd",              # template for remap data series
        "hiresmap_template": "hiresmap_template.jsd",           # template for hiresmap data series
        "phi_template"     : "phi_template.jsd",                # template for phi data series            
        "synoptic_template": "synoptic_template.jsd",           # template for synoptic data series
        "polfil_template"  : "synoptic_mr_polfil_template.jsd", # template for polfil data series

        # Toggle data series creation from above JSF files in DRMS
        "create_series": False,


        ###########################################################
        ################### 1_m720s_drms_pipe.py ##################
        ###########################################################

        # HMI source data series 
        "dataseries_input": "hmi.M_720s", # "mps_production.hmi_m_720s_nrt"

        # HMI cadence for the M_720s data series - default/nothing: @12min, change HMI cadence for fast prototyping
        "interval": "@12m",

        # HMI data period
        "period": "2022.06.06_23:00:00_TAI-2022.06.17_23:00:00_TAI", # CR2258

        # Exclude already processed HMI datasets
        "filter_duplicates": True,

        # split batch scripts after nsplit entries
        "nparallel_hmi": 15,  # number of parallel HMI DRMS shell scripts
        "nparallel_phi": 1,   # number of parallel PHI DRMS shell scripts


        ###########################################################
        ################# 2_phi_drms_interface.py #################
        ###########################################################

        "hmi_maprmax": 0.998,  # HMI default value
        "phi_maprmax": 0.9925, # maximum radius for the synoptic map


        ###########################################################
        ################### 3_hmiphisynoptic.py ###################
        ###########################################################

        # timestring2258_phi_hmi12m
        "timestring": "2022.06.06_03:00:00_TAI-2022.06.17_19:00:00_TAI@12m,2022.06.17_22:54:23_TAI,2022.06.18_10:56:25_TAI,2022.06.18_23:03:13_TAI,2022.06.19_11:15:52_TAI,2022.06.19_23:22:58_TAI,2022.06.20_11:36:08_TAI,2022.06.20_23:53:39_TAI,2022.06.21_04:17:58_TAI,2022.06.22_00:04:49_TAI,2022.06.22_12:18:51_TAI,2022.06.22_18:23:04_TAI,2022.06.23_00:26:52_TAI,2022.06.23_06:33:54_TAI,2022.06.23_12:41:16_TAI,2022.06.23_18:45:28_TAI,2022.06.24_00:49:36_TAI,2022.06.24_06:56:58_TAI,2022.05.28_08:15:44_TAI,2022.05.28_14:22:55_TAI,2022.05.28_20:26:46_TAI,2022.05.29_02:31:46_TAI,2022.05.29_08:40:07_TAI,2022.05.29_14:47:11_TAI,2022.05.29_20:51:05_TAI,2022.05.30_02:56:29_TAI,2022.05.30_09:05:03_TAI,2022.05.30_15:12:00_TAI,2022.05.30_21:15:56_TAI,2022.05.31_03:21:44_TAI,2022.05.31_09:30:30_TAI,2022.06.01_09:56:24_TAI,2022.06.01_16:03:02_TAI,2022.06.01_22:07:09_TAI,2022.06.02_04:13:44_TAI,2022.06.02_10:22:46_TAI,2022.06.02_16:29:13_TAI,2022.06.02_22:33:28_TAI,2022.06.03_04:40:26_TAI,2022.06.03_10:49:32_TAI,2022.06.03_16:55:48_TAI,2022.06.03_23:00:11_TAI,2022.06.04_05:07:33_TAI,2022.06.04_11:16:41_TAI,2022.06.04_17:22:45_TAI,2022.06.04_23:27:20_TAI,2022.06.05_05:35:04_TAI,2022.06.05_11:44:11_TAI,2022.06.05_17:50:04_TAI,2022.06.05_23:54:52_TAI,2022.06.06_06:02:58_TAI,2022.06.06_12:12:00_TAI,2022.06.06_18:17:43_TAI",
        # todo this timestring has to be created from the above hmi timestring. timestring: hmi_period+phi_period

        # Adjacent Meridian Contribution for Weight Function Shape
        "awf_nimg": 5,  # UNEVEN number of images considered by the weight function default:5: central image +2 on each side
        "awf_cmin": 5,  # minimum contribution %
        "awf_cmax": 5,  # maximum contribution %
        "awf_dmin": 25, # latitude border until which minimum contribution is used
        "awf_dmax": 60, # latitude border from which maximum contribution is used
        "awf_lim" : False,  # TODO DO NOT USE FOR NOW. Unexpected behaviour with NaN in synop.fits output when using awf_nlim: 25
        "awf_nlim": 25, # default: 25, TODO understand this parameter again, there might be a factor 2 missing/too much in the code using this

        # rebinning
        "bin": True,
        "xbin": 5, # HMI default 5
        "ybin": 4, # HMI default 4

        # classic hmisynoptic parameters
        "nsig"        : 3.0,  # TODO: not sure what the difference to noiseS is
        "mapmmax"     : 1800, # determines mapcols (default: 1800)
        "sinbdivs"    : 720,  # number of increments in sin latitude from 0 to 1 (default: 720)
        "lgmin"       : -90,  # longitude minimum, degrees (default: -90)
        "lgmax"       : +90,  # longitude maximum, degrees (default: +90)
        "checkqual"   : 0,    # un
        "center"      : 0.0,  # relative offset to central meridian for magnetogram slice data selection
        #"los"        : 0,   # OBSOLETE, scheduled to be removed
        "dlog"        : 0,    # log flag for the c code. currently unused
        "nEquivPtsReq": 20,   # number of HMI magnetograms for averaged pixels
        "noiseS"      : 3.0,  # std dev of noise
        "maxNoiseAdj" : 3.0,  # maximum adjustment due to increases with latitude of the noise level (radial data only) 
        "minOutPts"   : 4.0,  # minimum number of points that must exist before outliers can be  discarded when calulating summary statistics


        ###########################################################
        ############## DON'T CHANGE THESE PARAMETERS ##############
        ###########################################################

        "data_series_phi"  : "%s.phi_CR%s_%s",         #%(dataseries_owner, cr, id)
        "data_series_jv2ts": "%s.%s_hiresmap_CR%s_%s", #%(dataseries_owner, proj, cr, id) #"mps_loeschl.Ml_hiresmap_720s_test"
        "data_series_remap": "%s.%s_remap_CR%s_%s",    #%(dataseries_owner, proj, cr, id) #"mps_loeschl.Ml_remap_720s_test"

        "data_series_synop":  "%s.synoptic_%s_%s", #%(dataseries_owner, proj, id) # synoptic data series name
        "data_series_polfil": "%s.synoptic_Mr_polfil_%s", #%(dataseries_owner, id) # synoptic Mr polfil data series name

        # Synoptic map output file name - JSD FILES NEED TO BE ALTERED IF THIS PARAMETERS IS CHANGED
        "synop_name"      : "synop%s.fits",      # proj
        "synop_small_name": "synop%s_small.fits" #% proj

    }

    def __init__(self, config_path):
        """Initialize Config with a path to the YAML file."""
        self._path = Path(config_path)
        self._data = {}
        self._load()
        self._assemble_name_strings()
    
    def _load(self):
        """Load YAML config and apply defaults."""
        if not self._path.exists():
            warnings.warn(f"Config file not found: {self._path}. Using all defaults.")
            self._data = self._DEFAULTS.copy()
            return

        try:
            with self._path.open("r") as f:
                loaded = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise RuntimeError(f"Error parsing YAML config: {e}")

        # Merge defaults with loaded values
        self._data = self._DEFAULTS.copy()
        for key, default_value in self._DEFAULTS.items():
            if key not in loaded:
                #warnings.warn(f"Missing config key '{key}', using default: {default_value}")
                continue
            else:
                self._data[key] = loaded[key]
    
    def reload(self):
        """Reload config from disk."""
        self._load()

    def __getattr__(self, name):
        """Allow attribute-style access (e.g., config.verbose)."""
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"No such config key: {name}")

    def __repr__(self):
        return f"<Config {self._path.name}: {self._data}>"

    def _assemble_name_strings(self):

        if self._data["Mr"]:
            self._data["proj"]    = "Mr"
            self._data["Btype"]   = "Radial"
            self._data["mcorlev"] = 2 # option for magnetic correction: 0:none; 1:line of sight; 2:radial"
        else:
            self._data["proj"]    = "Ml"
            self._data["Btype"]   = "line-of-sight"
            self._data["mcorlev"] = 1 # option for magnetic correction: 0:none; 1:line of sight; 2:radial"

        self._data["data_series_phi"]   = "%s.phi_CR%s_%s"         %(self._data["dataseries_owner"], self._data["cr"],   self._data["id"])
        self._data["data_series_jv2ts"] = "%s.%s_hiresmap_CR%s_%s" %(self._data["dataseries_owner"], self._data["proj"], self._data["cr"], self._data["id"]) #"mps_loeschl.Ml_hiresmap_720s_test"
        self._data["data_series_remap"] = "%s.%s_remap_CR%s_%s"    %(self._data["dataseries_owner"], self._data["proj"], self._data["cr"], self._data["id"])  #"mps_loeschl.Ml_remap_720s_test"

        self._data["data_series_synop"]  = "%s.synoptic_%s_%s"        %(self._data["dataseries_owner"], self._data["proj"], self._data["id"])  # synoptic data series name
        self._data["data_series_polfil"] = "%s.synoptic_Mr_polfil_%s" %(self._data["dataseries_owner"], self._data["id"])  # synoptic Mr polfil data series name

    # Synoptic map output file name - JSD FILES NEED TO BE ALTERED IF THIS PARAMETERS IS CHANGED
        self._data["synop_name"]       = "synop%s.fits"       % self._data["proj"]
        self._data["synop_small_name"] = "synop%s_small.fits" % self._data["proj"]


if __name__ == "__main__":

    config = Config('testconfig.yaml')
    #print(config.phi_datapath)
    #print(config.synop_name)
    print(config.data_series_phi)
    print(config.data_series_jv2ts)
    print(config.data_series_remap)
    print(config.data_series_synop)
    print(config.data_series_polfil)
    print(config.synop_name)
    print(config.synop_small_name)




