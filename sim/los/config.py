###########################################################
#################### Global parameters ####################
###########################################################

# Enable verbose output
verbose = True


###########################################################
################### 1_m720s_drms_pipe.py ##################
###########################################################

# Data path to PHI data for DRMS ingestion
phi_datapath = '/scratch/slam/loeschl/dev/python/synop_old/LoS/output/data/phi/pipeline_test/'
#phi_datapath = '/scratch/slam/loeschl/dev/python/synop_old/LoS/output/data/phi/FDT_test_release_june_2022_defringed/'


# Output path for DRMS scripts - e.g. synop/output/CR_NUMBER_SESSION_ID/
script_path = '../../output/test/' 

# Ml/Mr selection -> False = Blos, True = Mr
Mr = True 

# HMI source data series 
dataseries_input = "hmi.M_720s" 

# HMI cadence for the M_720s data series - default/nothing = @12min, change HMI cadence for fast prototyping
interval = ""

# Carrington rotation number (primary key for synoptic maps)
cr = 2258

# HMI data period
period = "2022.06.06_23:00:00_TAI-2022.06.17_23:00:00_TAI@12m" # CR2258

# data series appendix e.g. "FDT_test_release_june_2022_defri" for FDT test release june 2022 defringed      
rev = "_FDT_test_release_june_2022_defri" 

# Exclude already processed HMI datasets
filter_duplicates = True

# owner of temporary data series, used for output file names
dataseries_owner = "mps_loeschl" 


# redefine where the bash scripts are stored!
# automatically create synop/output/CR_NUMBER_SESSION_ID/
# add "cd phi_datapath" to the beginning of the bash scripts
# add "cd script_path" to the end of the bash scripts
# careful with the script splitting routine, probably needs to be added to each


# Run this code at the bottom of the config file? v2hout an rmmout can be merged
# with the 2_phi_drms_interface.py variables data series definitions

if Mr:
    proj = "Mr"
    mcorlev = 2 # for jv2ts command line 
else:
    proj = "Ml"
    mcorlev = 1 # for jv2ts command line 

v2hout = '%s.%s_hiresmap_CR%s%s'%(dataseries_owner, proj, cr, rev) #'mps_loeschl.Ml_hiresmap_config.cr2240_fast'
rmmout = '%s.%s_remap_CR%s%s'%(dataseries_owner, proj, cr, rev) #'mps_loeschl.Ml_remap_CR2240_fast


###########################################################
################# 2_phi_drms_interface.py #################
###########################################################

# TEMPORARY OUTPUT FILE
# TODO revisit after defining script path and temporary data output path
temp_path = "" # add _DRMS output and bash scripts there
# path_out also needs to be replaced

maprmax = 0.9925 #0.998 # maximum radius for the synoptic map, 0.998 is the default for HMI synoptic maps

data_series_m720s = "%s.phi_CR%s%s"         %(dataseries_owner, cr, rev)
data_series_jv2ts = "%s.Mr_hiresmap_CR%s%s" %(dataseries_owner, cr, rev) #"mps_loeschl.Ml_hiresmap_720s_test"
data_series_remap = "%s.Mr_remap_CR%s%s"    %(dataseries_owner, cr, rev) #"mps_loeschl.Ml_remap_720s_test"









###########################################################
################### 4_hmiphisynoptic.py ###################
###########################################################


timestring = ""
awfs = [5]#, 15, 25, 35, 45, 55]
cadences = ["12m"] #["2h", "4h", "6h", "8h", "12h", "24h"]
path_synop = "" # synoptic map output path

# todo fix
#path = "../output/data/paper/cr%s_Mr_FDT_test_release_june_2022_defringed/awf_0%spct-%spct_%simg/" % (config["cr"], config["awf_cmin"], config["awf_cmax"], config["awf_nimg"])

# change get_arg_parameters() to read config from here

#def get_arg_parameters():
#    
#    # IMPORTANT: CHECK IF MAPMMAX AND SINBDIVS MATCH THE PROJECTION RESOLUTION
#    config = {
#        
#        
#        "cr":2258,
#        "input_ds": "mps_loeschl.Mr_remap_CR2258_FDT_test_release_june_2022_defri", #"mps_loeschl.mr_remap_cr2240_fdt_test_release_sup_conj_2021", #"mps_loeschl.Mr_remap_CR2240_trl_v01", #"mps_loeschl.Ml_remap_CR2240_rev02_ideal",#"mps_loeschl.Mr_remap_CR2240_rev03", #"mps_loeschl.Ml_remap_CR2240_rev02",#"mps_loeschl.Ml_remap_CR2240_fast", #"mps_loeschl.Ml_remap_720s", #"mps_loeschl.Ml_remap_720s_1440p_1xbin_070au", #"mps_loeschl.Ml_remap_720s",#_720p_2xbin_070au", #mps_loeschl.Ml_remap_720s #mps_loeschl.Ml_remap_CR2255
#        "outname": "synopMr.fits",
#        #"au": 0.28, # AU
#        
#        # Adjacent Meridian Contribution for Weight Function Shape
#        "awf_nimg": 5,
#        "awf_cmin": 5,  # minimum contribution %
#        "awf_cmax": 55,  # maximum contribution %
#        "awf_dmin": 25, # latitude border until which minimum contribution is used
#        "awf_dmax": 60, # latitude border from which maximum contribution is used
#        "awf_lim": False,
#        
#        # rebinning
#        "bin": True,
#        "nbin": [5],
#        
#        # classic hmisynoptic parameters
#        "nsig": 3.0, 
#        "mapmmax": 1800, #1800, 
#        "sinbdivs": 720, #720,
#        "lgmin": -90,
#        "lgmax": +90,
#        "checkqual": 0,
#        "center": 0.0,
#        #"halfWindow":15, # now dynamically calculated. obsolete
#        "los": 0,
#        "force": 0,   # unused / obsolete
#        "dlog": 0,
#        "nEquivPtsReq": 20, 
#        "noiseS": 3.0, 
#        "maxNoiseAdj": 3.0,
#        "minOutPts": 4.0,
#    }
#    
#    return config  

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
