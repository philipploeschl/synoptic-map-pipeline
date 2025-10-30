
import os, glob
import pandas as pd
import numpy as np
from scipy import optimize
from astropy.io import fits
import drms
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from config.config import Config
from utils.plots import magnetic_flux_plot_latitudes, combined_synoptic_noise_plot

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

    flux = pd.DataFrame(columns=['pos', 'neg'], dtype=float)

    for i in range(len(lats)-1):
        #print(lats[i], lats[i+1])
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

        flux_row = pd.DataFrame([[pos, neg]], columns=['pos', 'neg'])
        flux = pd.concat([flux, flux_row])

    return flux



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


    
def noise_cadence_windows(data, fits_table, thld_low=0, thld_high=5000, deg2px=10):
    # cadence_window_noise_plot
    noise = np.array([])
    mid   = np.array([])
    
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



########################
####### ANALYSIS #######
########################

def diagnostics(phi_img, phi_table, path, outname, config, thld_low=0, thld_high=10):

    latwidth = 10  #px
    lats = np.arange(0,1440+latwidth, latwidth)

    window_hmi, window_phi = get_phi_hmi_windows(phi_table, deg2px=10)

    flux_hmi = []
    flux_phi = []

    for (x1, x2) in window_hmi:
        flux_hmi.append(magnetic_flux_latitudes(phi_img, lats, x1=x1, x2=x2, thld_low=thld_low, thld_high=thld_high, mean=True, med=False))

    flux_hmi = sum(flux_hmi)/len(flux_hmi)

    for (x1, x2) in window_phi:
        flux_phi.append(magnetic_flux_latitudes(phi_img, lats, x1=x1, x2=x2, thld_low=thld_low, thld_high=thld_high, mean=True, med=False))

    flux_phi = sum(flux_phi)/len(flux_phi)

    sine_lat = [np.sin((np.pi/18)*(i-9.0)) for i in range(19)]
    pix_lat  = [int((y+1)*720) for y in sine_lat]

    # pix_lat[6]  = +30°
    # pix_lat[12] = -30°

    pos1, noise1 = noise_cadence_windows(phi_img[:pix_lat[6],:],      phi_table, thld_low=thld_low, thld_high=thld_high)
    pos2, noise2 = noise_cadence_windows(phi_img[pix_lat[6]:pix_lat[12],:],  phi_table, thld_low=thld_low, thld_high=thld_high)
    pos3, noise3 = noise_cadence_windows(phi_img[pix_lat[12]:,:], phi_table, thld_low=thld_low, thld_high=thld_high)

    pos   = [pos1,   pos2,    pos3]
    noise = [noise1, noise2,  noise3]
    legend = ['[ -90°,  -30°]', '[ -30°, +30°]', '[+30°, +90°]']#

    with PdfPages(os.path.join(path, outname+'_diagnostics.pdf')) as pdf:
        magnetic_flux_plot_latitudes(flux_phi, flux_hmi, thld_low, thld_high, latwidth=10, pdf=pdf)
        combined_synoptic_noise_plot(phi_img, phi_table, pos, noise, legend, config, path, outname, pdf=pdf)



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
    tracer = tracing.FortranTracer(max_steps=2000)
    field_lines = tracer.trace(seeds, pfss_out)
    print('Finished tracing field lines')

    ###############################################################################
    # Plot the result. The to plot is the input magnetogram, and the bottom plot
    # shows a contour map of the the footpoint polarities, which are +/- 1 for open
    # field regions and 0 for closed field regions.
    
    if pdf:
        with PdfPages(os.path.join(path, name+'_pfss.pdf')) as pdf:
            plot_pfss(pfss_in, pfss_out, field_lines, lon_1d, lat_1d, nsteps, pdf=pdf)
    else:
        plot_pfss(pfss_in, pfss_out, field_lines, lon_1d, lat_1d, nsteps, pdf=None)




def plot_pfss(pfss_in, pfss_out, field_lines, lon_1d, lat_1d, nsteps, pdf=None):
    import matplotlib.colors as mcolor

    fig = plt.figure(figsize=(8,11.25))

    # --- First subplot ---
    ss_br = pfss_out.source_surface_br
    ax1 = fig.add_subplot(3, 1, 1, projection=ss_br)
    im1 = ss_br.plot()
    ax1.plot_coord(pfss_out.source_surface_pils[0])
    ax1.set_title('Source surface magnetic field')
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
    norm.vmin = None # -1500 # reset vmin 
    norm.vmax = None # +1500 # reset vmax
    ax3 = fig.add_subplot(3, 1, 3, projection=m)
    im3 = m.plot(cmap='hmimag')
    xx = pfss_in.map.data.shape[1]/360
    yy = pfss_in.map.data.shape[0]//2
    ax3.contourf(np.rad2deg(lon_1d)*xx, np.sin(lat_1d)*yy+yy, pols, norm=norm, cmap=cmap, alpha=0.25)
    ax3.plot_coord(pfss_out.source_surface_pils[0])
    ax3.set_title('Input magnetogram w/ PFSS & Open Field')
    plt.colorbar(im3, ax=ax3)  # Attach colorbar to ax3

    plt.tight_layout()
        
    if pdf:
        #os.makedirs(outpath, exist_ok=True)
        #fig.savefig(os.path.join(outpath, f'{name}.pdf'), format='pdf')
        pdf.savefig(fig)
    else:
        plt.show()

    plt.close()




def main(config, path):

    ############################
    ####### GET PHI DATA #######
    ############################

    #datapath = "CR2297_polar_2025_v01/"
    #datapath = "CR2297_v02_nimg7_cmin25/"

    #cwd = os.getcwd()
    #root = os.path.normpath(os.path.join(cwd, ".."))
    #path = os.path.join(root, config.output_path, datapath, config.synop_path)
    path = os.path.join(path, config.synop_path)

    fname = "synopMr.fits"
    outname = f"{config.cr}"

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
    series  = "hmi.synoptic_mr_polfil_720s"
    segment = "Mr_polfil"
    #series  = "hmi.synoptic_mr_720s"
    #segment = "synopMr"
    #series = "hmi.synoptic_ml_720s"
    #segment = "synopMl"
    datapath_hmi = os.path.join(root, f"data/tmp/CR{carrington_number}/")
    os.makedirs(datapath_hmi, exist_ok=True)


    # Query JSOC for that rotation
    q = c.query(f"{series}[{carrington_number}]", seg=segment)
    fname_hmi = q[segment][0].split('/')[-1]

    try:
        file_hmi = glob.glob(f"{datapath_hmi}*{fname_hmi}")[0]
        synop_hmi = fits.open(file_hmi)
    except IndexError:
        # Download the FITS file
        result = c.export(f"{series}[{carrington_number}]", method='url', protocol='fits')
        result.download(datapath_hmi)
        file_hmi = glob.glob(f"{datapath_hmi}*{fname_hmi}")[0]
        synop_hmi = fits.open(file_hmi)

    hmi_img = synop_hmi[1].data   

    # create mask of NaN values in phi_img and fill them with hmi_img values
    mask_polfil = np.isnan(phi_img)
    phi_polfil = np.where(mask_polfil, hmi_img, phi_img)    

    #synop_phi[0].header["CUNIT2"] = "deg" # "Sine Latitude"

    primary_hdu = fits.PrimaryHDU()

    polfil_hdu = fits.CompImageHDU(data=phi_polfil, 
                                   header=synop_phi[0].header, 
                                   compression_type='RICE_1')


    polfil_hdul = fits.HDUList([primary_hdu, polfil_hdu])
    polfil_hdul.writeto(os.path.join(path, "synopMr_polfil.fits"), overwrite=True)

    # show filled synoptic map 
    #plt.imshow(phi_polfil, cmap='hmimag', vmin=-1500, vmax=1500, origin='lower')

    diagnostics(phi_img, phi_table, path, outname, config, thld_low=0, thld_high=10)
    pfss(phi_polfil,        synop_hmi, path, name='PHI', pdf=True)
    pfss(synop_hmi[1].data, synop_hmi, path, name='HMI', pdf=True)


if __name__ == "__main__":

    out_dirs = ["output/CR2297_v02_nimg5_cmin5",
                "output/CR2297_v02_nimg5_cmin25", 
                "output/CR2297_v02_nimg7_cmin25"]

    cwd = os.getcwd()
    root = os.path.normpath(os.path.join(cwd, ".."))

    for out_dir in out_dirs:
        config = Config(config_path=os.path.join(root, out_dir, 'config.yaml'))
        path = os.path.join(root, out_dir)
        main(config, path)


