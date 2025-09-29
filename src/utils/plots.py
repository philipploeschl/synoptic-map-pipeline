import os
import numpy as np
import matplotlib.pylab as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import sunpy.map



def plot_synoptic(synop, outpath, name, config, pdf=True):

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
    im = plt.imshow(synop,cmap="hmimag",vmin=-1500,vmax=1500,origin='lower',extent=[0,3600,0,1440])
    ax.set_title(f'PHI/HMI B {config.Btype} Synoptic Chart for Carrington Rotation {config.cr}', y=1.015, fontsize=suptitlesize, interpolation=False)
    ax.tick_params(axis='both', which='both', labelbottom=True, labeltop=False, labelleft=True, labelright=True)

    # label the x-axis 
    xlabels    = [0,30,60,90,120,150,180,210,240,270,300,330,360]
    xlocations = [0,300,600,900,1200,1500,1800,2100,2400,2700,3000,3300,3600]
    ax.set_xticks(xlocations)
    ax.set_xticklabels(xlabels)
    ax.set_xlabel('Carrington Longitude [°]', fontsize=labelsize)

    # Create the latitude labels on the right-hand side of the plot
    ylabels_r = [' ','-80',' ','-60',' ','-40',' ','-20',' ','0',' ',' 20',' ',' 40',' ',' 60',' ',' 80',' ']
    ylocations_r = ytick_normalize
    ax.set_yticks(ylocations_r)
    ax.set_yticklabels(ylabels_r)
    ax.set_ylabel('Sine Latitude [°]', fontsize=labelsize)
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
    else:
        plt.show()

