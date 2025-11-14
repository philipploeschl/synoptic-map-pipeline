
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
from utils.plots import magnetic_flux_plot_latitudes, combined_synoptic_noise_plot, plot_synoptic_sources

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
    
    window_phi = []
    window_hmi = []

    for row in fits_table:
        # make the colored boxes for each fits table line

        if row['SRC'] == 'HMI': 
            width = row["CRLN_START"] - row["CRLN_END"]

            if width > 0:
                window_hmi.append([int(row["CRLN_END"]*deg2px), int(row["CRLN_START"]*deg2px)])
            else:
                window_hmi.append([int(row["CRLN_END"]*deg2px), int(360*deg2px)])
                window_hmi.append([int(0*deg2px), int(row["CRLN_START"]*deg2px)])

    window_hmi = sorted(window_hmi)
    
    # This won't work without an HMI window
    # Define PHI window independent of HMI windows
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
        crln_start = []
        crln_end   = []
        crln_obs   = []
        for row in fits_table:
            if row['SRC'] == 'PHI':
                crln_start.append(row['CRLN_START'])
                crln_end.append(row['CRLN_END'])
                crln_obs.append(row['CRLN_OBS'])
        # WARNING: This doesn't account for observation gaps!
        print(crln_obs)
        window_phi.append([int(np.min(crln_obs)*deg2px), int(np.max(crln_obs)*deg2px)])

        gap_max = 30 # degrees = about 2 days

        tmp = crln_obs
        tmp = np.insert(tmp, 0, 360)
        tmp = np.insert(tmp, len(tmp), 0)
        gaps = np.abs(np.diff(tmp))
        print(gaps)
        print(len(gaps), len(tmp))
        borders = np.where(gaps > gap_max)[0]
        print(borders)
        print(tmp[borders[0]])
        """
        iend = np.where(np.diff(cr_dict['CAR_ROT']))[0]
        istart = np.where(np.diff(cr_dict['CAR_ROT']))[0]+1
        istart = np.insert(istart, 0, 0) # add first index


        for i, start in enumerate(istart):
            # add 0 and 360 to the list of observed clons to calculate gaps correctly
            if i < len(istart)-1:
                tmp = cr_dict['CRLN_OBS'][istart[i]:istart[i+1]]
                tmp = np.insert(tmp, 0, 360)
                tmp = np.insert(tmp, len(tmp), 0)
                gaps = np.sort(np.abs(np.diff(tmp)))
            else:
                tmp = cr_dict['CRLN_OBS'][istart[i]:]
                tmp = np.insert(tmp, 0, 360)
                tmp = np.insert(tmp, len(tmp), 0)
                gaps = np.sort(np.abs(np.diff(tmp)))

            gap = np.max(gaps)

            if np.any(gaps > gap_max):
                print(f"{cr_dict['CAR_ROT'][start]} incomplete | largest gap: {gap:.2f} degrees | {gaps[-3:]}")
            else:
                print(f"{cr_dict['CAR_ROT'][start]} complete   | largest gap: {gap:.2f} degrees | {gaps[-3:]}")
        """

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
    
    try: 
        p,cov = optimize.curve_fit(gauss,xx,y,p0=p0, maxfev=25000)
    except RuntimeError:
        p = [np.nan, np.nan, np.nan]

    if show:
        lbl = '{:.2e} $\pm$ {:.2e}'.format(p[1],p[2])
        plt.plot(xx,gauss(xx,*p),'r--', label=lbl)
        plt.legend(fontsize=9)
    
    return p


    
def noise_cadence_windows(data, fits_table, thld_low=0, thld_high=5000, deg2px=10):
    # cadence_window_noise_plot
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
            center2 = x1+(3600-x1)/2

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

def diagnostics(phi_img, phi_table, path, outname, config, thld_low=0, thld_high=10):

    latwidth = 10  #px
    lats = np.arange(0,1440+latwidth, latwidth)
    
    n_rows = 1440//latwidth
    columns = ['pos', 'neg']
    nandf = pd.DataFrame(np.nan, index=range(n_rows), columns=columns)

    print(f"phi_table{phi_table}")
    window_hmi, window_phi = get_phi_hmi_windows(phi_table, deg2px=10)

    flux_hmi = []
    flux_phi = []

    for (x1, x2) in window_hmi:
        flux_hmi.append(magnetic_flux_latitudes(phi_img, lats, x1=x1, x2=x2, thld_low=thld_low, thld_high=thld_high, mean=True, med=False))

    # this gives the average flux over all HMI windows
    #flux_hmi = sum(flux_hmi)/len(flux_hmi)
    if len(flux_hmi) > 1:
        flux_hmi_combined = pd.concat(flux_hmi)
        flux_hmi = flux_hmi_combined.groupby(flux_hmi_combined.index).mean()
    elif len(flux_hmi) == 1:
        flux_hmi = flux_hmi[0]
    else:
        flux_hmi = nandf

    for (x1, x2) in window_phi:
        flux_phi.append(magnetic_flux_latitudes(phi_img, lats, x1=x1, x2=x2, thld_low=thld_low, thld_high=thld_high, mean=True, med=False))

    # this gives the average flux over all PHI windows
    #flux_phi = sum(flux_phi)/len(flux_phi)

    if len(flux_phi) > 1:
        flux_phi_combined = pd.concat(flux_phi)
        flux_phi = flux_phi_combined.groupby(flux_phi_combined.index).mean()
    elif len(flux_phi) == 1:
        flux_phi = flux_phi[0]
    else:
        flux_phi = nandf

    sine_lat = [np.sin((np.pi/18)*(i-9.0)) for i in range(19)]
    pix_lat  = [int((y+1)*720) for y in sine_lat]

    # pix_lat[6]  = +30°
    # pix_lat[12] = -30°

    pos1, noise1, offset1 = noise_cadence_windows(phi_img[:pix_lat[6],:],             phi_table, thld_low=thld_low, thld_high=thld_high)
    pos2, noise2, offset2 = noise_cadence_windows(phi_img[pix_lat[6]:pix_lat[12],:],  phi_table, thld_low=thld_low, thld_high=thld_high)
    pos3, noise3, offset3 = noise_cadence_windows(phi_img[pix_lat[12]:,:],            phi_table, thld_low=thld_low, thld_high=thld_high)

    pos    = [pos1,    pos2,    pos3]
    noise  = [noise1,  noise2,  noise3]
    offset = [offset1, offset2, offset3]

    legend = ['[ -90°,  -30°]', '[ -30°, +30°]', '[+30°, +90°]']#

    with PdfPages(os.path.join(path, f'CR{outname}_diagnostics.pdf')) as pdf:
        fig_mag = magnetic_flux_plot_latitudes(flux_phi, flux_hmi, thld_low, thld_high, latwidth=10, save=True)
        fig_syn = combined_synoptic_noise_plot(phi_img, phi_table, pos, noise, offset, legend, config, path, outname, save=True)
        pdf.savefig(fig_mag)
        pdf.savefig(fig_syn)
        fig_mag.savefig(os.path.join(path, f'CR{outname}_latflux.png'), format='png')
        fig_syn.savefig(os.path.join(path, f'CR{outname}_noise.png'),   format='png')

        plot_synoptic_sources(phi_img, path, f'CR{outname}_synoptic', config, phi_table, pdf=True)


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




def main(path, run_diagnostics=True, run_pfss=True, fname="synopMr.fits", series="hmi.synoptic_mr_polfil_720s", segment="Mr_polfil"):

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
    carrington_number = int(synop_phi[0].header["CAR_ROT"])
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
    plt.imshow(phi_polfil, cmap='hmimag', vmin=-1500, vmax=1500, origin='lower')
    plt.show()

    # populate config for diagnostics plots
    config = Config()
    config.cr = carrington_number
   
    if "Mr" in segment:
        config.Mr = True
        config.Btype = "Radial"
    else:
        config.Mr = False
        config.Btype = "line-of-sight"

    if run_diagnostics:
        diagnostics(phi_img, phi_table, path, outname, config, thld_low=0, thld_high=10)
    
    if run_pfss:
        pfss(phi_polfil,        synop_hmi, path, name='PHI-HMI', pdf=True)
        pfss(synop_hmi[1].data, synop_hmi, path, name='HMI', pdf=True)




def flux_statistics():

    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy.stats import linregress
    from scipy.optimize import curve_fit

    data = {       
        'x':       [   1,        2,      3,      4,      5,        6,       7,      8,      9,     10,     11,    12,      13,    14,      15,    16,     17],
        'CR':      [2284,     2285,   2286,   2287,   2288,     2289,    2290,   2291,   2292,   2293,   2294,   2295,   2296,  2297,    2298,  2299,   2300],
        'HMI':     [-0.016,	-0.344,	-0.262,	-0.063,	  0.05,	  np.nan,   0.009, np.nan, -0.013,	0.336,	 0.42, np.nan,	0.414,	0.083, -0.141, 0.134, -0.071],
        'HMI_err': [0.001,   0.007,	 0.007,  0.006,  0.002,	  np.nan,   0.001, np.nan,  0.007,  0.007,	0.005, np.nan,  0.007,	0.001,	0.002, 0.007,  0.001],
        'PHI':     [0.1,    -0.076, -0.405,  0.058,  0.295,   np.nan,   0.081, np.nan, -0.085,  0.462,  0.868, np.nan, -0.035,  0.325,   0.39, 0.461,  0.323],
        'PHI_err': [0.003,   0.002,  0.002,  0.002,  0.003,   np.nan,   0.008, np.nan,  0.009,  0.008,  0.007, np.nan,  0.002,  0.004,  0.003, 0.003,  0.005]
    }
    df = pd.DataFrame(data)



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
    print(params1[3])
    # --- Plot ---
    plt.figure(figsize=(7, 5))
    plt.errorbar(df['x'], df['HMI'], yerr=df['HMI_err'], color='tab:blue', fmt='o', capsize=5, label='HMI')
    #plt.plot(df['x'], fit_line1, linestyle='--', color='tab:blue', label=f'Linear fit HMI: y={slope1:.2f}x+{intercept1:.2f}')
    #plt.plot(df['x'], cosine(df['x'], *params1), color='tab:blue', linestyle='--', label=f'y_HMI = A × cos(2π f x + φ) + {params1[3]:.3f}G')#f'Cosine Fit {params1[0]:.2f}  cos(2π {params1[1]:.2f} x + {params1[2]:.2f}) + {params1[3]:.2f}')

    plt.errorbar(df['x'], df['PHI'], yerr=df['PHI_err'], color='tab:orange', fmt='o', capsize=5, label='PHI')
    #plt.plot(df['x'], fit_line2, linestyle='--', color='tab:orange', label=f'Linear fit PHI: y={slope2:.2f}x+{intercept2:.2f}')
    #plt.plot(df['x'], cosine(df['x'], *params2), color='tab:orange', linestyle='--', label=f'y_PHI  = A × cos(2π f x + φ) + {params2[3]:.3f}G')#f'Cosine Fit {params1[0]:.2f}  cos(2π {params1[1]:.2f} x + {params1[2]:.2f}) + {params1[3]:.2f}')

    # --- Labels and legend ---
    plt.xlabel('CR')
    plt.ylabel('Average Magnetic Flux [Mx/cm²]')
    plt.xlim(0, 18)
    plt.ylim(-1.5, 1.5)
    plt.xticks(ticks=df['x'], labels=df['CR'], rotation=45) 
    plt.title('Average HMI & PHI Flux')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig('flux_statistics_nofit.png', format='png', dpi=300)

    plt.show()

if __name__ == "__main__":

    #flux_statistics()
    
    start_cr = 2297
    end_cr   = 2297
    run_pfss = False
    run_diagnostics = True
    #base = Path('/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/output/release_2025_v01/l3/syn/')
    base = Path('/scratch/slam/loeschl/dev/python/synoptic-map-pipeline/output/PHI_only/')

    paths = sorted(base.glob("CR*/synop/"))
    paths = [p for p in paths if int(p.parent.name[2:]) >= start_cr and int(p.parent.name[2:]) <= end_cr]

    for path in paths:
        main(path, run_diagnostics=run_diagnostics, run_pfss=run_pfss, fname="synopMr.fits", series="hmi.synoptic_mr_polfil_720s", segment="Mr_polfil")

        try: 
            main(path, run_diagnostics=run_diagnostics, run_pfss=run_pfss, fname="synopMr.fits", series="hmi.synoptic_mr_polfil_720s", segment="Mr_polfil")
        except Exception as e:
            print(f"An error occurred: {e}")
            continue
    

