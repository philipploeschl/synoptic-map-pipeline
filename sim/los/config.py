###########################################################
#################### Global parameters ####################
###########################################################

# Enable verbose output
verbose = True

# Session ID, also used as data series appendix e.g. "FDT_test_release_june_2022_defri" for FDT test release june 2022 defringed      
id = "pipeline_test" 

# Data path to PHI data for DRMS ingestion
phi_datapath = '/scratch/slam/loeschl/dev/python/synop_old/LoS/output/data/phi/pipeline_test/'
#phi_datapath = '/scratch/slam/loeschl/dev/python/synop_old/LoS/output/data/phi/FDT_test_release_june_2022_defringed/'


# Output path for DRMS scripts relative (relative to synop/)- e.g. synop/output/CR_NUMBER_SESSION_ID/
output_path = 'output/'

script_path = 'scripts/' # path to bash scripts, relative to synop/output/CR_NUMBER_SESSION_ID/
log_path    = 'logs/'    # path to log files, relative to synop/output/CR_NUMBER_SESSION_ID/
data_path   = 'data/'    # path to data files, relative to synop/output/CR_NUMBER_SESSION_ID/
jsd_path    = 'jsd/'     # path to JSD files, relative to synop/output/CR_NUMBER_SESSION_ID/

# File structure created in misc.py: create_session_folder
# - OUTPUT_PATH/
#   - CR_NUMBER_YYYYMMDD_HHMMSS
#       - DATA
#       - SCRIPTS   
#       - LOGS

# redefine where the bash scripts are stored!
# automatically create synop/output/CR_NUMBER_SESSION_ID/
# add "cd phi_datapath" to the beginning of the bash scripts
# add "cd script_path" to the end of the bash scripts
# careful with the script splitting routine, probably needs to be added to each

# path to JSD templates, relative to synop/
template_path = "drms_prep/" 


###########################################################
################# Data series definition ##################
###########################################################

# owner of temporary data series, used for output file names
dataseries_owner = "mps_loeschl" 

# Ml/Mr selection -> False = Blos, True = Mr
Mr = True 

# Carrington rotation number (primary key for synoptic maps)
cr = 2258

# toggle creation jsd files for data series
create_jsd_phi      = True 
create_jsd_hiresmap = True
create_jsd_remap    = True
create_jsd_synoptic = False 
create_jsd_polfil   = False

remap_template    = "remap_template.jsd"              # template for remap data series
hiresmap_template = "hiresmap_template.jsd"           # template for hiresmap data series
phi_template      = "phi_template.jsd"                # template for phi data series            
synoptic_template = "synoptic_template.jsd"           # template for synoptic data series
polfil_template   = "synoptic_mr_polfil_template.jsd" # template for polfil data series

# Toggle data series creation in DRMS
create_series = False

###########################################################
############## DON'T CHANGE THESE PARAMETERS ##############
###########################################################

if Mr:
    proj = "Mr"
    Btype = "Radial"
    mcorlev = 2 # for jv2ts command line 
else:
    proj = "Ml"
    Btype = "line-of-sight"
    mcorlev = 1 # for jv2ts command line 

data_series_phi = "%s.phi_CR%s_%s"         %(dataseries_owner, cr, id)
data_series_jv2ts = "%s.%s_hiresmap_CR%s_%s" %(dataseries_owner, proj, cr, id) #"mps_loeschl.Ml_hiresmap_720s_test"
data_series_remap = "%s.%s_remap_CR%s_%s"    %(dataseries_owner, proj, cr, id) #"mps_loeschl.Ml_remap_720s_test"

data_series_synop = "%s.synoptic_%s_%s" %(dataseries_owner, proj, id) # synoptic data series name
data_series_polfil = "%s.synoptic_Mr_polfil_%s" %(dataseries_owner, id) # synoptic Mr polfil data series name

###########################################################
################### 1_m720s_drms_pipe.py ##################
###########################################################


# HMI source data series 
dataseries_input = "hmi.M_720s" 

# HMI cadence for the M_720s data series - default/nothing = @12min, change HMI cadence for fast prototyping
interval = ""

# HMI data period
period = "2022.06.06_23:00:00_TAI-2022.06.17_23:00:00_TAI@12m" # CR2258

# Exclude already processed HMI datasets
filter_duplicates = True

# split batch scripts after nsplit entries
nsplit = 150

# Directly run the bash after creating them . If False, only create bash scripts, but do not execute them
run_hmi_scripts = False 







###########################################################
################# 2_phi_drms_interface.py #################
###########################################################

# Directly run the bash after creating them . If False, only create bash scripts, but do not execute them
run_phi_scripts = False 

maprmax = 0.9925 #0.998 # maximum radius for the synoptic map, 0.998 is the default for HMI synoptic maps




###########################################################
################### 4_hmiphisynoptic.py ###################
###########################################################


# Synoptic map output file name - JSD FILES NEED TO BE ALTERED IF THIS PARAMETERS IS CHANGED
synop_outname = "synop%s.fits" % proj
synop_outpath = output_path

# timestring2258_phi_hmi12m
timestring = "2022.06.06_03:00:00_TAI-2022.06.17_19:00:00_TAI@12m,2022.06.17_22:54:23_TAI,2022.06.18_10:56:25_TAI,2022.06.18_23:03:13_TAI,2022.06.19_11:15:52_TAI,2022.06.19_23:22:58_TAI,2022.06.20_11:36:08_TAI,2022.06.20_23:53:39_TAI,2022.06.21_04:17:58_TAI,2022.06.22_00:04:49_TAI,2022.06.22_12:18:51_TAI,2022.06.22_18:23:04_TAI,2022.06.23_00:26:52_TAI,2022.06.23_06:33:54_TAI,2022.06.23_12:41:16_TAI,2022.06.23_18:45:28_TAI,2022.06.24_00:49:36_TAI,2022.06.24_06:56:58_TAI,2022.05.28_08:15:44_TAI,2022.05.28_14:22:55_TAI,2022.05.28_20:26:46_TAI,2022.05.29_02:31:46_TAI,2022.05.29_08:40:07_TAI,2022.05.29_14:47:11_TAI,2022.05.29_20:51:05_TAI,2022.05.30_02:56:29_TAI,2022.05.30_09:05:03_TAI,2022.05.30_15:12:00_TAI,2022.05.30_21:15:56_TAI,2022.05.31_03:21:44_TAI,2022.05.31_09:30:30_TAI,2022.06.01_09:56:24_TAI,2022.06.01_16:03:02_TAI,2022.06.01_22:07:09_TAI,2022.06.02_04:13:44_TAI,2022.06.02_10:22:46_TAI,2022.06.02_16:29:13_TAI,2022.06.02_22:33:28_TAI,2022.06.03_04:40:26_TAI,2022.06.03_10:49:32_TAI,2022.06.03_16:55:48_TAI,2022.06.03_23:00:11_TAI,2022.06.04_05:07:33_TAI,2022.06.04_11:16:41_TAI,2022.06.04_17:22:45_TAI,2022.06.04_23:27:20_TAI,2022.06.05_05:35:04_TAI,2022.06.05_11:44:11_TAI,2022.06.05_17:50:04_TAI,2022.06.05_23:54:52_TAI,2022.06.06_06:02:58_TAI,2022.06.06_12:12:00_TAI,2022.06.06_18:17:43_TAI"


# Adjacent Meridian Contribution for Weight Function Shape
awf_nimg = 5,
awf_cmin = 5,  # minimum contribution %
awf_cmax = 5, # maximum contribution %
awf_dmin = 25, # latitude border until which minimum contribution is used
awf_dmax = 60, # latitude border from which maximum contribution is used
awf_lim  = False,
awf_nlim = 25, # default: 25, TODO understand this parameter again


# todo fix
#path = "../output/data/paper/cr%s_Mr_FDT_test_release_june_2022_defringed/awf_0%spct-%spct_%simg/" % (config["cr"], config["awf_cmin"], config["awf_cmax"], config["awf_nimg"])



# rebinning
bin = True,
xbin = 5, # HMI default 5
ybin = 4, # HMI default 4

# classic hmisynoptic parameters
nsig = 3.0, 
mapmmax = 1800, #1800, 
sinbdivs = 720, #720,
lgmin = -90,
lgmax = +90,
checkqual = 0,
center = 0.0,
los = 0,
dlog = 0,
nEquivPtsReq = 20, 
noiseS = 3.0, 
maxNoiseAdj = 3.0,
minOutPts = 4.0,


# Adaptive Weight Function
# - code relies on images taken from the ecliptic
# - lattitude specific weight function control needs to consider out of ecliptic observations
# - understand awf_lim and describe it properly



"""
ToDo List
- refacdtor spice kernels to use official solar orbiter github repository
- SPICE kernel names and download paths
- Timestamps or file paths for the PHI data
- https://repos.cosmos.esa.int/socci/scm/spice_kernels/solar-orbiter.git
- /scratch/valori/nrt_fmdb/l2/DATES
- phi-fdt-blos_OBSDATE-PROCESSINGDATE-DID always take latest processing date if multiple are available 
- possibly option to select if you want to take the last one or specifiy version as file list
- how do I handle quality bits
- provide meta data with dates for each longitdues
- file list from start and end date with exception list
- check how synptic map pipeline handles noise outliers since PHI might come wiht sqrt(3) difference for onboard averaged data. make sure we don't lose data without noticing

"""

"""
roadmap
- old test case 2240 -> 2258 for the updated header
- test case may 2025
- date +-5d of FDT
"""

"""
ToDo config parameters
- time stamps for paths
- parameters to connect the scripts

- generic JSD files
- automatic data_series creation
"""
