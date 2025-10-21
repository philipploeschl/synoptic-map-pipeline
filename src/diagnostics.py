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

from scipy import optimize
import bisect

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



def noise_plot_longitudes(data, thld_low, thld_high, fits_table, latwidth=10, pdf=False):

    bar_height = -0.25
    labelsize = 12
    suptitlesize=16

    # make the plot
    fig, ax = plt.subplots(figsize=(14,6))
    fig.subplots_adjust(left=0,right=1,top=1,bottom=0)
    ax.tick_params(labelsize=14)

    pos, noise = noise_cadence_windows(data, fits_table)
    #colors = ["orange" if src == "PHI" else "steelblue" for src in phi_table["SRC"]][::-1]
    #if len(pos) > len(colors): colors.insert(0, 'orange')

    ax.scatter(pos, noise, s=7.5, label='Gaussian Noise')             

    ax.tick_params(axis='both', which='both', labelbottom=True, labeltop=False, labelleft=True, labelright=True)

    # label the x-axis 
    xlabels    = [0,30,60,90,120,150,180,210,240,270,300,330,360]
    xlocations = [0,300,600,900,1200,1500,1800,2100,2400,2700,3000,3300,3600]
    ax.set_xticks(xlocations)
    ax.set_xticklabels(xlabels)
    ax.set_xlabel('Carrington Longitude [°]', fontsize=labelsize)

    ax.tick_params(labelsize=labelsize, axis='both', which='both', bottom=True, top=True, left=True, right=True, labelbottom=True, labeltop=False, labelleft=True, labelright=False)

    ymax = 5
    ax.set_xlim(0, 3600)
    ax.set_ylim(bar_height, ymax)

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
        ax.vlines(row["CRLN_END"]*deg2px, bar_height, -bar_height+ymax, color='black', linewidth=0.7)

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


def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin() 
    return idx

def gauss(x,a,x0,sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))

def gaussian_fit(a, show=True):
    #a=np.histogram(data.flat,density=True,bins=100)
    xx = a[1][:-1] + (a[1][1]-a[1][0])/2
    y  = a[0][:]
    p0 = [0.,sum(xx*y)/sum(y),np.sqrt(sum(y * (xx - sum(xx*y)/sum(y))**2) / sum(y))]
    p0[0] = y[find_nearest(xx,p0[1])-5:find_nearest(xx,p0[1])+5].mean()
    p,cov = optimize.curve_fit(gauss,xx,y,p0=p0, maxfev=5000)
    if show:
        lbl = '{:.2e} $\pm$ {:.2e}'.format(p[1],p[2])
        plt.plot(xx,gauss(xx,*p),'r--', label=lbl)
        plt.legend(fontsize=9)
    return p


    
def noise_cadence_windows(data, fits_table, deg2px=10):
    # cadence_window_noise_plot
    noise = np.array([])
    mid   = np.array([])

    for row in fits_table:
        # make the colored boxes for each fits table line
        
        x1 = int(row["CRLN_END"]   * deg2px) # lower boundary
        x2 = int(row["CRLN_START"] * deg2px) # upper boundary
        width = x2 - x1
        #width =  (row["CRLN_START"] - row["CRLN_END"]) * deg2px

        if width > 0:
            #windows.append()    
            slice = data[:, x1:x2]
            center = x1+(x2-x1)/2

            bins = np.linspace(-1e2, 1e2, 200)
            counts, bin_edges = np.histogram(slice.ravel(), bins=bins, density=False)
            sigma = gaussian_fit([counts, bin_edges], show=False)[2]

            noise = np.append(noise, sigma)
            mid   = np.append(mid, center)
        
        else:
            # interval wraps around 0°
            #slice = np.hstack((data[:,:x1], data[:,x2:]))

            slice1 = data[:,:x2]
            slice2 = data[:,x1:]

            center1 = x2/2
            center2 = x1+(3600-x1)/2

            bins = np.linspace(-1e2, 1e2, 200)
            counts1, bin_edges1 = np.histogram(slice1.ravel(), bins=bins, density=False)
            sigma1 = gaussian_fit([counts1, bin_edges1], show=False)[2]

            counts2, bin_edges2 = np.histogram(slice2.ravel(), bins=bins, density=False)
            sigma2 = gaussian_fit([counts2, bin_edges2], show=False)[2]

            noise = np.append(noise, sigma1)
            noise = np.append(noise, sigma2)
            mid   = np.append(mid, center1)
            mid   = np.append(mid, center2)

    order = np.argsort(mid)

    mid = mid[order]
    noise = noise[order]
        
    return mid, noise


def combined_synoptic_noise_plot(data, fits_table, config, outpath, name, pdf=False):
    """
    Two-panel plot:
    Top: Synoptic map
    Bottom: Noise scatter
    PHI/HMI horizontal bars perfectly aligned between plots
    Colorbar only for top plot
    Legend in the empty bottom-right axis
    """

    fig = plt.figure(figsize=(14, 10.5))
    gs = GridSpec(2, 2, figure=fig, width_ratios=[30, 1], height_ratios=[1.5, 1],
                  hspace=0.05, wspace=0.05)

    # Main axes
    ax_synop = fig.add_subplot(gs[0, 0])
    ax_noise = fig.add_subplot(gs[1, 0], sharex=ax_synop)
    # Colorbar for top plot
    cax = fig.add_subplot(gs[0, 1])
    # Empty axis for legend
    ax_legend = fig.add_subplot(gs[1, 1])
    ax_legend.axis('off')  # hide axis

    labelsize = 12
    deg2px = 10
    bar_height = 40
    noise_bar_height = 0.15

    # -------------------------
    # (1) Synoptic Map
    # -------------------------
    im = ax_synop.imshow(
        data, cmap="hmimag", vmin=-1500, vmax=1500,
        origin="lower", extent=[0, 3600, bar_height, 1440 + bar_height],
        interpolation=None
    )

    ax_synop.set_title(
        f'PHI/HMI B {config.Btype} Synoptic Chart for Carrington Rotation {config.cr}',
        y=1.02, fontsize=14
    )

    # Add x-label on top plot
    #ax_synop.set_xlabel("Carrington Longitude [°]", fontsize=labelsize)

    # Longitude ticks
    xlabels = [0,30,60,90,120,150,180,210,240,270,300,330,360]
    xlocations = [i * 10 for i in xlabels]
    ax_synop.set_xticks(xlocations)
    ax_synop.set_xticklabels(xlabels)
    ax_synop.set_ylabel('Latitude [°]', fontsize=labelsize)
    ax_synop.tick_params(labelsize=labelsize)

    # Latitude ticks
    ylabels_r = [' ','-80',' ','-60',' ','-40',' ','-20',' ','0',' ','20',' ','40',' ','60',' ','80',' ']
    ytick_latitude = [np.sin((np.pi/18)*(i-9.0)) for i in range(19)]
    ytick_normalize = [(y+1)*720. + bar_height for y in ytick_latitude]
    ax_synop.set_yticks(ytick_normalize)
    ax_synop.set_yticklabels(ylabels_r)
    ax_synop.set_ylim(0, 1440+bar_height)

    # PHI/HMI horizontal bars (top)
    for row in fits_table:
        color = 'steelblue' if row['SRC'] == 'HMI' else 'orange'
        width = row["CRLN_START"] - row["CRLN_END"]
        if width > 0:
            ax_synop.barh(bar_height/2, width*deg2px, left=row["CRLN_END"]*deg2px,
                          height=bar_height, color=color)
        else:
            ax_synop.barh(bar_height/2, (360-row["CRLN_END"])*deg2px,
                          left=row["CRLN_END"]*deg2px, height=bar_height, color=color)
            ax_synop.barh(bar_height/2, row["CRLN_START"]*deg2px,
                          left=0, height=bar_height, color=color)
        ax_synop.vlines(row["CRLN_END"]*deg2px, 0, bar_height, color='black', linewidth=0.7)
    ax_synop.hlines(y=bar_height, xmin=0, xmax=360*deg2px, color='black', linewidth=0.7)

    # Colorbar
    cbar = fig.colorbar(im, cax=cax, orientation='vertical')
    label = '$B_r$ [Gauss]' if config.Mr else '$B_{LoS}$ [Gauss]'
    cbar.set_label(label=label, size=labelsize, labelpad=-15)

    # Make colorbar height match the synoptic map axis exactly and reduce width by 30%
    cax_pos = ax_synop.get_position()  # get synoptic axis position (Bbox)
    cax_width = 0.03 * 0.7  # 30% thinner than original width
    cax.set_position([cax_pos.x1 + 0.01, cax_pos.y0, cax_width, cax_pos.height])


    # -------------------------
    # (2) Noise Plot
    # -------------------------
    pos, noise = noise_cadence_windows(data, fits_table)
    ax_noise.scatter(pos, noise, s=7.5, color="black", label="Gaussian Noise")
    ax_noise.set_xlim(0, 3600)
    ylim_noise = 4
    ax_noise.set_ylim(-noise_bar_height, ylim_noise)
    ax_noise.set_xlabel("Carrington Longitude [°]", fontsize=labelsize)
    ax_noise.set_ylabel("Noise [σ]", fontsize=labelsize)
    ax_noise.tick_params(labelsize=labelsize)
    ax_noise.set_xticks(xlocations)
    ax_noise.set_xticklabels(xlabels)
    
    # PHI/HMI horizontal bars (bottom) aligned with top
    for row in fits_table:
        color = 'steelblue' if row['SRC'] == 'HMI' else 'orange'
        width = row["CRLN_START"] - row["CRLN_END"]
        left_positions = []
        widths = []
        if width > 0:
            left_positions = [row["CRLN_END"]*deg2px]
            widths = [width*deg2px]
        else:
            left_positions = [row["CRLN_END"]*deg2px, 0]
            widths = [(360-row["CRLN_END"])*deg2px, row["CRLN_START"]*deg2px]
        for left, w in zip(left_positions, widths):
            ax_noise.barh(-noise_bar_height/2, w, left=left,
                          height=noise_bar_height, color=color)
            ax_noise.vlines(left, -noise_bar_height, noise_bar_height+ylim_noise, color='black', linewidth=0.7)
    ax_noise.hlines(y=0, xmin=0, xmax=360*deg2px, color='black', linewidth=0.7)

    # -------------------------
    # Legend in empty axis
    # -------------------------
    phi_patch = mpatches.Patch(color='orange', label='PHI')
    hmi_patch = mpatches.Patch(color='steelblue', label='HMI')
    boundary_line = mlines.Line2D([], [], color='black', linewidth=0.7, label='Boundary')

    ax_noise.legend(handles=[phi_patch, hmi_patch, boundary_line],
                    loc='upper center',bbox_to_anchor=(0.15, -0.05), 
                    ncol=3, frameon=False)
    
    # --- Save or show ---
    fig.tight_layout()
    if pdf:
        os.makedirs(outpath, exist_ok=True)
        fig.savefig(os.path.join(outpath, f'{name}.pdf'), format='pdf')
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

combined_synoptic_noise_plot(phi_img, phi_table, config, path, outname, pdf=False)