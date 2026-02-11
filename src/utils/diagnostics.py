
import os, glob
import pandas as pd
import numpy as np
from scipy import optimize
from astropy.io import fits
import drms
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pathlib import Path

from config.config import Config
from utils.plots import magnetic_flux_plot_latitudes, combined_synoptic_noise_plot, plot_synoptic_sources, plot_synoptic_with_stripe_magnitudes

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

    flux = pd.DataFrame(columns=['pos', 'neg'], dtype=float)

    for i in range(len(lats)-1):

        window = data[lats[i]:lats[i+1], x1:x2]
        
        pos = window[window > thld_low]
        pos = pos[pos < thld_high]
        
        neg = window[window < -1*thld_low]
        neg = neg[neg > -1*thld_high]

        if mean:
            if pos.size > 0 and not np.all(np.isnan(pos)):
                pos = np.nanmean(pos)
            else:
                pos = np.nan  # or 0, or some default
            
            if neg.size > 0 and not np.all(np.isnan(neg)):
                neg = np.nanmean(neg)
            else:
               neg = np.nan  # or 0, or some default

        if med:
            if pos.size > 0 and not np.all(np.isnan(pos)):
                pos = np.nanmedian(pos)
            else:
                pos = np.nan  # or 0, or some default
            
            if neg.size > 0 and not np.all(np.isnan(neg)):
                neg = np.nanmedian(neg)
            else:
                neg = np.nan  # or 0, or some default

        flux_row = pd.DataFrame({"pos":[pos], "neg":[neg]}) #[[pos, neg]], columns=['pos', 'neg'])
        flux = pd.concat([flux, flux_row], ignore_index=True)


    return flux



def get_phi_hmi_windows(fits_table, deg2px=10):
    # find start and end of PHI and HMI data coverage in synoptic map
    
    windows_phi = []
    windows_hmi = []

    # TODO CHANGE HMI WINDOWING AFTER HMI TABLE UPDATES!
    for row in fits_table:
        # make the colored boxes for each fits table line

        if row['SRC'] == 'HMI': 
            width = row["CRLN_START"] - row["CRLN_END"]

            if width > 0:
                windows_hmi.append([int(row["CRLN_END"]*deg2px), int(row["CRLN_START"]*deg2px)])
            else:
                windows_hmi.append([int(row["CRLN_END"]*deg2px), int(360*deg2px)])
                windows_hmi.append([int(0*deg2px), int(row["CRLN_START"]*deg2px)])

    windows_hmi = sorted(windows_hmi)
    
    """
    if len(window_hmi) > 0:
        for i, (x1, x2) in enumerate(window_hmi):
            if i == 0:
                if x1 > 0:
                    window_phi.append([0, x1])
            else:
                window_phi.append([window_hmi[i-1][1], x1])

            if i == len(window_hmi)-1:
                if x2 < 360*deg2px:
                    window_phi.append([x2, 360*deg2px])
    else:
        #window_phi.append([0, 360*deg2px])
    """ 
    crln_phi   = []
    for row in fits_table:
        if row['SRC'] == 'PHI':
            crln_phi.append(row['CRLN_OBS'])

    #print(crln_phi)
    windows_phi = filter_observation_windows(crln_phi, max_gap=30)

    windows_phi = (np.array(windows_phi)*deg2px).astype(int)
    #print(windows_phi)

    return windows_hmi, windows_phi


def filter_observation_windows(lon_obs, max_gap=30):

    """
    Identify contiguous observing windows where solar longitude coverage
    is continuous and no gap between measurements exceeds max_gap degrees.

    Parameters
    ----------
    lon_obs : list of float
        Observed Carrington longitudes in chronological order.
    max_gap : float
        Maximum allowed jump (in degrees) before declaring an observation gap.

    Returns
    -------
    list of [start_lon, end_lon]
        Start and end longitudes of each acceptable observation window.
    """

    if len(lon_obs)==0:
        return []

    windows = []
    start = lon_obs[0]
    prev  = lon_obs[0]

    for lon in lon_obs[1:]:
        if abs(lon - prev) > max_gap:
            # Gap detected → close current window
            # save in reverse for later function compatibilty
            windows.append([prev, start])
            start = lon  # start new window
        prev = lon

    # Close final window
    windows.append([prev, start])

    return windows


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
    
    try: 
        p,cov = optimize.curve_fit(gauss,xx,y,p0=p0, maxfev=25000)
    except RuntimeError:
        p = [np.nan, np.nan, np.nan]

    if show:
        lbl = '{:.2e} $\pm$ {:.2e}'.format(p[1],p[2])
        plt.plot(xx,gauss(xx,*p),'r--', label=lbl)
        plt.legend(fontsize=9)
    
    return p


    
def ar_filtering(img, high_thld=250.0, low_thld=25.0, empty=0.0):

    from skimage.morphology import reconstruction

    seed = np.abs(img) >= high_thld
    mask = np.abs(img) >= low_thld

    final_mask = reconstruction(
        seed.astype(np.uint8),
        mask.astype(np.uint8),
        method='dilation'
    ).astype(bool)
    filtered_img = np.where(final_mask, img, empty)

    return filtered_img, final_mask


def noise_cadence_windows(data, fits_table, thld_low=0, thld_high=5000, deg2px=10):
    # cadence_window_noise_plot

    (ny, nx) = data.shape

    noise  = np.array([])
    mid    = np.array([])
    offset = np.array([])

    mask = (np.abs(data) > thld_low) & (np.abs(data) < thld_high)
    data = np.where(mask, data, np.nan)    

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
            (_, avg, sigma) = gaussian_fit([counts, bin_edges], show=False)

            noise  = np.append(noise, sigma)
            mid    = np.append(mid, center)
            offset = np.append(offset, avg)
        
        else:
            # interval wraps around 0°
            #slice = np.hstack((data[:,:x1], data[:,x2:]))

            slice1 = data[:,:x2]
            slice2 = data[:,x1:]

            center1 = x2/2
            center2 = x1+(nx-x1)/2

            bins = np.linspace(-1e2, 1e2, 200)
            counts1, bin_edges1 = np.histogram(slice1.ravel(), bins=bins, density=False)
            (_, avg1, sigma1) = gaussian_fit([counts1, bin_edges1], show=False)

            counts2, bin_edges2 = np.histogram(slice2.ravel(), bins=bins, density=False)
            (_, avg2, sigma2) = gaussian_fit([counts2, bin_edges2], show=False)

            noise = np.append(noise, sigma1)
            noise = np.append(noise, sigma2)
            mid   = np.append(mid, center1)
            mid   = np.append(mid, center2)

            offset = np.append(offset, avg1)
            offset = np.append(offset, avg2)

    order = np.argsort(mid)

    mid = mid[order]
    noise = noise[order]
    offset = offset[order]

    return mid, noise, offset



########################
####### ANALYSIS #######
########################

def get_window_flux(synop_filtered, window, lats, latwidth, thld_low, thld_high, mean=True, med=False):

    flux_list = []
    (ny, nx) = synop_filtered.shape

    n_rows = ny//latwidth
    columns = ['pos', 'neg']
    nandf = pd.DataFrame(np.nan, index=range(n_rows), columns=columns)

    for (x1, x2) in window:
        flux_list.append(magnetic_flux_latitudes(synop_filtered, lats, x1=x1, x2=x2, thld_low=thld_low, thld_high=thld_high, mean=mean, med=med))

    # this gives the average flux over all PHI windows
    #flux_phi = sum(flux_phi)/len(flux_phi)

    if len(flux_list) > 1:
        flux_combined = pd.concat(flux_list)
        flux_out = flux_combined.groupby(flux_combined.index).mean()
    elif len(flux_list) == 1:
        flux_out = flux_list[0]
    else:
        flux_out = nandf

    return flux_out

    
def diagnostics(synop_img, synop_table, path, carrington_number, config, export=None, separate_maps=False, hmi_img=None):

    # ADAPT FOR COMBINED / PHI ONLY / HMI ONLY MAPS

    ar_thld_low  = config.diag_ar_thld_low
    ar_thld_high = config.diag_ar_thld_high 

    flux_thld_low  = config.diag_flux_thld_low 
    flux_thld_high = config.diag_flux_thld_high

    synop_filtered, synop_mask = ar_filtering(synop_img, high_thld=ar_thld_high, low_thld=ar_thld_low, empty=np.nan)
    synop_filtered = np.where(~synop_mask, synop_img, np.nan)

    (ny, nx) = synop_img.shape

    latwidth = 10  #px
    lats = np.arange(0,ny+latwidth, latwidth)
    print(synop_img.shape)
    #n_rows = ny//latwidth
    #columns = ['pos', 'neg']
    #nandf = pd.DataFrame(np.nan, index=range(n_rows), columns=columns)

    #print(f"phi_table{phi_table}")
    window_hmi, window_phi = get_phi_hmi_windows(synop_table, deg2px=10)

    flux_hmi = []
    flux_phi = []

    if separate_maps and hmi_img is not None:
        # use full HMI image for HMI flux calculation
        #x1 = 0
        #x2 = len(hmi_img[0])
        
        hmi_filtered, hmi_mask = ar_filtering(hmi_img, high_thld=ar_thld_high, low_thld=ar_thld_low, empty=np.nan)
        hmi_filtered = np.where(~hmi_mask, hmi_img, np.nan)

        # use PHI windows for comparable activity and pixel statistics
        #for (x1, x2) in window_phi:
        #    flux_hmi.append(magnetic_flux_latitudes(hmi_filtered, lats, x1=x1, x2=x2, thld_low=thld_low, thld_high=thld_high, mean=True, med=False))

        flux_hmi = get_window_flux(hmi_filtered, window_phi, lats, latwidth, flux_thld_low, flux_thld_high)
    else:
        # get HMI flux from window_hmi in combined synop_filtered
        #for (x1, x2) in window_hmi:
        #    flux_hmi.append(magnetic_flux_latitudes(synop_filtered, lats, x1=x1, x2=x2, thld_low=thld_low, thld_high=thld_high, mean=True, med=False))

        flux_hmi = get_window_flux(synop_filtered, window_hmi, lats, latwidth, flux_thld_low, flux_thld_high)

    # this gives the average flux over all HMI windows
    #flux_hmi = sum(flux_hmi)/len(flux_hmi)
    """
    if len(flux_hmi) > 1:
        flux_hmi_combined = pd.concat(flux_hmi)
        flux_hmi = flux_hmi_combined.groupby(flux_hmi_combined.index).mean()
    elif len(flux_hmi) == 1:
        flux_hmi = flux_hmi[0]
    else:
        flux_hmi = nandf
    """

    flux_phi = get_window_flux(synop_filtered, window_phi, lats, latwidth, flux_thld_low, flux_thld_high)

    """
    # Repeat for PHI
    for (x1, x2) in window_phi:
        #print(x1,x2)
        flux_phi.append(magnetic_flux_latitudes(synop_filtered, lats, x1=x1, x2=x2, thld_low=thld_low, thld_high=thld_high, mean=True, med=False))

    # this gives the average flux over all PHI windows
    #flux_phi = sum(flux_phi)/len(flux_phi)

    if len(flux_phi) > 1:
        flux_phi_combined = pd.concat(flux_phi)
        flux_phi = flux_phi_combined.groupby(flux_phi_combined.index).mean()
    elif len(flux_phi) == 1:
        flux_phi = flux_phi[0]
    else:
        flux_phi = nandf
    #print(flux_phi)
    #print(flux_hmi)
    """

    sine_lat = [np.sin((np.pi/18)*(i-9.0)) for i in range(19)]
    pix_lat  = [int((y+1)*720) for y in sine_lat]

    # pix_lat[6]  = +30°
    # pix_lat[12] = -30°

    pos1, noise1, offset1 = noise_cadence_windows(synop_filtered[:pix_lat[6],:],             synop_table, thld_low=flux_thld_low, thld_high=flux_thld_high)
    pos2, noise2, offset2 = noise_cadence_windows(synop_filtered[pix_lat[6]:pix_lat[12],:],  synop_table, thld_low=flux_thld_low, thld_high=flux_thld_high)
    pos3, noise3, offset3 = noise_cadence_windows(synop_filtered[pix_lat[12]:,:],            synop_table, thld_low=flux_thld_low, thld_high=flux_thld_high)

    pos    = [pos1,    pos2,    pos3]
    noise  = [noise1,  noise2,  noise3]
    offset = [offset1, offset2, offset3]

    legend = ['[ -90°,  -30°]', '[ -30°, +30°]', '[+30°, +90°]']#
    
    if config.Mr: component = "B_r"
    else: component = "B_LoS"

    with PdfPages(os.path.join(path, f'CR{carrington_number}_diagnostics.pdf')) as pdf:
        fig_mag = magnetic_flux_plot_latitudes(flux_phi, flux_hmi, flux_thld_low, flux_thld_high, latwidth=10, save=True)
        #fig_syn = combined_synoptic_noise_plot(synop_img, synop_table, pos, noise, offset, legend, config, path, carrington_number, save=True)
        fig_syn = combined_synoptic_noise_plot(synop_img, synop_table, pos, noise, offset, legend, config, save=True)
        pdf.savefig(fig_mag)
        pdf.savefig(fig_syn)
        fig_mag.savefig(os.path.join(path, f'CR{carrington_number}_latflux.png'), format='png')
        fig_syn.savefig(os.path.join(path, f'CR{carrington_number}_noise.png'),   format='png')

        plot_synoptic_sources(synop_img, component, path, f'CR{carrington_number}_synoptic', carrington_number, synop_table, save=True)

    if export: export_magnetic_flux(flux_phi, flux_hmi, carrington_number, file=export)



def export_magnetic_flux(flux_phi, flux_hmi, cr, file):

    #is_empty = (not os.path.exists(file)) or os.path.getsize(file) == 0

    hmi_avg = np.round(np.nanmean(flux_hmi['pos'].values+flux_hmi['neg'].values), 3)
    hmi_std = np.round(np.nanstd (flux_hmi['pos'].values+flux_hmi['neg'].values), 3)    
    hmi_rms = np.round(np.nanstd (flux_hmi['pos'].values+flux_hmi['neg'].values)/len(flux_hmi['pos']), 3)          

    phi_avg = np.round(np.nanmean(flux_phi['pos'].values+flux_phi['neg'].values), 3)
    phi_std = np.round(np.nanstd (flux_phi['pos'].values+flux_phi['neg'].values), 3)
    phi_rms = np.round(np.nanstd (flux_phi['pos'].values+flux_phi['neg'].values)/len(flux_phi['pos']), 3)

    with open(file, 'a') as f:
        #if is_empty:
        #    # write header or first line
        #    f.write("#cr,hmi_avg,hmi_std,hmi_rms,phi_avg,phi_std,phi_rms\n")

        # write your data row
        f.write(f"{cr},{hmi_avg},{hmi_std},{hmi_rms},{phi_avg},{phi_std},{phi_rms}\n")



def pfss(phi_polfil, synop_hmi, path, name=None, pdf=False):
        
    ########################
    ######### PFSS #########
    ########################
    from astropy import units as u
    from astropy import constants as const
    import sunpy.map
    from astropy.coordinates import SkyCoord
    import pfsspy
    from pfsspy import tracing
    import matplotlib.colors as mcolor


    ###############################################################################
    # Since this map is far to big to calculate a PFSS solution quickly, lets
    # resample it down to a smaller size.
    
    #phi_map.meta["CUNIT2"] = "deg" # "Sine Latitude"

    phi_map = sunpy.map.Map(phi_polfil, dict(synop_hmi[1].header))
    phi_map = phi_map.resample([720, 360] * u.pix)
    #phi_map = phi_map.resample([480, 240] * u.pix)
    #phi_map = phi_map.resample([360, 180] * u.pix)
    
    #print('New shape: ', phi_map.data.shape)

    ###############################################################################
    # Now calculate the PFSS solution
    #nrho = 25
    nrho = 50
    rss = 2.5
    pfss_in = pfsspy.Input(phi_map, nrho, rss)
    pfss_out = pfsspy.pfss(pfss_in)

    ###############################################################################
    # Finally, using the 3D magnetic field solution we can trace some field lines.
    # In this case a grid of 90 x 180 points equally gridded in theta and phi are
    # chosen and traced from the source surface outwards.
    #
    # First, set up the tracing seeds

    r = const.R_sun
    # Number of steps in cos(latitude)
    nsteps = 90
    lon_1d = np.linspace(0, 2 * np.pi, nsteps * 2 + 1)
    lat_1d = np.arcsin(np.linspace(-1, 1, nsteps + 1))
    lon, lat = np.meshgrid(lon_1d, lat_1d, indexing='ij')
    lon, lat = lon*u.rad, lat*u.rad
    seeds = SkyCoord(lon.ravel(), lat.ravel(), r, frame=pfss_out.coordinate_frame)

    ###############################################################################
    # Trace the field lines
    print('Tracing field lines...')
    tracer = tracing.FortranTracer(max_steps=5000)
    field_lines = tracer.trace(seeds, pfss_out)
    print('Finished tracing field lines')

    ###############################################################################
    # Plot the result. The to plot is the input magnetogram, and the bottom plot
    # shows a contour map of the the footpoint polarities, which are +/- 1 for open
    # field regions and 0 for closed field regions.
    
    if pdf:
        with PdfPages(os.path.join(path, f'CR{synop_hmi[1].header["CAR_ROT"]}_{name}_pfss_mag{phi_map.data.shape[1]}x{phi_map.data.shape[0]}_nrho{nrho}_nsteps{nsteps}.pdf')) as pdf:
            fig = plot_pfss(pfss_in, pfss_out, field_lines, lon_1d, lat_1d, nsteps, name, pdf=pdf)
            pdf.savefig(fig)
            fig.savefig(os.path.join(path, f'CR{synop_hmi[1].header["CAR_ROT"]}_{name}_pfss_mag{phi_map.data.shape[1]}x{phi_map.data.shape[0]}_nrho{nrho}_nsteps{nsteps}.png'), format='png')
           
    else:
        fig = plot_pfss(pfss_in, pfss_out, field_lines, lon_1d, lat_1d, nsteps, pdf=None)
    




def plot_pfss(pfss_in, pfss_out, field_lines, lon_1d, lat_1d, nsteps, name, pdf=None):
    import matplotlib.colors as mcolor

    fig = plt.figure(figsize=(8,11.25))

    # --- First subplot ---
    ss_br = pfss_out.source_surface_br
    ax1 = fig.add_subplot(3, 1, 1, projection=ss_br)
    im1 = ss_br.plot()
    ax1.plot_coord(pfss_out.source_surface_pils[0])
    ax1.set_title(f'Source surface magnetic field')
    plt.colorbar(im1, ax=ax1)  # Attach colorbar to ax1

    # --- Second subplot ---
    ax2 = fig.add_subplot(3, 1, 2)
    cmap = mcolor.ListedColormap(['tab:red', 'black', 'tab:blue'])
    norm = mcolor.BoundaryNorm([-1.5, -0.5, 0.5, 1.5], ncolors=3)
    pols = field_lines.polarities.reshape(2 * nsteps + 1, nsteps + 1).T
    cf2 = ax2.contourf(np.rad2deg(lon_1d), np.sin(lat_1d), pols, norm=norm, cmap=cmap)
    ax2.set_ylabel('sin(latitude)')
    ax2.set_title('Open (blue/red) and closed (black) field')
    ax2.set_aspect(0.5 * 360 / 2)
    plt.colorbar(cf2, ax=ax2)  # Attach colorbar to ax2

    # --- Third subplot ---
    m = pfss_in.map # Create a norm with the limits you want 
    norm = m.plot_settings['norm'] # get existing norm 
    norm.vmin = None #-1500 # reset vmin 
    norm.vmax = None #+1500 # reset vmax
    ax3 = fig.add_subplot(3, 1, 3, projection=m)
    im3 = m.plot(cmap='hmimag', vmin=-1500, vmax=1500)
    xx = pfss_in.map.data.shape[1]/360
    yy = pfss_in.map.data.shape[0]//2
    ax3.contourf(np.rad2deg(lon_1d)*xx, np.sin(lat_1d)*yy+yy, pols, norm=norm, cmap=cmap, alpha=0.25)
    ax3.plot_coord(pfss_out.source_surface_pils[0])
    ax3.set_title(f'{name} input magnetogram w/ PFSS & Open Field')
    plt.colorbar(im3, ax=ax3)  # Attach colorbar to ax3

    plt.tight_layout()
        
    if pdf: 
        return fig
    else: 
        plt.show()

    plt.close()



def main(path, carrington_number, run_diagnostics=True, run_pfss=True, export_diagnostics=None, separate_maps=True, fname="synopMr.fits", series="hmi.synoptic_mr_polfil_720s", segment="Mr_polfil"):

    print(f"Processing {os.path.join(path, fname)}...")

    root = os.getcwd()

    ############################
    ####### GET PHI DATA #######
    ############################

    try:
        synop_phi  = fits.open(os.path.join(path, fname))
    except FileNotFoundError:
        # skip folders without processed synoptic fits files
        return 0
    
    phi_img   = synop_phi[0].data
    phi_table = synop_phi[1].data

    # Define Carrington rotation number
    #carrington_number = int(synop_phi[0].header["CAR_ROT"])
    outname = f"{carrington_number}"


    ############################
    ####### GET HMI DATA #######
    ############################

    # Create DRMS client
    c = drms.Client(email="loeschl@mps.mpg.de", verbose=True)

    datapath_hmi = os.path.join(root, f"../data/tmp/CR{carrington_number}/")
    os.makedirs(datapath_hmi, exist_ok=True)

    # Query JSOC for that rotation
    q = c.query(f"{series}[{carrington_number}]", seg=segment)
    fname_hmi = q[segment][0].split('/')[-1]

    try:
        file_hmi  = glob.glob(f"{datapath_hmi}*{fname_hmi}")[0]
        synop_hmi = fits.open(file_hmi)
    except IndexError:
        # Download the FITS file
        result = c.export(f"{series}[{carrington_number}]", method='url', protocol='fits')
        result.download(datapath_hmi)
        file_hmi  = glob.glob(f"{datapath_hmi}*{fname_hmi}")[0]
        synop_hmi = fits.open(file_hmi)


    hmi_img = synop_hmi[1].data   
    
    # create mask of NaN values in phi_img and fill them with hmi_img values
    mask_polfil = np.isnan(phi_img)
    phi_polfil  = np.where(mask_polfil, hmi_img, phi_img)    
    
    # aggressive HMI pole filling
    #phi_polfil[:40, :]  = hmi_img[:40, :]
    #phi_polfil[1400: :] = hmi_img[1400:, :]

    #synop_phi[0].header["CUNIT2"] = "deg" # "Sine Latitude"

    primary_hdu = fits.PrimaryHDU()

    polfil_hdu = fits.CompImageHDU(data=phi_polfil, 
                                   header=synop_phi[0].header, 
                                   compression_type='RICE_1')

    polfil_hdul = fits.HDUList([primary_hdu, polfil_hdu])
    polfil_hdul.writeto(os.path.join(path, "synopMr_polfil.fits"), overwrite=True)

    # show filled synoptic map 
    #plt.imshow(phi_polfil, cmap='hmimag', vmin=-1500, vmax=1500, origin='lower')
    #plt.show()

    # populate config for diagnostics plots
    config = Config(path / "../config.yaml")
    #config.cr = carrington_number
    config.update("cr", carrington_number)

    if "Mr" in segment:
        config.Mr = True
        config.Btype = "Radial"
    else:
        config.Mr = False
        config.Btype = "line-of-sight"

    if run_diagnostics:
        diagnostics(phi_img, phi_table, path, outname, config, export=export_diagnostics, separate_maps=separate_maps, hmi_img=hmi_img)
    
    if run_pfss:
        pfss(phi_polfil,        synop_hmi, path, name='PHI-HMI', pdf=True)
        pfss(synop_hmi[1].data, synop_hmi, path, name='HMI',     pdf=True)




def flux_statistics(file, outname):

    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy.stats import linregress
    from scipy.optimize import curve_fit
    """
    data = {       
        'x':       [   1,        2,      3,      4,      5,        6,       7,      8,      9,     10,     11,    12,      13,    14,      15,    16,     17],
        'CR':      [2284,     2285,   2286,   2287,   2288,     2289,    2290,   2291,   2292,   2293,   2294,   2295,   2296,  2297,    2298,  2299,   2300],
        'HMI':     [-0.016,	-0.344,	-0.262,	-0.063,	  0.05,	  np.nan,   0.009, np.nan, -0.013,	0.336,	 0.42, np.nan,	0.414,	0.083, -0.141, 0.134, -0.071],
        'HMI_err': [0.001,   0.007,	 0.007,  0.006,  0.002,	  np.nan,   0.001, np.nan,  0.007,  0.007,	0.005, np.nan,  0.007,	0.001,	0.002, 0.007,  0.001],
        'PHI':     [0.1,    -0.076, -0.405,  0.058,  0.295,   np.nan,   0.081, np.nan, -0.085,  0.462,  0.868, np.nan, -0.035,  0.325,   0.39, 0.461,  0.323],
        'PHI_err': [0.003,   0.002,  0.002,  0.002,  0.003,   np.nan,   0.008, np.nan,  0.009,  0.008,  0.007, np.nan,  0.002,  0.004,  0.003, 0.003,  0.005]
    }
    df = pd.DataFrame(data)
    """

    df = pd.read_csv(file, comment=None)

    df = df.rename(columns={
        "cr": "CR",
        "hmi_avg": "HMI",
        "hmi_std": "HMI_err",
        "phi_avg": "PHI",
        "phi_std": "PHI_err",
    })

    # x follows the same increments as CR
    df["x"] = df["CR"] - df["CR"].iloc[0] + 1

    df = df[["x", "CR", "HMI", "HMI_err", "PHI", "PHI_err"]]


    mask = ~np.isnan(df['HMI']) & ~np.isnan(df['PHI'])
    x_fit    = df['x'][mask]
    yhmi_fit = df['HMI'][mask]
    yphi_fit = df['PHI'][mask]

    # --- Linear regression ---
    slope1, intercept1, r_value1, p_value1, std_err1 = linregress(x_fit, yhmi_fit)
    fit_line1 = intercept1 + slope1 * df['x']

    slope2, intercept2, r_value2, p_value2, std_err2 = linregress(x_fit, yphi_fit)
    fit_line2 = intercept2 + slope2 * df['x']

    # --- Define model ---
    def cosine(x, A, f, phi, C):
        return A * np.cos(2 * np.pi * f * x + phi) + C

    # initial guesses
    p0 = [2, 0.1, 0, 1]
    params1, cov1 = curve_fit(cosine, x_fit, yhmi_fit, p0=p0)
    params2, cov2 = curve_fit(cosine, x_fit, yphi_fit, p0=p0)
    
    # --- Plot ---
    plt.figure(figsize=(7, 5))
    plt.errorbar(df['x'], df['HMI'], yerr=df['HMI_err'], color='tab:blue', fmt='o', capsize=5, label='HMI')
    #plt.plot(df['x'], fit_line1, linestyle='--', color='tab:blue', label=f'Linear fit HMI: y={slope1:.2f}x+{intercept1:.2f}')
    #plt.plot(df['x'], cosine(df['x'], *params1), color='tab:blue', linestyle='--', label=f'y_HMI = A × cos(2π f x + φ) + {params1[3]:.3f}G')#f'Cosine Fit {params1[0]:.2f}  cos(2π {params1[1]:.2f} x + {params1[2]:.2f}) + {params1[3]:.2f}')

    plt.errorbar(df['x'], df['PHI'], yerr=df['PHI_err'], color='tab:orange', fmt='o', capsize=5, label='PHI')
    #plt.plot(df['x'], fit_line2, linestyle='--', color='tab:orange', label=f'Linear fit PHI: y={slope2:.2f}x+{intercept2:.2f}')
    #plt.plot(df['x'], cosine(df['x'], *params2), color='tab:orange', linestyle='--', label=f'y_PHI  = A × cos(2π f x + φ) + {params2[3]:.3f}G')#f'Cosine Fit {params1[0]:.2f}  cos(2π {params1[1]:.2f} x + {params1[2]:.2f}) + {params1[3]:.2f}')

    # --- Labels and legend ---
    xlim = (df["CR"].iloc[-1]-df["CR"].iloc[0])+2
    plt.xlabel('CR')
    plt.ylabel('Average Magnetic Flux [Mx/cm²]')
    plt.xlim(0, xlim)
    plt.ylim(-1.5, 1.5)
    plt.xticks(ticks=df['x'], labels=df['CR'], rotation=45) 
    plt.title('Average HMI & PHI Flux')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(file.parent / outname, format='png', dpi=300)

    plt.show()


def extract_cr(name: str) -> int:
    # name like "CR1234" or "CR1234_PHI"
    base = name.split("_")[0]    # → "CR1234"
    return int(base[2:])          # extract number


def stripe_pattern_magnitude(path):
    import matplotlib.patches as patches
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    cr =  extract_cr(path.parent.name)
    synop = fits.open(path / "synopMr.fits")

    img = synop[0].data
    fits_table = synop[1].data

    config = Config(path / "../config.yaml")
    plot_synoptic_with_stripe_magnitudes(img, path, f"CR{cr}_stripe_pattern_magnitudes", config, fits_table, pdf=True)



if __name__ == "__main__":

    # function call from pipeline modules  "diagnostics(synop_img, table_hdu.data, synop_outpath, config['synop_name'][:-5], global_config)"
    
    start_cr = 2279
    end_cr   = 2306

    only_flux_statistics = False
    only_stripes         = False
    run_pfss             = False
    run_diagnostics      = True

    #base = Path('/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/output/release_2025_v01/l3/syn/PHIHMI')
    #base = Path('/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/output/PHI_only/')
    #base = Path('/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/output/vector_tests/')
    #base = Path('/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/output/release_2025_v01/l3/syn/PHI')
    base = Path('/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/output/release_2025_v02/l3/syn/PHIHMI')

    diag_out = base / 'flux_diagnostics.csv'
    
    paths = sorted(base.glob("CR*/synop/"))
    paths = [p for p in paths if start_cr <= extract_cr(p.parent.name) <= end_cr]

    if only_flux_statistics: 
        flux_statistics(diag_out, 'flux_statistics_new.png')
    
    elif only_stripes:
        for path in paths:
            stripe_pattern_magnitude(path)

    else:
        with open(diag_out, 'w') as f:
            f.write("cr,hmi_avg,hmi_std,hmi_rms,phi_avg,phi_std,phi_rms\n")

        for path in paths:
            try: 
                main(path, extract_cr(path.parent.name), run_diagnostics=run_diagnostics, run_pfss=run_pfss, export_diagnostics=diag_out, fname="synopMr.fits", series="hmi.synoptic_mr_polfil_720s", segment="Mr_polfil")
            except Exception as e:
                print(f"An error occurred: {e}")
                continue
        
        flux_statistics(diag_out, 'flux_statistics_new.png')
                
