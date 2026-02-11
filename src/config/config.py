import yaml
from pathlib import Path
import warnings
from datetime import datetime

class Config:
    # Default values
    _DEFAULTS = {

        ###########################################################
        ################# Pipeline Configuration ##################
        ###########################################################

        # Pipeline selection
        "b3c":                     False, # LoS pipeline by default
        "b3c_disambig":            "random",   # random, radial, potential

        "run_drms_prep":           False, # run 0_drms_prep.py to create JSD files and data series in DRMS
        "run_m720s_drms_pipe":     False,  # run 1_m720s_drms_pipe.py to create the hiresmap and remap
        "run_phi_drms_interface":  False, # run 2_phi_drms_interface.py to create the phi data series

        "run_hmi_scripts":         False, # run all HMI scripts in the outpath_scripts directory 
        "run_phi_scripts":         False, # run all PHI scripts in the outpath_scripts directory 

        "run_hmiphisynoptic":      True, # run 3_hmisynoptic.py to create the synoptic maps
        "run_polefilling":         False, # run all synoptic map pole filling

        "run_diagnostics":         False, # run diagnostics.py to create the synoptic maps diagnostics

        ###########################################################
        #################### Global parameters ####################
        ###########################################################

        # Enable verbose output
        "verbose": True,

        # Session ID, also used as data series appendix e.g. "FDT_test_release_june_2022_defri" for FDT test release june 2022 defringed      
        "id": "pipeline_test", # DEPRECATED

        "data_series_phi"      : "mps_loeschl.phi_M",            
        "data_series_jv2ts_phi": "mps_loeschl.phi_%s_hiresmap", 
        "data_series_remap_phi": "mps_loeschl.phi_%s_remap",    

        "data_series_hmi"      : "hmi.M_720s",                  # "mps_production.hmi_m_720s_nrt"
        "data_series_jv2ts_hmi": "mps_loeschl.hmi_%s_hiresmap", 
        "data_series_remap_hmi": "mps_loeschl.hmi_%s_remap",     

        "data_series_synop"    : "mps_loeschl.synoptic_%s",        # synoptic data series name
        "data_series_polfil"   : "mps_loeschl.synoptic_Mr_polfil", # synoptic Mr polfil data series name, no Ml equivalent as polfil requires Mr projection

        # database path for new implementation
        "phi_dbpath": "/data/solo/phi/data/fmdb/public/l2",
        #"date_start": "2022-06-03", # YYYY-MM-DD # PROBABLY OBSOLETE, NOW USING TIMESTRING_PHI --IGNORE--
        #"date_end"  : "2022-06-18", # YYYY-MM-DD # PROBABLY OBSOLETE, NOW USING TIMESTRING_PHI --IGNORE--
        "key"       : "blos",       # data segment

        # Output path for DRMS scripts relative (relative to synop/)- e.g. synop/output/CR_NUMBER_SESSION_ID/
        "output_path": 'output/',

        "script_path" : 'scripts/', # path to bash scripts, relative to synop/output/CR_NUMBER_SESSION_ID/
        "log_path"    : 'logs/',    # path to log files, relative to synop/output/CR_NUMBER_SESSION_ID/
        "data_path"   : 'data/',    # path to data files, relative to synop/output/CR_NUMBER_SESSION_ID/
        "jsd_path"    : 'jsd/',     # path to JSD files, relative to synop/output/CR_NUMBER_SESSION_ID/
        "synop_path"  : 'synop/',   # path to synoptic maps, relative to synop/output/CR_NUMBER_SESSION_ID/
        "obsplan_path": 'obsplan/', # path to observation plans, relative to synop/output/CR_NUMBER_SESSION_ID/

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
        "create_jsd_phi"         : False, 
        "create_jsd_hiresmap_phi": False,
        "create_jsd_hiresmap_hmi": False,
        "create_jsd_remap_phi"   : False,
        "create_jsd_remap_hmi"   : False,
        "create_jsd_synoptic"    : False, 
        "create_jsd_polfil"      : False,

        "remap_template"   : "remap_template.jsd",              # template for remap data series
        "hiresmap_template": "hiresmap_template.jsd",           # template for hiresmap data series
        "phi_template"     : "phi_template.jsd",                # template for phi data series            
        "synoptic_template": "synoptic_template.jsd",           # template for synoptic data series
        "polfil_template"  : "synoptic_mr_polfil_template.jsd", # template for polfil data series

        "create_series"  : False, # Toggle data series creation from above JSF files in DRMS
        "use_temp_series": False, # Use temporary data series based on ID and CR number


        ###########################################################
        ################### HMI & PHI Processing ##################
        ###########################################################

        # HMI source data series # OBSOLETE MOVED TO data_series_hmi  
        #"dataseries_input": "hmi.M_720s", # "mps_production.hmi_m_720s_nrt"

        # HMI cadence for the M_720s data series - default/nothing: @12min, change HMI cadence for fast prototyping
        "interval_hmi": "@12m",
        "interval_phi": "@12m",

        # Exclude already processed datasets
        "filter_duplicates_hmi": True,
        "filter_duplicates_phi": True,

        # split batch scripts after nsplit entries
        "nparallel_hmi": 5,  # number of parallel HMI DRMS shell scripts
        "nparallel_phi": 1,   # number of parallel PHI DRMS shell scripts

        "hmi_maprmax": 0.998,  # HMI default value
        "phi_maprmax": 0.9925, # maximum radius for the synoptic map
        

        ###########################################################
        ################# Synoptic Map Processing #################
        ###########################################################

        # timestring2258_phi_hmi12m
        "timestring_hmi": "2022.06.06_03:00:00_TAI-2022.06.17_19:00:00_TAI",
        "timestring_phi": "2024.05.19_10:56:26_TAI-2024.05.20_14:56:26_TAI,2024.05.06_06:56:26_TAI-2024.05.19_06:56:26_TAI",
        
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

        # Synoptic map output file name - JSD FILES NEED TO BE ALTERED IF THIS PARAMETERS IS CHANGED
        "synop_name"      : "synop%s.fits",      # proj
        "synop_small_name": "synop%s_small.fits" #% proj

    }


    def __init__(self, config_path=None):
        """Initialize Config with an optional path to the YAML file."""
        self._path = Path(config_path) if config_path else None
        self._data = {}
        self._load()
        self._assemble_name_strings()

    def _deep_update(self, defaults, overrides):
        """
        Recursively merge overrides into defaults.
        - If a key exists in both and both values are dicts, merge them.
        - Otherwise, overwrite the default with the override.
        """
        result = defaults.copy()
        for key, value in overrides.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_update(result[key], value)
            else:
                result[key] = value
        return result

    def _load(self):
        """Load YAML config and apply defaults."""
        # Start with defaults
        self._data = self._DEFAULTS.copy()

        # No file path given → just use defaults
        if self._path is None:
            warnings.warn("No config file provided, using all defaults.")
            return

        # File path given but missing
        if not self._path.exists():
            warnings.warn(f"Config file not found: {self._path}. Using all defaults.")
            return

        # Try loading YAML
        try:
            with self._path.open("r") as f:
                loaded = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise RuntimeError(f"Error parsing YAML config: {e}")

        # Deep merge
        self._data = self._deep_update(self._DEFAULTS, loaded)
    
    def update(self, key, value):
        """Update a config value."""
        if key in self._data:
            self._data[key] = value
        else:
            raise KeyError(f"Config key '{key}' does not exist.")
        

    def reload(self):
        """Reload config from disk."""
        self._load()


    def save(self, output_path):
        """
        Save the current config to a YAML file.
        This can be used for logging the exact settings used in a run.
        """
        output_path = Path(output_path)
        file = output_path.joinpath('config.yaml')

        # Ensure the directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Add timestamp to file header as a comment
        with file.open("w") as f:
            f.write(f"# Saved config on {datetime.now().isoformat()}\n")
            yaml.safe_dump(self._data, f, sort_keys=False)


    def _assemble_name_strings(self):
        # TODO VECT
        # - add conntrol structure for vector Btype
        # - add vecot proj

        if self._data["Mr"]:
            self._data["proj"]    = "Mr"
            self._data["Btype"]   = "Radial"
            self._data["mcorlev"] = 2 # option for magnetic correction: 0:none; 1:line of sight; 2:radial"
        else:
            self._data["proj"]    = "Ml"
            self._data["Btype"]   = "line-of-sight"
            self._data["mcorlev"] = 1 # option for magnetic correction: 0:none; 1:line of sight; 2:radial"


        if self._data["use_temp_series"]:
            self._data["data_series_phi"]       = "%s.phi_CR%s_%s"              %(self._data["dataseries_owner"], self._data["cr"],   self._data["id"])
            self._data["data_series_jv2ts_phi"] = "%s.phi_%s_hiresmap_CR%s_%s"  %(self._data["dataseries_owner"], self._data["proj"], self._data["cr"], self._data["id"]) #"mps_loeschl.Ml_hiresmap_720s_test"
            self._data["data_series_remap_phi"] = "%s.phi_%s_remap_CR%s_%s"     %(self._data["dataseries_owner"], self._data["proj"], self._data["cr"], self._data["id"])  #"mps_loeschl.Ml_remap_720s_test"

            self._data["data_series_jv2ts_hmi"] = "%s.hmi_%s_hiresmap_CR%s_%s"  %(self._data["dataseries_owner"], self._data["proj"], self._data["cr"], self._data["id"]) #"mps_loeschl.Ml_hiresmap_720s_test"
            self._data["data_series_remap_hmi"] = "%s.hmi_%s_remap_CR%s_%s"     %(self._data["dataseries_owner"], self._data["proj"], self._data["cr"], self._data["id"])  #"mps_loeschl.Ml_remap_720s_test"

            self._data["data_series_synop"]     = "%s.synoptic_%s_%s"           %(self._data["dataseries_owner"], self._data["proj"], self._data["id"])  # synoptic data series name
            self._data["data_series_polfil"]    = "%s.synoptic_Mr_polfil_%s"    %(self._data["dataseries_owner"], self._data["id"]) # synoptic Mr polfil data series name
        
        else:    
            try:
                #Execute if no dataseries definitions were provided and default parameters are used instead
                #self._data["data_series_phi"]       = "mps_loeschl.phi_M"                # mps_phi.something
                self._data["data_series_jv2ts_phi"] = self._data["data_series_jv2ts_phi"] %self._data["proj"] # 
                self._data["data_series_remap_phi"] = self._data["data_series_remap_phi"] %self._data["proj"] # 

                #self._data["data_series_hmi"]       = "hmi.M_720s"                       # "mps_production.hmi_m_720s_nrt"
                self._data["data_series_jv2ts_hmi"] = self._data["data_series_jv2ts_hmi"] %self._data["proj"] # 
                self._data["data_series_remap_hmi"] = self._data["data_series_remap_hmi"] %self._data["proj"] # 

                self._data["data_series_synop"]     = self._data["data_series_synop"]     %self._data["proj"] # synoptic data series name
                self._data["data_series_polfil"]    = "mps_loeschl.synoptic_Mr_polfil" # synoptic Mr polfil data series name, no Ml equivalent as polfil requires Mr projection
            except:
                pass

        # Synoptic map output file name - JSD FILES NEED TO BE ALTERED IF THIS PARAMETERS IS CHANGED
        self._data["synop_name"]       = "synop%s.fits"       % self._data["proj"]
        self._data["synop_small_name"] = "synop%s_small.fits" % self._data["proj"]


    def __getattr__(self, name):
        """Allow attribute-style access (e.g., config.verbose)."""
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"No such config key: {name}")


    def __repr__(self):
        return f"<Config {self._path.name}: {self._data}>"
    

    


if __name__ == "__main__":

    config = Config('testconfig.yaml')
  




