import numpy as np
from astropy.io import fits
import pandas as pd
import os, glob
from config.config import Config
from utils.plots import plot_synoptic_sources, plot_synoptic

import drms
from sunpy.net import jsoc
from matplotlib import pyplot as plt


##############################################
####### FUNCTION DEFINITIONS FOR UTILS #######
##############################################

def magnetic_flux(data, thld=0):
    
    pos = data[data >    thld]
    neg = data[data < -1*thld]
    
    sum_pos = np.sum(pos)
    sum_neg = np.sum(neg)
    
    return int(sum_pos), int(sum_neg)


def latitude_magnetic_flux(data, lats, x1, x2, thld_low=0, thld_high=25, norm=True, mean=False, med=False):
    #latwidth = 10  #px
    #lats = np.arange(0,1440, latwidth)
    #flux_hmi   = latitude_magnetic_flux(hmiMr_polfil.data, lats, x1=2000, x2=3600, thld_low=0, thld_high=25, norm=True, mean=False, med=False)

    flux = pd.DataFrame(columns=['pos', 'neg'])
    
    for i in range(len(lats)-1):
        window = data[lats[i]:lats[i+1], x1:x2]
        
        pos = window[window > thld_low]
        pos = pos[pos < thld_high]
        
        neg = window[window < -1*thld_low]
        neg = neg[neg > -1*thld_high]
        
        if mean:
            pos = np.mean(pos)
            neg = np.mean(neg)
            
        if med:
            pos = np.median(pos)
            neg = np.median(neg)
                
        if norm:
            area_pos = len(pos)
            area_neg = len(neg) 
            #print(np.sum(pos, dtype=int), area, np.round(np.sum(pos)/area, 2), len(pos), np.round(np.sum(pos)/len(pos), 2))
            pos = np.sum(pos)/area_pos
            neg = np.sum(neg)/area_neg


        flux_row = pd.DataFrame([[pos, neg]], columns=['pos', 'neg'])
        flux = pd.concat([flux, flux_row])

    return flux

def latitude_magnetic_flux_plot(flux_phi, flux_hmi, latwidth=10, pdf=False):

    fig, ax = plt.subplots(figsize=(7,5))

    ax.plot(flux_hmi['pos'].values+flux_hmi['neg'].values, linestyle='dashed', label='HMI')
    ax.plot(flux_phi['pos'].values+flux_phi['neg'].values, linestyle='dashdot', label='PHI')


    xticks = np.linspace(0, 1440/latwidth, 19)-0.5
    xlabels = np.linspace(-90,90, 19, dtype=int)
    #xticks  = np.linspace(0, 1440//latwidth-1, 1440//latwidth)-0.5
    #xlabels = np.linspace(-90,90, 1440//latwidth, dtype=int)

    plt.axhline(y=0, color='grey', linestyle=(0,(5,10)), alpha=0.75)

    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabels)

    ax.set_xlabel('Latitude Windows')
    ax.set_ylabel('Magnetic Flux [mx/cm²]')
    ax.set_title('Average weak magnetic flux balance (0-25G) in 200-360° Region')
    ax.set_ylim([-6,6])

    plt.legend(loc='lower right', ncol=2)

    plt.tight_layout()
    if pdf:
        plt.savefig("flux_correction.pdf", format="pdf", dpi=300)
    else:
        plt.imshow()


############################
####### GET PHI DATA #######
############################

config = Config(config_path='/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/src/config.yaml') 

datapath = "CR2297_polar_2025_v01/"

cwd = os.getcwd()
root = os.path.normpath(os.path.join(cwd, ".."))
path = os.path.join(root, config.output_path, datapath, config.synop_path)

fname = "synopMl.fits"
outname = f"{config.cr}_diagnostics"

synop_phi  = fits.open(os.path.join(path, fname))

phi_img   = synop_phi[0].data
phi_table = synop_phi[1].data

#plot_synoptic_sources(phi_img, path, outname, config, phi_table, pdf=False)



############################
####### GET HMI DATA #######
############################

# Create DRMS client
c = drms.Client(email="loeschl@mps.mpg.de", verbose=True)

# Define Carrington rotation number
carrington_number = int(config.cr)

# Choose the HMI synoptic map series you want
series  = "hmi.synoptic_ml_720s"
segment = "synopMl"
#series = "hmi.synoptic_mr_720s"
#segment = "synopMr"

datapath_hmi = os.path.join(root, f"data/tmp/CR{carrington_number}/")
os.makedirs(datapath_hmi, exist_ok=True)


# Query JSOC for that rotation
q = c.query(f"{series}[{carrington_number}]", seg=segment)
fname_hmi = q[segment][0].split('/')[-1]

try:
    file_hmi = glob.glob(f"{datapath_hmi}*{fname_hmi}")[0]
    synop_hmi = fits.open(file_hmi)
except FileNotFoundError:
    # Download the FITS file
    result = c.export(f"{series}[{carrington_number}]", method='url', protocol='fits')
    result.download(datapath_hmi)
    file_hmi = glob.glob(f"{datapath_hmi}*{fname_hmi}")[0]
    synop_hmi = fits.open(file_hmi)

hmi_img = synop_hmi[0].data   
# TODO add costum title to replace PHI/HMI with HMI for this use case
#plot_synoptic(synop_hmi[0].data, path, outname, config, pdf=False)


########################
####### ANALYSIS #######
########################

#plot_synoptic(hmi_img-phi_img, path, outname, config, pdf=False)

latwidth = 10  #px
lats = np.arange(0,1440, latwidth)

hmi_x1, hmi_x2 = 0,    2460
phi_x1, phi_x2 = 2460, 3600
e
thld_low  = 0
thld_high = 25

flux_phi   = latitude_magnetic_flux(phi_img, lats, x1=phi_x1, x2=phi_x2, thld_low=thld_low, thld_high=thld_high, norm=True, mean=False, med=False)
flux_hmi   = latitude_magnetic_flux(phi_img, lats, x1=hmi_x1, x2=hmi_x2, thld_low=thld_low, thld_high=thld_high, norm=True, mean=False, med=False)

latitude_magnetic_flux_plot(flux_phi, flux_hmi, latwidth=10, pdf=False)

def get_phi_hmi_windows(fits_table, deg2px=10):
    # find start and end of PHI and HMI data coverage in synoptic map

    phi = []
    hmi = []

    for row in fits_table:
        # make the colored boxes for each fits table line
        if row['SRC'] == 'HMI': 
            hmi.append([int(row["CRLN_END"]*deg2px), int(row["CRLN_START"]*deg2px)])

        width = row["CRLN_START"] - row["CRLN_END"]

        if width > 0:
            windows.append()
            ax.barh(bar_height/2, width*deg2px, left=row["CRLN_END"]*deg2px, height=bar_height, color=color)
        else:
            # interval wraps around 0°
            ax.barh(bar_height/2, (360-row["CRLN_END"])*deg2px, left=row["CRLN_END"]*deg2px, height=bar_height, color=color)
            ax.barh(bar_height/2, row["CRLN_START"]*deg2px, left=0, height=bar_height, color=color)

    return windows



def get_cadence_windows(fits_table, deg2px=10):
    # make the horizontal bar with color coded data sources

    windows = []
    for row in fits_table:
        # make the colored boxes for each fits table line
        if row['SRC'] == 'HMI': 
            continue

        width = row["CRLN_START"] - row["CRLN_END"]

        if width > 0:
            windows.append()
            ax.barh(bar_height/2, width*deg2px, left=row["CRLN_END"]*deg2px, height=bar_height, color=color)
        else:
            # interval wraps around 0°
            ax.barh(bar_height/2, (360-row["CRLN_END"])*deg2px, left=row["CRLN_END"]*deg2px, height=bar_height, color=color)
            ax.barh(bar_height/2, row["CRLN_START"]*deg2px, left=0, height=bar_height, color=color)
