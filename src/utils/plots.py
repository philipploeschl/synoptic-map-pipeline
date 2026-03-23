import os
import numpy as np
from scipy import optimize
import sunpy.map
import pandas as pd

import matplotlib.pylab as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.gridspec import GridSpec


def plot_synoptic_sources(synop, component, outpath, name, crt_rot, fits_table, save=True):

    (ny, nx) = synop.shape

    labelsize = 12
    ticksize  = 10
    titlesize = 14
    suptitlesize=16
    fontsize = labelsize
    bar_height = ny//36

    ytick_latitude = []
    ytick_normalize = []
    for i in range(19):
        calculation = np.sin((np.pi/18)*(i-9.0))
        ytick_latitude.append(calculation)
        ytick_normalize.append((calculation+1)*(ny/2))

    # MAKE PLOT #1
    fig, ax = plt.subplots(figsize=(14,6))
    ax.tick_params(labelsize=14)
    
    im = ax.imshow(synop,cmap="hmimag",vmin=-1500,vmax=1500,origin='lower', aspect='auto' , interpolation=None)
    ax.set_title(f'PHI/HMI ${component}$ Synoptic Chart for Carrington Rotation {crt_rot}', y=1.015, fontsize=suptitlesize)
    ax.tick_params(axis='both', which='both', labelbottom=True, labeltop=False, labelleft=True, labelright=True)

    # label the x-axis 
    xlabels    = [0,30,60,90,120,150,180,210,240,270,300,330,360]
    xlocations = np.arange(0, nx+1, nx//12)
    ax.set_xlim(0, 360)
    ax.set_xticks(xlocations)
    ax.set_xticklabels(xlabels)
    ax.set_xlabel('Carrington Longitude [°]', fontsize=labelsize)

    # Create the latitude labels on the right-hand side of the plot
    ylabels_r = [' ','-80',' ','-60',' ','-40',' ','-20',' ','0',' ',' 20',' ',' 40',' ',' 60',' ',' 80',' ']
    ylocations_r = ytick_normalize
    ax.set_ylim(-bar_height, ny)
    ax.set_yticks(ylocations_r)
    ax.set_yticklabels(ylabels_r)
    ax.set_ylabel('Latitude [°]', fontsize=labelsize)
    ax.yaxis.labelpad=0
    ax.tick_params(labelsize=labelsize, axis='both', which='both', bottom=True, top=True, left=True, right=True, labelbottom=True, labeltop=False, labelleft=True, labelright=False)

    # After `ax.imshow(...)` or similar:
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.25)

    # Add colorbar
    cbar = fig.colorbar(im, cax=cax, orientation='vertical')
    cbar.set_label(label=f'${component}$ [Gauss]', size=labelsize, labelpad=-15)
    
    fig.subplots_adjust(left=0.06, right=0.94, top=0.9, bottom=0.1)

    # make the horizontal bar with color coded data sources
    deg2px = nx/360.  
    for row in fits_table:
        # make the colored boxes for each fits table line
        color = 'steelblue' if row['SRC'] == 'HMI' else 'orange'
        width = row["CRLN_START"] - row["CRLN_END"]

        if width > 0:
            ax.barh(-bar_height/2, width*deg2px, left=row["CRLN_END"]*deg2px, height=bar_height, color=color)
        else:
            # interval wraps around 0°
            ax.barh(-bar_height/2, (360-row["CRLN_END"])*deg2px, left=row["CRLN_END"]*deg2px, height=bar_height, color=color)
            ax.barh(-bar_height/2, row["CRLN_START"]*deg2px, left=0, height=bar_height, color=color)

        # add vertical black lines as boundaries
        ax.vlines(row["CRLN_END"]*deg2px, -bar_height, 0, color='black', linewidth=0.7)
    
    ax.hlines(y=0, xmin=0, xmax=360*deg2px, color='black',linewidth=0.7)

    phi_patch = mpatches.Patch(color='orange', label='PHI')
    hmi_patch = mpatches.Patch(color='steelblue', label='HMI')
    boundary_line = mlines.Line2D([], [], color='black', linewidth=0.7, label='Boundary')

    ax.legend(handles=[phi_patch, hmi_patch, boundary_line],loc='upper center',bbox_to_anchor=(0.12, -0.045), ncol=3, frameon=False)
    
    if save:
        plt.savefig(os.path.join(outpath, f'{name}.pdf'), format='pdf')
        plt.savefig(os.path.join(outpath, f'{name}.png'), format='png')
    else:
        plt.show()
    

def plot_synoptic_with_stripe_magnitudes(synop, outpath, name, config, fits_table, pdf=True):

    (ny, nx) = synop.shape

    labelsize = 12
    ticksize  = 10
    titlesize = 14
    suptitlesize=16
    fontsize = labelsize
    bar_height = 40

    ytick_magnitude = []
    ytick_normalize = []
    for i in range(21):
        ytick_magnitude.append(i*144 + 720)
        ytick_normalize.append((i)*72.)


    # make the plot
    fig, ax = plt.subplots(figsize=(14,6))
    fig.subplots_adjust(left=0,right=1,top=1,bottom=0)
    ax.tick_params(labelsize=14)
    im = ax.imshow(synop,cmap="hmimag",vmin=-1500,vmax=1500,origin='lower',extent=[0,nx,bar_height,ny+bar_height] , interpolation=None)
    ax.set_title(f'PHI/HMI B {config.Btype} Synoptic Chart for Carrington Rotation {config.cr}', y=1.015, fontsize=suptitlesize)
    ax.tick_params(axis='both', which='both', labelbottom=True, labeltop=False, labelleft=True, labelright=True)

    # label the x-axis 
    xlabels    = [0,30,60,90,120,150,180,210,240,270,300,330,360]
    xlocations = np.arange(0, nx+1, nx//12) #[0,300,600,900,1200,1500,1800,2100,2400,2700,3000,3300,3600]
    ax.set_xticks(xlocations)
    ax.set_xticklabels(xlabels)
    ax.set_xlabel('Carrington Longitude [°]', fontsize=labelsize)

    # Create the latitude labels on the right-hand side of the plot
    ylabels_r = ['-10', ' ','-8',' ','-6',' ','-4',' ','-2',' ','0',' ',' 2',' ',' 4',' ',' 6',' ',' 8',' ', '10']
    ylocations_r = [y + bar_height for y in ytick_normalize]
    ax.set_ylim(0, ny + bar_height)
    ax.set_yticks(ylocations_r)
    ax.set_yticklabels(ylabels_r)
    ax.set_ylabel('Stripe Magnitude [G]', fontsize=labelsize)
    ax.yaxis.labelpad=0
    ax.tick_params(labelsize=labelsize, axis='both', which='both', bottom=True, top=True, left=True, right=True, labelbottom=True, labeltop=False, labelleft=True, labelright=False)

    # After `ax.imshow(...)` or similar:
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.25)

    # Add colorbar
    if config.Mr:
        cbar = fig.colorbar(im, cax=cax, orientation='vertical')
        cbar.set_label(label='$B_r$ [Gauss]', size=labelsize, labelpad=-15)
    else:
        cbar = fig.colorbar(im, cax=cax, orientation='vertical')
        cbar.set_label(label='$B_{LoS}$ [Gauss]', size=labelsize, labelpad=-15)
    
    fig.subplots_adjust(left=0.06, right=0.94, top=1., bottom=0.025)

    # make the horizontal bar with color coded data sources
    deg2px = nx/360.  
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
    

    import matplotlib.patches as patches
    # Compute mean for each column along y
    column_means = np.nanmean(synop[1300+bar_height:1375+bar_height, :], axis=0)


    # The x-axis is shared, so you need matching coordinate scales
    x = np.arange(column_means.size)

    # Create a twin axis on top for the line plot    
    #ax2 = ax.twinx()
    #ax2.set_position(ax.get_position())
    #ax2.set_ylim(-10, 10)        # actual data units of column_means
    ax.plot(x, 72*column_means+720+bar_height)
    #ax2.set_xlabel("Column mean")

    #ax2.set_ylabel("Mean Stripe Magnitude [G]", fontsize=labelsize)
    # Add this *after* imshow and before plt.show()
    rect = patches.Rectangle(
        (8, 1300+bar_height),          # bottom-left corner (x=0, y=0)
        3590,            # width
        75,             # height
        linewidth=4,
        edgecolor='tab:red',
        facecolor='none',
        alpha=1         # adjust transparency
    )

    ax.add_patch(rect)


    plt.tight_layout()

    if pdf:
        plt.savefig(os.path.join(outpath, f'{name}.png'), format='png')
        plt.savefig(os.path.join(outpath, f'{name}.pdf'), format='pdf')
    else:
        plt.show()
    


    return fig

def plot_synoptic(synop, outpath, name, src, config, pdf=True):

    (ny, nx) = synop.shape

    labelsize = 12
    ticksize  = 10
    titlesize = 14
    suptitlesize=16
    fontsize = labelsize

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
    im = plt.imshow(synop,cmap="hmimag",vmin=-1500,vmax=1500,origin='lower',extent=[0,nx,0,ny])
    ax.set_title(f'{src} B {config.Btype} Synoptic Chart for Carrington Rotation {config.cr}', y=1.015, fontsize=suptitlesize)
    ax.tick_params(axis='both', which='both', labelbottom=True, labeltop=False, labelleft=True, labelright=True)

    # label the x-axis 
    xlabels    = [0,30,60,90,120,150,180,210,240,270,300,330,360]
    xlocations = np.arange(0, nx+1, nx//12)
    ax.set_xticks(xlocations)
    ax.set_xticklabels(xlabels)
    ax.set_xlabel('Carrington Longitude [°]', fontsize=labelsize)

    # Create the latitude labels on the right-hand side of the plot
    ylabels_r = [' ','-80',' ','-60',' ','-40',' ','-20',' ','0',' ',' 20',' ',' 40',' ',' 60',' ',' 80',' ']
    ylocations_r = ytick_normalize
    ax.set_yticks(ylocations_r)
    ax.set_yticklabels(ylabels_r)
    ax.set_ylabel('Latitude [°]', fontsize=labelsize)
    ax.yaxis.labelpad=0
    ax.tick_params(labelsize=labelsize, axis='both', which='both', bottom=True, top=True, left=True, right=True, labelbottom=True, labeltop=False, labelleft=True, labelright=False)

    # After `ax.imshow(...)` or similar:
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.25)

    # Add colorbar
    if config.Mr:
        cbar = fig.colorbar(im, cax=cax, orientation='vertical')
        cbar.set_label(label='$B_r$ [Gauss]', size=labelsize, labelpad=-15)
    else:
        cbar = fig.colorbar(im, cax=cax, orientation='vertical')
        cbar.set_label(label='$B_{LoS}$ [Gauss]', size=labelsize, labelpad=-15)
    
    fig.subplots_adjust(left=0.06, right=0.94, top=1., bottom=0.025)
    
    if pdf:
        plt.savefig(os.path.join(outpath, f'{name}.pdf'), format='pdf')
        plt.savefig(os.path.join(outpath, f'{name}.png'), format='png')
    else:
        plt.show()



########################
####### ANALYSIS #######
########################

def combined_synoptic_noise_plot(data, fits_table, pos, noise, offset, legend, config, save=False):
    """
    Two-panel plot:
    Top: Synoptic map
    Bottom: Noise scatter
    PHI/HMI horizontal bars perfectly aligned between plots
    Colorbar only for top plot
    Legend in the empty bottom-right axis
    """

    (ny, nx) = data.shape

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
    deg2px = nx/360.
    bar_height = 40
    noise_bar_height = 0.15

    # -------------------------
    # (1) Synoptic Map
    # -------------------------
    im = ax_synop.imshow(
        data, cmap="hmimag", vmin=-1500, vmax=1500,
        origin="lower", extent=[0, nx, bar_height, ny + bar_height],
        interpolation=None
    )

    ax_synop.set_title(
        f'PHI/HMI B {config.Btype} Synoptic Chart for Carrington Rotation {config.cr}',
        y=1.02, fontsize=24
    )

    # Add x-label on top plot
    #ax_synop.set_xlabel("Carrington Longitude [°]", fontsize=labelsize)

    # Longitude ticks
    xlabels = [0,30,60,90,120,150,180,210,240,270,300,330,360]
    xlocations = [i * deg2px for i in xlabels]
    ax_synop.set_xticks(xlocations)
    ax_synop.set_xticklabels(xlabels)
    ax_synop.set_ylabel('Latitude [°]', fontsize=labelsize)
    ax_synop.tick_params(labelsize=labelsize)

    # Latitude ticks
    ylabels_r = [' ','-80',' ','-60',' ','-40',' ','-20',' ','0',' ','20',' ','40',' ','60',' ','80',' ']
    ytick_latitude = [np.sin((np.pi/18)*(i-9.0)) for i in range(19)]
    ytick_normalize = [(y+1)*(ny/2) + bar_height for y in ytick_latitude]
    ax_synop.set_yticks(ytick_normalize)
    ax_synop.set_yticklabels(ylabels_r)
    ax_synop.set_ylim(0, ny+bar_height)

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

    colors = ["#0072B2", "#000000", "#D55E00"]
    for xx, yy, ll, cc in zip(pos, noise, legend, colors):
        ax_noise.scatter(xx, yy, s=7.5, label=ll, color=cc)

    for xx, yy, ll, cc in zip(pos, offset, legend, colors):
        ax_noise.scatter(xx, yy, s=7.5, label=ll, color=cc, marker='x')

    ax_noise.set_xlim(0, nx)
    ylim_noise = np.ceil(np.nanmax(noise)+1)
    #ylim_noise = 7

    ax_noise.set_ylim(-noise_bar_height, ylim_noise)
    ax_noise.set_xlabel("Carrington Longitude [°]", fontsize=labelsize)
    ax_noise.set_ylabel("Noise σ [G]", fontsize=labelsize)
    ax_noise.tick_params(labelsize=labelsize)
    ax_noise.set_xticks(xlocations)
    ax_noise.set_xticklabels(xlabels)
    
    handles, labels = ax_noise.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    legend_scatter = ax_noise.legend(
        by_label.values(), by_label.keys(),
        loc='upper left',
        bbox_to_anchor=(1, 1),
        title="Latitude windows:",
        fontsize=labelsize - 2,
        frameon=False
    )
    ax_noise.add_artist(legend_scatter)  # Keep this legend when adding the next one


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
    #fig.tight_layout()
    if save:
        #os.makedirs(outpath, exist_ok=True)
        #fig.savefig(os.path.join(outpath, f'{name}.pdf'), format='pdf')
        #pdf.savefig(fig)
        return fig 
    else:
        plt.show()

    plt.close()




def magnetic_flux_plot_latitudes(flux_phi, flux_hmi, thld_low, thld_high, ny, latwidth=10, save=False):

    labelsize = 18
    titlesize = 24

    fig, ax = plt.subplots(figsize=(14, 10.5))

    line1 = ax.plot(flux_hmi['pos'].values+flux_hmi['neg'].values, linestyle='dashed',  linewidth=2, label='HMI')
    line2 = ax.plot(flux_phi['pos'].values+flux_phi['neg'].values, linestyle='dashdot', linewidth=2, label='PHI')

    xticks = np.linspace(0, ny/latwidth, 19)-0.5
    xlabels = np.linspace(-90,90, 19, dtype=int)

    plt.axhline(y=0, color='grey', linestyle=(0,(5,10)), alpha=0.75)

    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabels)

    ax.set_xlabel('Latitude [°]', fontsize=labelsize)
    ax.set_ylabel('Magnetic Flux [mx/cm²]', fontsize=labelsize)
    ax.set_title(f'Average weak magnetic flux balance for ({thld_low}-{thld_high}G)', fontsize=titlesize)
    
    lim = np.nanmax([np.nanmax(np.abs(flux_phi["pos"]+flux_phi["neg"])), 
                     np.nanmax(np.abs(flux_hmi["pos"]+flux_hmi["neg"])), 
                   ])
    
    lim = np.ceil(lim)+2
    ax.set_ylim([-lim, lim])

    ax.tick_params(labelsize=labelsize)

    plt.legend(loc='lower right', ncol=2, fontsize=labelsize)

    hmi_avg = np.round(np.nanmean(flux_hmi['pos'].values+flux_hmi['neg'].values), 3)
    hmi_std = np.round(np.nanstd (flux_hmi['pos'].values+flux_hmi['neg'].values), 3)          
    hmi_rms = np.round(np.nanstd (flux_hmi['pos'].values+flux_hmi['neg'].values)/len(flux_hmi['pos']), 3)          
    
    phi_avg = np.round(np.nanmean(flux_phi['pos'].values+flux_phi['neg'].values), 3)
    phi_std = np.round(np.nanstd (flux_phi['pos'].values+flux_phi['neg'].values), 3)          
    phi_rms = np.round(np.nanstd (flux_phi['pos'].values+flux_phi['neg'].values)/len(flux_phi['pos']), 3)          
    
    plt.annotate(
        f"Average signal\n",
        xy=(1, 1),
        xycoords='axes fraction',   # relative to axes (1.0 = right/top)
        textcoords='offset points',
        xytext=(-10, -10),
        ha='right',
        va='top',
        fontsize=labelsize,
        fontweight='bold'
    )
    
    plt.annotate(
        f"HMI: {hmi_avg} $\pm$ {hmi_std} G\n",
        xy=(1, 1),
        xycoords='axes fraction',   # relative to axes (1.0 = right/top)
        textcoords='offset points',
        xytext=(-10, -35),
        ha='right',
        va='top',
        fontsize=labelsize,
        color=line1[0].get_color()
    )


    plt.annotate(
        f"PHI: {phi_avg} $\pm$ {phi_std} G",
        xy=(1, 1),
        xycoords='axes fraction',   # relative to axes (1.0 = right/top)
        textcoords='offset points',
        xytext=(-10, -60),
        ha='right',
        va='top',
        fontsize=labelsize,
        color=line2[0].get_color()
    )

    #plt.tight_layout()
    if save:
        #pdf.savefig(fig)
        #plt.savefig("flux_correction.pdf", format="pdf", dpi=300)
        return fig
    else:
        plt.show()

    plt.close()



"""
def flux_plot(hmiMr_polfil, synopMr05_v00, thld, save=False):
    
    labels = ['Full Map\n0-360°', 'PHI 1\n0-40°', 'PHI 2\n200-360°']
    
    hmi_pos , hmi_neg  = magnetic_flux(hmiMr_polfil.data         , thld=thld)
    hmi_pos1, hmi_neg1 = magnetic_flux(hmiMr_polfil.data[:,0:400], thld=thld)
    hmi_pos2, hmi_neg2 = magnetic_flux(hmiMr_polfil.data[:,2000:], thld=thld)

    phi_pos , phi_neg  = magnetic_flux(synopMr05_v00.data         , thld=thld)
    phi_pos1, phi_neg1 = magnetic_flux(synopMr05_v00.data[:,0:400], thld=thld)
    phi_pos2, phi_neg2 = magnetic_flux(synopMr05_v00.data[:,2000:], thld=thld)

    phi_flux_pos = [phi_pos, phi_pos1, phi_pos2]
    phi_flux_neg = [abs(phi_neg), abs(phi_neg1), abs(phi_neg2)]

    hmi_flux_pos = [hmi_pos, hmi_pos1, hmi_pos2]
    hmi_flux_neg = [abs(hmi_neg), abs(hmi_neg1), abs(hmi_neg2)]

    x = np.arange(len(labels))  # the label locations
    width = 0.3  # the width of the bars

    fig, ax = plt.subplots(figsize=(7,5))
    rects1 = ax.bar(x - width  , phi_flux_pos, width/2, label='PHI+')
    rects2 = ax.bar(x - width/2, phi_flux_neg, width/2, label='PHI-')
    rects3 = ax.bar(x + width/2, hmi_flux_pos, width/2, label='HMI+')
    rects4 = ax.bar(x + width  , hmi_flux_neg, width/2, label='HMI-')

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel('B Flux [mx/cm²]')
    ax.set_title('CR2240 Magnetic Flux by Region')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()

    #ax.bar_label(rects1, padding=3)
    #ax.bar_label(rects2, padding=3)
    
    ylim = ax.get_ylim()[1]
    exp = np.floor(np.log10(ylim))
    ylim_new = np.round(ylim/10**exp, 1)*10**exp
    plt.vlines([0.5,1.5], 0, ylim_new, colors='k', linestyles='solid')#, label='', data=None)

    fig.tight_layout()

    
    print("PHI+: %d, PHI-: %d | PHI1+: %d, PHI1-: %d | PHI2+: %d, PHI2-: %d"%(phi_pos, phi_neg, phi_pos1, phi_neg1, phi_pos2, phi_neg2))
    print("HMI+: %d, HMI-: %d | HMI1+: %d, HMI1-: %d | HMI2+: %d, HMI2-: %d"%(hmi_pos, hmi_neg, hmi_pos1, hmi_neg1, hmi_pos2, hmi_neg2))
    
    print("HMI+/PHI+: %.2f, HMI-/PHI-: %.2f | HMI1+/PHI1+: %.2f, HMI1-/PHI1-: %.2f | HMI2+/PHI2+: %.2f, HMI2-/PHI2-: %.2f" %(hmi_pos/phi_pos, hmi_neg/phi_neg, hmi_pos1/phi_pos1, hmi_neg1/phi_neg1, hmi_pos2/phi_pos2, hmi_neg2/phi_neg2))
      
    if save:
        plt.savefig('flux_balance.pdf', format='pdf', dpi=300)



def plot_pfss_openfield(fieldmap, pfss_out, field_lines, title="PHI/HMI"):
    import matplotlib.colors as mcolor

    fig = plt.figure(figsize=(8,11.25))

    ss_br = pfss_out.source_surface_br
    ax1 = fig.add_subplot(3, 1, 1, projection=ss_br)

    # Plot the source surface map
    im1 = ss_br.plot()
    # Plot the polarity inversion line
    ax1.plot_coord(pfss_out.source_surface_pils[0])
    ax1.set_title('%s Source surface magnetic field'%title)
    plt.colorbar()

    m = fieldmap#phi_v02_pfss_in.map

    ax2 = fig.add_subplot(3, 1, 2)
    cmap = mcolor.ListedColormap(['tab:red', 'black', 'tab:blue'])
    norm = mcolor.BoundaryNorm([-1.5, -0.5, 0.5, 1.5], ncolors=3)
    pols = field_lines.polarities.reshape(2 * nsteps + 1, nsteps + 1).T
    ax2.contourf(np.rad2deg(lon_1d), np.sin(lat_1d), pols, norm=norm, cmap=cmap)
    ax2.set_ylabel('sin(latitude)')

    ax2.set_title('%s Open (blue/red) and closed (black) field'%title)
    ax2.set_aspect(0.5 * 360 / 2)
    plt.colorbar()


    ax3 = fig.add_subplot(3, 1, 3, projection=m)
    m.plot(cmap='hmimag')
    ax3.contourf(np.rad2deg(lon_1d)*2, np.sin(lat_1d)*180+180, pols, norm=norm, cmap=cmap, alpha=0.25)
    ax3.plot_coord(pfss_out.source_surface_pils[0])
    ax3.set_title('Input %s magnetogram w/ PFSS & Open Field' %title)
    plt.colorbar()
    plt.tight_layout()
    
    return fig

"""