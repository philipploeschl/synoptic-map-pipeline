import numpy as np
from astropy.io import fits
import pandas as pd
import os, glob
from config.config import Config
from utils.plots import plot_synoptic_sources, plot_synoptic

import drms
from sunpy.net import jsoc
from matplotlib import pyplot as plt

import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from mpl_toolkits.axes_grid1 import make_axes_locatable

##############################################
####### FUNCTION DEFINITIONS FOR UTILS #######
##############################################

def magnetic_flux(data, thld=0):
    
    pos = data[data >    thld]
    neg = data[data < -1*thld]
    
    sum_pos = np.sum(pos)
    sum_neg = np.sum(neg)
    
    return int(sum_pos), int(sum_neg)


def magnetic_flux_latitudes(data, lats, x1, x2, thld_low=0, thld_high=25, mean=False, med=False):
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
                
        flux_row = pd.DataFrame([[pos, neg]], columns=['pos', 'neg'])
        flux = pd.concat([flux, flux_row])

    return flux

def magnetic_flux_plot_latitudes(flux_phi, flux_hmi, thld_low, thld_high, latwidth=10, pdf=False):

    fig, ax = plt.subplots(figsize=(7,5))

    ax.plot(flux_hmi['pos'].values+flux_hmi['neg'].values, linestyle='dashed',  label='HMI')
    ax.plot(flux_phi['pos'].values+flux_phi['neg'].values, linestyle='dashdot', label='PHI')

    xticks = np.linspace(0, 1440/latwidth, 19)-0.5
    xlabels = np.linspace(-90,90, 19, dtype=int)

    plt.axhline(y=0, color='grey', linestyle=(0,(5,10)), alpha=0.75)

    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabels)

    ax.set_xlabel('Latitude [°]')
    ax.set_ylabel('Magnetic Flux [mx/cm²]')
    ax.set_title(f'Average weak magnetic flux balance for ({thld_low}-{thld_high}G)')
    ax.set_ylim([-5,5])

    plt.legend(loc='lower right', ncol=2)

    plt.tight_layout()
    if pdf:
        pass
        #plt.savefig("flux_correction.pdf", format="pdf", dpi=300)
    else:
        plt.show()





def get_phi_hmi_windows(fits_table, deg2px=10):
    # find start and end of PHI and HMI data coverage in synoptic map
    
    window_phi = []
    window_hmi = []

    for row in fits_table:
        # make the colored boxes for each fits table line

        if row['SRC'] == 'HMI': 
            width = row["CRLN_START"] - row["CRLN_END"]

            if width > 0:
                window_hmi.append([int(row["CRLN_END"]*deg2px), int(row["CRLN_START"]*deg2px)])
            else:
                window_hmi.append([row["CRLN_END"]*deg2px, 360*deg2px])
                window_hmi.append([0*deg2px, row["CRLN_START"]*deg2px])

    window_hmi = sorted(window_hmi)
    
    for i, (x1, x2) in enumerate(window_hmi):
        if i == 0:
            if x1 > 0:
                window_phi.append([0, x1])
        else:
            window_phi.append([window_hmi[i-1][1], x1])

        if i == len(window_hmi)-1:
            if x2 < 360*deg2px:
                window_phi.append([x2, 360*deg2px])

    return window_hmi, window_phi



def noise_plot_longitudes(flux_phi, flux_hmi, thld_low, thld_high, fits_table, latwidth=10, pdf=False):

    bar_height = 40
    labelsize = 12
    suptitlesize=16

    ytick_latitude = []
    ytick_normalize = []
    for i in range(19):
        calculation = np.sin((np.pi/18)*(i-9.0))
        ytick_latitude.append(calculation)
        ytick_normalize.append((calculation+1)*720.)

    # make the plot
    fig, ax = plt.subplots(figsize=(14,6))
    fig.subplots_adjust(left=0,right=1,top=1,bottom=0)
    ax.tick_params(labelsize=14)
    
    
    # TODO    
    #im = plt.imshow(synop,cmap="hmimag",vmin=-1500,vmax=1500,origin='lower',extent=[0,3600,bar_height,1440+bar_height] , interpolation=None)
    #ax.set_title(f'PHI/HMI B {config.Btype} Synoptic Chart for Carrington Rotation {config.cr}', y=1.015, fontsize=suptitlesize)




    ax.tick_params(axis='both', which='both', labelbottom=True, labeltop=False, labelleft=True, labelright=True)

    # label the x-axis 
    xlabels    = [0,30,60,90,120,150,180,210,240,270,300,330,360]
    xlocations = [0,300,600,900,1200,1500,1800,2100,2400,2700,3000,3300,3600]
    ax.set_xticks(xlocations)
    ax.set_xticklabels(xlabels)
    ax.set_xlabel('Carrington Longitude [°]', fontsize=labelsize)

    # Create the latitude labels on the right-hand side of the plot
    ylabels_r = [' ','-80',' ','-60',' ','-40',' ','-20',' ','0',' ',' 20',' ',' 40',' ',' 60',' ',' 80',' ']
    ylocations_r = [y + bar_height for y in ytick_normalize]
    ax.set_ylim(0, 1440 + bar_height)
    ax.set_yticks(ylocations_r)
    ax.set_yticklabels(ylabels_r)
    ax.set_ylabel('Latitude [°]', fontsize=labelsize)
    ax.yaxis.labelpad=0
    ax.tick_params(labelsize=labelsize, axis='both', which='both', bottom=True, top=True, left=True, right=True, labelbottom=True, labeltop=False, labelleft=True, labelright=False)

    ax.set_xlim(0, 3600)

    # After `ax.imshow(...)` or similar:
    #divider = make_axes_locatable(ax)
    #cax = divider.append_axes("right", size="3%", pad=0.25)

    fig.subplots_adjust(left=0.06, right=0.94, top=1., bottom=0.025)

    # make the horizontal bar with color coded data sources
    deg2px = 10  
    for row in fits_table:
        # make the colored boxes for each fits table line
        color = 'steelblue' if row['SRC'] == 'HMI' else 'orange'
        width = row["CRLN_START"] - row["CRLN_END"]

        if width > 0:
            ax.barh(bar_height/2, width*deg2px, left=row["CRLN_END"]*deg2px, height=bar_height, color=color)
        else:
            # interval wraps around 0°
            ax.barh(bar_height/2, (360-row["CRLN_END"])*deg2px, left=row["CRLN_END"]*deg2px, height=bar_height, color=color)
            ax.barh(bar_height/2, row["CRLN_START"]*deg2px, left=0, height=bar_height, color=color)

        # add vertical black lines as boundaries
        ax.vlines(row["CRLN_END"]*deg2px, 0, bar_height, color='black', linewidth=0.7)
    
    ax.hlines(y=bar_height, xmin=0, xmax=360*deg2px, color='black',linewidth=0.7)

    phi_patch = mpatches.Patch(color='orange', label='PHI')
    hmi_patch = mpatches.Patch(color='steelblue', label='HMI')
    boundary_line = mlines.Line2D([], [], color='black', linewidth=0.7, label='Boundary')

    ax.legend(handles=[phi_patch, hmi_patch, boundary_line],loc='upper center',bbox_to_anchor=(0.12, -0.045), ncol=3, frameon=False)
    
    if pdf:
        pass
        #plt.savefig(os.path.join(outpath, f'{name}.pdf'), format='pdf')
    else:
        plt.show()




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

plot_synoptic_sources(phi_img, path, outname, config, phi_table, pdf=False)



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

# AVERAGE OVER HORIZONTAL LATITUDE WINDOWS

latwidth = 10  #px
lats = np.arange(0,1440, latwidth)

hmi_x1, hmi_x2 = 0,    2460
phi_x1, phi_x2 = 2460, 3600

thld_low  = 0
thld_high = 7.5

window_hmi, window_phi = get_phi_hmi_windows(phi_table, deg2px=10)

flux_hmi = []
flux_phi = []

for (x1, x2) in window_hmi:
    flux_hmi.append(magnetic_flux_latitudes(phi_img, lats, x1=x1, x2=x2, thld_low=thld_low, thld_high=thld_high, mean=True, med=False))

flux_hmi = sum(flux_hmi)/len(flux_hmi)

for (x1, x2) in window_phi:
    flux_phi.append(magnetic_flux_latitudes(phi_img, lats, x1=x1, x2=x2, thld_low=thld_low, thld_high=thld_high, mean=True, med=False))

flux_phi = sum(flux_phi)/len(flux_phi)

magnetic_flux_plot_latitudes(flux_phi, flux_hmi, thld_low, thld_high, latwidth=10, pdf=False)


noise_plot_longitudes(flux_phi, flux_hmi, thld_low, thld_high, phi_table, latwidth=10, pdf=False)
 
# AVERAGE OVER VERTICAL CADENCE WINDOWS





def get_cadence_windows(fits_table, deg2px=10):
    # make the horizontal bar with color coded data sources
    # TODO Cadence spaced slices for PHI, regular slices of similar width for HMI

    windows = []
    for row in fits_table:
        # make the colored boxes for each fits table line
        if row['SRC'] == 'HMI': 
            continue

        width = row["CRLN_START"] - row["CRLN_END"]

        if width > 0:
            windows.append()
            pass
            #ax.barh(bar_height/2, width*deg2px, left=row["CRLN_END"]*deg2px, height=bar_height, color=color)
        else:
            # interval wraps around 0°
            #ax.barh(bar_height/2, (360-row["CRLN_END"])*deg2px, left=row["CRLN_END"]*deg2px, height=bar_height, color=color)
            #ax.barh(bar_height/2, row["CRLN_START"]*deg2px, left=0, height=bar_height, color=color)
            pass





