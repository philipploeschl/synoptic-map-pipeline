# Comments
# - len[2] array had to be renamed to length due to pyhton len() function
# - MIN() / MAX() in the C implementation are supposed to return integers but rounding errors are introduced if I treat them as integers in python. 
#   Prevailing rounding mode might be different on DRMS server. Python implementation uses float returns on min/max operations instead.
# - comparing the python with the C output produces a column with residual signal in column 2509 at the end of inRec 3. 
#   This is most likely a rounding issue as the mrc value is xxxx.52 and rounded up in python. This problem is fixed if the mrc is rounded down for inRec 3. 
#   This fix introduces residual signal in col 2399 at the same time, as the columns wrongly missing when processed for the other nsynop part. 
#   Overall this will produce a slightly different synoptic map than the C code but shouldn't matter in the long run.

import numpy as np
import scipy as sp
import subprocess
from utils.solephem import solephem
import datetime as datetime
from copy import copy
from astropy.io import fits
import os, sys
from datetime import date

from utils.plots import plot_synoptic_sources
from utils.utils import create_src_fits_table


# DEFINES
QUAL_CHECK = "0xfffefb00"

C1  =  0.0757644       ##/* days/degree at 27.27527 */
C2  = 92353.9357       ##/* day of 1853:11:09_22h:27m:24s */
PI  = 3.14159265358979323844
SID = 86400.0
RADSINDEG = PI / 180
SHRT_MAX = 32767
SHRT_MIN = -SHRT_MAX -1
DRMS_MISSING_FLOAT = np.nan    
kNOISE_EQ = 10.0 # redefined in CalcSynopCol but unused

STATUS_OK = 0
STATUS_ERROR = 1

# DRMS Interface
def get_drms_parameters_hmi(inRecs, input_ds):

    formatted = [] 
    drms_param = []
    nRecs = 0

    if input_ds == "": return drms_param, nRecs
    if inRecs is None or len(inRecs) < 23: return drms_param, nRecs
    #inRecs = "2014.05.12_12:00:00_TAI, 2014.05.13_00:00:00_TAI, 2014.05.13_12:00:00_TAI, 2014.05.14_00:00:00_TAI" # input argument
 
    #nRecs = len(inRecs.split(','))
    #show_info = 'show_info %s["%s"] key="CALVER64,T_REC,QUALITY,FDRADIAL,CARSTRCH,DIFROT_A,DIFROT_B,DIFROT_C,CRVAL1,CRLN_OBS,CAR_ROT,MAPLGMAX,MAPLGMIN,MAPMMAX,I_DREC" -iPA'
    show_info = 'show_info %s["%s"] key="CALVER64,T_REC,QUALITY,FDRADIAL,CARSTRCH,DIFROT_A,DIFROT_B,DIFROT_C,CRVAL1,CRLN_OBS,CAR_ROT,MAPLGMAX,MAPLGMIN,MAPMMAX,I_DREC,INSTRUME" -iPA' 
    
    #-P for path and -A for segment
    
    si_out = subprocess.check_output(show_info %(input_ds, inRecs) , shell=True)[:-1].decode("utf-8")
    raw = si_out.split('\n')
    
    keys = raw[0].split('\t')
    
    for line in raw[1:]:  
        formatted = line.split('\t') # [CALVER64, T_REC, QUALITY, FDRADIAL, CARSTRCH, DIFROT_A, DIFROT_B, DIFROT_C, CRVAL1, CRLN_OBS, CAR_ROT, MAPLGMAX, MAPLGMIN, I_DREC]
        
        dict_tmp = {}

        for i, key in enumerate(keys):
            
            if formatted[i].strip() == "InvalidKeyname":
                dict_tmp[key] = 0
            else:
                dict_tmp[key] = formatted[i]
        dict_tmp["FILENAME"] = ''

        drms_param.append(dict_tmp)
        nRecs += 1

    return drms_param, nRecs

def get_drms_parameters_phi(inRecs, input_ds, input_ds_origin):

    formatted_remap = [] 
    formatted_base = [] 
    drms_param = []
    nRecs = 0

    if input_ds == "": return drms_param, nRecs
    if inRecs is None or len(inRecs) < 23: return drms_param, nRecs
    #inRecs = "2014.05.12_12:00:00_TAI, 2014.05.13_00:00:00_TAI, 2014.05.13_12:00:00_TAI, 2014.05.14_00:00:00_TAI" # input argument
    
    #nRecs = len(inRecs.split(','))
    #show_info = 'show_info %s["%s"] key="CALVER64,T_REC,QUALITY,FDRADIAL,CARSTRCH,DIFROT_A,DIFROT_B,DIFROT_C,CRVAL1,CRLN_OBS,CAR_ROT,MAPLGMAX,MAPLGMIN,MAPMMAX,I_DREC" -iPA'
    show_info_remap = 'show_info %s["%s"] key="CALVER64,T_REC,QUALITY,FDRADIAL,CARSTRCH,DIFROT_A,DIFROT_B,DIFROT_C,CRVAL1,CRLN_OBS,CAR_ROT,MAPLGMAX,MAPLGMIN,MAPMMAX,I_DREC,INSTRUME" -iPA' 
    show_info_base  = 'show_info %s["%s"] key="FILENAME" -iPA' 

    #-P for path and -A for segment
    
    si_out_remap = subprocess.check_output(show_info_remap %(input_ds, inRecs) , shell=True)[:-1].decode("utf-8")
    raw_remap = si_out_remap.split('\n')
    keys_remap = raw_remap[0].split('\t')

    si_out_base = subprocess.check_output(show_info_base %(input_ds_origin, inRecs) , shell=True)[:-1].decode("utf-8")
    raw_base = si_out_base.split('\n')
    keys_base = raw_base[0].split('\t')
    
    for (line_remap, line_base) in (zip(raw_remap[1:],raw_base[1:])):  
        formatted_remap = line_remap.split('\t') # [CALVER64, T_REC, QUALITY, FDRADIAL, CARSTRCH, DIFROT_A, DIFROT_B, DIFROT_C, CRVAL1, CRLN_OBS, CAR_ROT, MAPLGMAX, MAPLGMIN, I_DREC, INSTRUME]
        formatted_base = line_base.split('\t') # FILENAME
        
        dict_tmp = {}

        for i, key in enumerate(keys_remap):
            
            if formatted_remap[i].strip() == "InvalidKeyname":
                dict_tmp[key] = 0
            else:
                dict_tmp[key] = formatted_remap[i]
        for i, key in enumerate(keys_base):
            
            if formatted_base[i].strip() == "InvalidKeyname":
                dict_tmp[key] = 0
            else:
                dict_tmp[key] = formatted_base[i]
        drms_param.append(dict_tmp)
        nRecs += 1

    return drms_param, nRecs


def update_common_carrot(drms_getkey):
    
    carrots = []
    for inRec in drms_getkey:
        carrots.append(float(inRec['CAR_ROT']))

    if not carrots:
        raise ValueError("Error: No inRecs found!")

    most_common = max(carrots, key=carrots.count)
    print(f"Most common CAR_ROT: {most_common}, {carrots.count(most_common)} out of {len(carrots)} records")
    
    for inRec in drms_getkey:
        inRec["CAR_ROT"] = most_common
    
    return drms_getkey, most_common

# Misc functions

def CarringtonTime(crot, L):

    #double eph[30];
    #double CT, clong = 0.0;
    #double err, CTp50m, CTm50m;
    #TIME t;
    #char *stime;
    #char tstr[64];
    
    eph = np.zeros(30)
    #CT = 0.0
    #T1853 = 0.0
    #delta_T = 0.0
    #T1853 = sscan_time("1853.11.09_22:27:24_UTC");

    #delta_T = sscan_time("1977.01.01_00:00:00_TAI") - sscan_time("1601.01.01_00:00:00_UT");

    CT = 360.0 * crot - L
    t = (C2 + CT * C1) * SID

    #t = T1853 + CT * C1 * SID;
    solephem(t, eph)

    #print(eph[8])
    err = CT - eph[8]
    solephem(t + 6 * 3600.0, eph)
    CTp50m = eph[8]
    solephem(t - 6 * 3600.0, eph)
    CTm50m = eph[8]
    
    #interpolate to correct t
    t += 12 * 3600 * (err / (CTp50m - CTm50m))
    solephem(t, eph)
    err = CT - eph[8]
    solephem(t + 300.0, eph)
    CTp50m = eph[8]
    solephem(t - 300.0, eph)
    CTm50m = eph[8]
    
    #interpolate tao correct t
    t += 600 * (err / (CTp50m - CTm50m))

    return t

def rint(val):
    return int(round(val,0))


def sscan_time(tstring):
   # http:#//jsoc.stanford.edu/man/man3/sscan_time.html
    """
    sscan_time reads from a character string representing a calendar  date
    / clock time in a standard format, returning a double-precision float-
    ing point number representing the elapsed time in SI  seconds  between
    the  represented  time  and  an arbitrary epoch.
    """
    #delta_T = sscan_time("1977.01.01_00:00:00_TAI") - sscan_time("1601.01.01_00:00:00_UT");
    # Difference between DRMS_EPOCH_S (1977.01.01_00:00:00_TAI) and WSO_EPOCH_S (1601.01.01_00:00:00_UT)
    # CarringtonTime converts time and Carrington coordinates based on Phil's code ctimes.c
    # (/home/wso/src/misc/ctimes.c) which is based on WSO obs. Thus this time difference needs to
    # be corrected to consist with DRMS time.

    try: 
        t = datetime.datetime.strptime(tstring, "%Y.%m.%d_%H:%M:%S_UT")
    except:
        t = datetime.datetime.strptime(tstring, "%Y.%m.%d_%H:%M:%S_TAI")
        
    dt = (t-datetime.datetime(1970,1,1)).total_seconds()
    
    return dt 

def init_MagCol(length):
    
    mMagCol = {}
    
    mMagCol["dist"]     = None
    mMagCol["datacolBr"] = np.zeros(length[1]) # (float *)malloc(sizeof(float) * length[1])
    mMagCol["datacolBt"] = np.zeros(length[1]) # (float *)malloc(sizeof(float) * length[1])
    mMagCol["datacolBp"] = np.zeros(length[1]) # (float *)malloc(sizeof(float) * length[1])
    mMagCol["equivPts"] = None
    mMagCol["ds"]       = None 
    mMagCol["col"]      = None 
    mMagCol["valid"]    = None 
    mMagCol["wt"]       = None
    
    return mMagCol

def init_sortedMagCol(length):
    
    sortedMagCol = {}

    for i in range(0,length):
        sortedMagCol[i] = [] # initialise empty lists for each dictionary entry
    
    return sortedMagCol


def drms_ismissing_float(val):
    
    if np.isnan(val):
        return 1
    else:
        return 0

# Adaptive weight function calculation
def adaptive_weight_functions(drms_getkey, synstep, mrd_cont, nimg=5, lim=False, nlim=25): #exp=5):
    # default: exp=2.5
    # mrd_cont = meridian contribution

    time     = np.array([])
    deltas   = np.array([])
    cadences = np.array([])  # cadence to the left!
    widths   = np.array([]).astype(int) # total widths of each slice 
    mids     = np.array([]).astype(int)  # mid column to place weight function (works with asymmetric cadences)
    weights  = np.array([])

    multi = nimg     # total width of magnetogram slices, must be UNEVEN
    delta_min = 4  # hours for HMI averaging
    delta_max = 80 # hours: about 45° halfWidth. only used with data gaps
    
    nrows = len(mrd_cont)
    pph = (2.2/4)/synstep # pix per hour approximated from HMI cadence

    # convert time strings into datetime objects
    for key in drms_getkey:
        time = np.append(time, datetime.datetime.strptime(key['T_REC'], "%Y.%m.%d_%H:%M:%S_TAI"))

    # find the local cadence by building a timedelta to the next time object
    deltas = (time[1:] - time[:-1])

    # set beginning boundary condition cadence
    delta1 = deltas[0].days*24+deltas[0].seconds/3600
    
    delta1, delta2 = minimumDelta(delta1, delta1, delta_min)
    delta1, delta2 = maximumDelta(delta1, delta1, delta_max)
    
    cadences = np.array([delta1, delta2])
    #cadences = np.array([deltas[0].days*24+deltas[0].seconds/3600, deltas[0].days*24+deltas[0].seconds/3600])

    # calculate cadence on each side of the record
    for i in range(len(deltas)-1):
        
        #cadences = np.vstack((cadences, [deltas[i].days*24+deltas[i].seconds/3600, deltas[i+1].days*24+deltas[i+1].seconds/3600]))
        delta1 = deltas[i].days*24+deltas[i].seconds/3600
        delta2 = deltas[i+1].days*24+deltas[i+1].seconds/3600

        delta1, delta2 = minimumDelta(delta1, delta2, delta_min)
        delta1, delta2 = maximumDelta(delta1, delta2, delta_max)

        cadences = np.vstack((cadences, [delta1, delta2]))

    # set end boundary condition cadence
    #cadences = np.vstack((cadences, [deltas[-1].days*24+deltas[-1].seconds/3600, deltas[-1].days*24+deltas[-1].seconds/3600]))
    delta1 = deltas[-1].days*24+deltas[-1].seconds/3600
    
    delta1, delta2 = minimumDelta(delta1, delta1, delta_min)
    delta1, delta2 = maximumDelta(delta1, delta1, delta_max)
    
    cadences = np.vstack((cadences, [delta1, delta2]))
    
    for cadence in cadences:
        cad_max = np.max(cadence)
        widths = np.append(widths, np.ceil(multi*cad_max*pph).astype(int)) 
        
        if not widths[-1] % 2: widths[-1] += 1 # make widths uneven to have a central column
        
        mids = np.append(mids, (np.round(cad_max*pph*multi/2)).astype(int)) # floor for array[0] element
    #weights = [np.zeros(int(w)) for w in widths]

    # np.floor to avoid going into the neighbour frame!
    # cadence half width
    chwidth = np.floor(cadences*pph/2).astype(int)
    
    exp_pos = 1-1/(multi-1) # position of the adjacent central meridian
                  # 0.5 for 1 adjacent slice = middle of the wing
                  # 0.25 for 2 adjacent slices           
    exps = calc_exp(exp_pos, mrd_cont) # calculates exponent at 
    
    weights = []
    for w in widths:
        rows = np.zeros([nrows, w])
        weights.append(rows)
    
    # loop over weight of each magnetogram
    for i in range(len(weights)):

        # polynomial version
        # measured from current CM:
        # 1x chwidth reaches image border to the next record 
        # 2x chwidth reaches central meridian of next record
        # 3x chwidth reaches outer border of next record at matching cadence

        # factor 2.0 extends the weights to completely overlap adjacent frames of matching cadence
        # variable cadence might cause the weight function to end somewhere in the in the next
        # slice such that the drop off at the adjacent central meridian is always the same

        # multi = total width as multiple of the cadence
        # multi * 2 = total width in central half widths chwidth
        # (multi-1)*2 = widths in the wings
        # (multi-1) = width of one wing
        
        n1 = np.ceil((multi-1)*chwidth[i][0]).astype(int) # needs to be >1.0 to work without NaNs 
        n2 = np.ceil((multi-1)*chwidth[i][1]).astype(int) # needs to be >1.0 to work without NaNs

        if lim:
            # nlim = 25 # this gives 2*25*0.1 = 5° wide overlap region
            # now set in config.py
            if n1 > nlim: n1 = nlim
            if n2 > nlim: n2 = nlim
        
        for j, exp in enumerate(exps):

            slope1 = np.arange(0, 1, 1/n1)**exp       # **5/2 for < 20% contribution at adjCM
            slope2 = np.arange(0, 1, 1/n2)[::-1]**exp #reverse for decreasing order
            
            weights[i][j][mids[i]-(chwidth[i][0]+n1):mids[i]-(chwidth[i][0])] = slope1
            weights[i][j][mids[i]-chwidth[i][0]:mids[i]+chwidth[i][1]+1] = 1
            weights[i][j][mids[i]+(chwidth[i][1]+1):mids[i]+(chwidth[i][1]+1+n2)] = slope2
        
            #exp_pos = 1-1/(multi-1) # position of the adjacent central meridian
            #                      # 0.5 for 1 adjacent slice = middle of the wing
            #                      # 0.25 for 2 adjacent slices
            #exps = calc_exp(exp_pos, mrd_cont) # calculates exponent at 
            #
            #for exp in exps:
            #    slope1 = np.arange(0, 1, 1/n1)**exp     # **5/2 for < 20% contribution at adjCM
            #    slope2 = np.arange(0, 1, 1/n2)[::-1]**exp #reverse for decreasing order
            #
            #    weights_lat[j][mids[i]-(chwidth[i][0]+n1):mids[i]-(chwidth[i][0])] = slope1
            #    weights_lat[j][mids[i]-chwidth[i][0]:mids[i]+chwidth[i][1]+1] = 1
            #    weights_lat[j][mids[i]+(chwidth[i][1]+1):mids[i]+(chwidth[i][1]+1+n2)] = slope2
            #
            ## reverse weights to account for dates in the synptic map being filled from right to left
            #weights_lat[j] = weights_lat[j][::-1]
            #
            #weights.append(weights_lat)
            weights[i][j] = weights[i][j][::-1] # reverse to account for SM filling from the right

    return weights, cadences

def minimumDelta(d1, d2, minimum):
    
    if d1 < minimum: d1 = minimum
    if d2 < minimum: d2 = minimum
    return d1, d2

def maximumDelta(d1, d2, maximum):
    
    if d1 > maximum: d1 = maximum
    if d2 > maximum: d2 = maximum
    return d1, d2


def calc_weights(n, mrd_cont):
    # n = 2* chwidth
    # mrd_cont = contribution at adjacent meridian
    
    y = []
    width = 3*n+1
    mid = n//2

    slope1 = np.arange(0, 1, 1/n)
    slope2 = slope1[::-1]


    exps = calc_exp(slope1[mid], mrd_cont)

    for exp in exps:
        tmp = np.zeros(width)
        tmp[0:n]     = slope1**exp
        tmp[n:2*n+1] = 1
        tmp[2*n+1:]  = slope2**exp

        y.append(tmp)

    return y, exps

def calc_exp(y,z):
    return np.log(z)/np.log(y)


# Meridian contribution
def adjacent_merdian_contributions(sinbdivs, dmin, dmax, cmin, cmax):
    
    # sinbdivs ... number of sinb divisions
    # dmin ... inner boundary in degrees
    # dmax ... outer boundary in degrees
    # cmin ... minimum contribution in percent
    # cmax ... maximum contribution in percent
    
    mrd_cont = np.zeros(sinbdivs)
    degs = np.degrees(np.arcsin(np.linspace(0,1, sinbdivs)))

    imin = len(degs[degs<dmin])
    imax = len(degs[degs<dmax])
    #print(imin, degs[imin], imax, degs[imax])
    
    nstep = (imax-imin)
    step = (cmax-cmin)/nstep

    for i in range(0, sinbdivs):
        if degs[i] < dmin:
            mrd_cont[i] = cmin
        elif degs[i] > dmax:
            mrd_cont[i] = cmax
        else:
            mrd_cont[i] = cmin+(i-imin)*step
            
    mrd_cont = np.append(mrd_cont[::-1], mrd_cont)/100 # mirror, append, fraction
    
    return mrd_cont


# Sort functions

def SortMagCols(nlist):
    mergeSort(nlist)
    
def mergeSort(nlist):
    #print("Splitting ",nlist)
    if len(nlist)>1:
        mid = len(nlist)//2
        lefthalf = nlist[:mid]
        righthalf = nlist[mid:]

        mergeSort(lefthalf)
        mergeSort(righthalf)
        i=j=k=0       
        while i < len(lefthalf) and j < len(righthalf):
            if np.fabs(lefthalf[i]["dist"]) < np.fabs(righthalf[j]["dist"]):
                nlist[k]=lefthalf[i]
                i=i+1
            else:
                nlist[k]=righthalf[j]
                j=j+1
            k=k+1

        while i < len(lefthalf):
            nlist[k]=lefthalf[i]
            i=i+1
            k=k+1

        while j < len(righthalf):
            nlist[k]=righthalf[j]
            j=j+1
            k=k+1
    #print("Merging ",nlist)

#qsort((void *)inp, npts, sizeof(float), cmp)

def qsort(data_list):
    quickSortHlp(data_list,0,len(data_list)-1)

def quickSortHlp(data_list,first,last):
    if first < last:

        splitpoint = partition(data_list,first,last)

        quickSortHlp(data_list,first,splitpoint-1)
        quickSortHlp(data_list,splitpoint+1,last)


def partition(data_list,first,last):
    pivotvalue = data_list[first]

    leftmark = first+1
    rightmark = last

    done = False
    while not done:

        while leftmark <= rightmark and data_list[leftmark] <= pivotvalue:
            leftmark = leftmark + 1
 
        while data_list[rightmark] >= pivotvalue and rightmark >= leftmark:
            rightmark = rightmark -1
 
        if rightmark < leftmark:
            done = True
        else:
            temp = data_list[leftmark]
            data_list[leftmark] = data_list[rightmark]
            data_list[rightmark] = temp
 
    temp = data_list[first]
    data_list[first] = data_list[rightmark]
    data_list[rightmark] = temp
 
 
    return rightmark


# Obsolete function, kept for reference
def FreeMagColsData(start, end, incr, n, mc, length):
    if (mc):
        #float *data = NULL;
        #int cIdx;
        #int idx;
        for cIdx in range(start, end+1, incr):                  #for (cIdx = start; incr > 0 ? cIdx <= end : cIdx >= end; cIdx += incr)
            for idx in range(0, n[cIdx]):                       #for (idx = 0; idx < n[cIdx]; idx++)
                data = mc[cIdx][idx]["datacol"]
                if (len(data)>0):
                    mc[cIdx][idx]["datacol"] = np.zeros(length[1])
                    mc[cIdx][idx]["valid"] = 0
  

# Binning functions
#void frebinbox(float *image_in, float *image_out, int nx, int ny, int nbinx, int nbiny)
def frebinbox(image_in, image_out, nx, ny, nbinx, nbiny):

    #int nxout, nyout;
    #int ii, jj, i, j;
    nxout = int(nx / nbinx)
    nyout = int(ny / nbiny)

    for j in range(0, nyout):              #for (j = 0; j < nyout; j++)
    
        #int yOff, jy;
        jy = j * nbiny
        for i in range(0, nxout):          #for (i = 0; i < nxout; i++)
        
            #int ix;
            ix = i * nbinx
            aveval = 0.0                   #float aveval = 0.0;
            number = 0                     #int number = 0;
            for jj in range(0, nbiny):     #for (jj = 0; jj < nbiny; jj++)
            
                yOff = (jy + jj) * nx
                for ii in range(0, nbinx):          #for (ii = 0; ii < nbinx; ii++)
                
                    iData = yOff + ix + ii          #int iData = yOff + ix + ii;
                    if not np.isnan(image_in[iData]): #if (!(isnan(image_in[iData])))
                    
                        aveval += image_in[iData] # image_in[int(jy+jj)][int(ix+ii)]   #aveval += image_in[iData]
                        number += 1
            
            if number > 0:
                image_out[j * nxout + i] = aveval / number              #image_out[j * nxout + i] = aveval / number
            else:
                image_out[j * nxout + i] = np.nan


# Pixel statistics
#int magStats(float **val, int npts, double sum, int outThreshold, double *avg, float *med)
def magStats(val, npts, sum_, outThreshold):
    
    # variable name sum is taken by function -> rename to sum_
                        
    actPts = npts             #int actPts = npts;
    inp = copy(val)           #float *inp = *val;  # *inp points at the first entry of val -> same location in the memory, shallow copy
    idx = 0                   #int idx = 0;
    iout = 0                  #int iOut = 0;
    medianInt = 0.0           #float medianInt = 0.0;

    qsort(inp)
    
    # only enter if there are enough data points
    if (npts > outThreshold and npts > 1):
    
        actPts = npts - 1
        out = np.zeros(actPts)     #out = malloc(sizeof(float) * actPts)
        
        medianInt = inp[npts // 2]
        
        first = inp[0]
        last = inp[npts - 1]
        
        # remove outlier on one side
        if (np.fabs(first - medianInt) <= np.fabs(last - medianInt)):
            idx = 0
            sum_ -= last
        
        else:
            idx = 1
            sum_ -= first

        #for (iOut = 0; idx < npts && iOut < actPts; idx++, iOut++)
        for iOut in range(0, actPts):
            if (idx < npts):
                out[iOut] = inp[idx]
                idx = idx + 1
            else:
                break
        
        del(inp) #free(inp);
        val = out
        
        # filter zeros 
        #val = val[val!=0]
        #actPts = len(val)
        
        inp = val # useless in python
    
    avg = sum_ / actPts
    med = inp[actPts // 2]
    
    
    return val, actPts, avg, med


# Synoptic map main function
def synoptic_map(config):#, hw_overwrite=None):
    
    inRecs_hmi = config["timestring_hmi"]
    inRecs_phi = config["timestring_phi"]

    # query HMI and PHI remap data series separately
    drms_getkey_hmi, nRecs_hmi = get_drms_parameters_hmi(inRecs_hmi, config["input_ds_hmi"])
    drms_getkey_phi, nRecs_phi = get_drms_parameters_phi(inRecs_phi, config["input_ds_phi"], config["input_ds_phi_origin"])

    # combine into a single drms_getkey dictionary list for the remaining code
    # sort by descending CRLN_OBS to emulate T_REC order
    
    drms_getkey_tmp = drms_getkey_hmi + drms_getkey_phi
    drms_getkey = sorted(drms_getkey_tmp, key=lambda x: float(x['CRLN_OBS']), reverse=True)

    nRecs = nRecs_hmi + nRecs_phi

    # select the most common CAR_ROT entry and set it for all data
    # WARNING, this requires
    # - all data to be from the same map, as months offset would be overwritten by this
    # - the HMI dataset not to overlap with itself!
    # TODO this might need a decimal carrington number based on the first and last HMI date
    drms_getkey, common_carrot = update_common_carrot(drms_getkey)
    config["cr"] = common_carrot
    
    #nsig, mapmmax, sinbdivs, lgmin, lgmax, nbin, center, halfWindow, checkqual, los, force, dlog, nEquivPtsReq, noiseS, maxNoiseAdj, minOutPts = get_arg_parameters()
    
    #if hw_overwrite is not None:
    #    halfWindow = hw_overwrite
        
    length = [0,0]
    length[0] = rint(360.0 / (config["lgmax"] - config["lgmin"]) * config["mapmmax"])
    length[1] = 2 * config["sinbdivs"]
    
    config["length"] = [length[0], length[1]]
    
    synstep = 360.0 / length[0]
    synstart = (config["cr"] - 1) * 360.0 + 0.0 * synstep
    synend = config["cr"] * 360.0 - 1.0 * synstep

    # unused
    #nStackMags = rint(2 * config["halfWindow"] * 0.5) # /* consecutive magnetograms are shifted about 1 degree apart */

    sensAdj = 1 # unused and undefined in original code

    ## query HMI and PHI remap data series separately
    #drms_getkey_hmi, nRecs_hmi = get_drms_parameters(inRecs_hmi, config["input_ds_hmi"])
    #drms_getkey_phi, nRecs_phi = get_drms_parameters(inRecs_phi, config["input_ds_phi"])

    ## combine into a single drms_getkey dictionary list for the remaining code
    ## sort by descending CRLN_OBS to emulate T_REC order
    #drms_getkey_tmp = drms_getkey_hmi + drms_getkey_phi
    #drms_getkey = sorted(drms_getkey_tmp, key=lambda x: float(x['CRLN_OBS']), reverse=True)

    #nRecs = nRecs_hmi + nRecs_phi

    ## select the most common CAR_ROT entry and set it for all data
    #drms_getkey = update_common_carrot(drms_getkey)

    mrd_cont = adjacent_merdian_contributions(config["sinbdivs"], config["awf_dmin"], config["awf_dmax"], config["awf_cmin"], config["awf_cmax"]) #(sinbdivs, dmin, dmax, cmin, cmax) # TODO SETUP
    weights, cadences = adaptive_weight_functions(drms_getkey, synstep, mrd_cont, nimg=config["awf_nimg"], lim=config["awf_lim"], nlim=config["awf_nlim"]) #exp=config["awf_exp"])

    #imrec_keys = ["recno", "mapct", "mapCM", "mapdev", "ds", "tmin", "tmax", "tobs"]
    imrec = [] # list to hold dictionary

    idx = 0

    for ds in range(nRecs):
        mapct = 0.0
        mapCM = 0.0
        remapLgmax = 0.0
        remapLgmin = 0.0
        key = 0
        csKey = 0
        radialFound = 0
        losFound = 0

        inRec = ds
        
        #print(drms_getkey[inRec]['T_REC'], drms_getkey[inRec]['Ml'])
        # store timestring in inRec
        config["calVer"] = drms_getkey[inRec]["CALVER64"]
        trec   = drms_getkey[inRec]["T_REC"]

        #check data quality
        quality = drms_getkey[inRec]["QUALITY"]
        
        if (quality == QUAL_CHECK):
            print("SKIP: Bad QUALITY = 0x%08x; T_REC=%s, rejected iRec = %d\n" %(quality, trec, ds))
            continue

        #Ensure that all images used are either radial values or 
        #       * line-of-sight values, not a mixture of the two. */

        rkey = int(drms_getkey[inRec]["FDRADIAL"])
        if (rkey > 0):
            print("  Found radial keyword %d, ds=%d.\n", rkey, ds)
            if (losFound):
                print("  Attempt to use a mixture of radial and line-of-sight images.\n")
                print("    Rejecting ds=%d.\n" %ds)
                continue

            else:
                radialFound = 1

        else:
            if (radialFound):
                print("  Attempt to use a mixture of radial and line-of-sight images.\n")
                print("    Rejecting ds=%d.\n" %ds)
                continue

            else:
                losFound = 1

        csKey = int(drms_getkey[inRec]["CARSTRCH"])
        #csKey = (drms_ismissing_int(csKey)) ? 0 : csKey;

        if(idx == 0):
            carrStretch = csKey

        else:
            if(csKey != carrStretch):
                print("  Attempt to mix carr-streched and non-carr-stretched images.\n")
                print("    Rejecting ds=%d.\n" %ds)
                continue


        if (carrStretch > 0):
            csCoeffKey = float(drms_getkey[inRec]["DIFROT_A"])
            if (idx == 0):
                diffrotA = float(csCoeffKey)
            else: 
                if (np.fabs(csCoeffKey - diffrotA) > 0.001):
                    print("  Attempt to use inconsistent carr stretch parameters.\n")
                    print("    Rejecting ds=%d.\n" %ds)
                    continue

            csCoeffKey = float(drms_getkey[inRec]["DIFROT_B"])

            if (idx == 0):
                diffrotB = float(csCoeffKey)

            else:
                if (np.fabs(csCoeffKey - diffrotB) > 0.001):

                    print("  Attempt to use inconsistent carr stretch parameters.\n")
                    print("    Rejecting ds=%d.\n" %ds)
                    continue


            csCoeffKey = float(drms_getkey[inRec]["DIFROT_C"])
            if (idx == 0):
                diffrotC = float(csCoeffKey)

            else:
                if (np.fabs(csCoeffKey - diffrotC) > 0.001):
                    print("  Attempt to use inconsistent carr stretch parameters.\n")
                    print("    Rejecting ds=%d.\n" %ds)
                    continue 


        clong  = float(drms_getkey[inRec]["CRVAL1"])
        cmLong = float(drms_getkey[inRec]["CRLN_OBS"])
        orot   = int(drms_getkey[inRec]["CAR_ROT"])

        mapctnew = float(orot)*360.0 - clong  - config["center"]
        mapCMnew = float(orot)*360.0 - cmLong - config["center"]

        if (mapCMnew < mapCM):
            print("  Source image (ds=%d) has a smaller CT than previous img; skipped.\n", ds)
            continue

        else:
            mapct = mapctnew
            mapCM = mapCMnew

        remapLgmax = float(drms_getkey[inRec]["MAPLGMAX"])
        remapLgmin = float(drms_getkey[inRec]["MAPLGMIN"])
        
        # adaptive halfWindow depending on the local cadence variation
        # halfWindow always set by the longer cadence to the adjacent records
        width = len(weights[ds][0])
        config["halfWindow"] = np.round(((width-1) * synstep)/2., 5)
        
        imrec_tmp = {}
        imrec_tmp["src"] = drms_getkey[inRec]["INSTRUME"]
        imrec_tmp["filename"] = drms_getkey[inRec]["FILENAME"]
        imrec_tmp["mapdev"] = (remapLgmax - remapLgmin) / 2.0
        imrec_tmp["recno"]  = int(drms_getkey[inRec]["I_DREC"])
        imrec_tmp["mapct"]  = mapct
        imrec_tmp["mapCM"]  = mapCM
        imrec_tmp["ds"]     = ds
        imrec_tmp["tobs"]   = trec
        imrec_tmp["tmin"]   = np.max([mapCM - config["halfWindow"], mapct + config["center"] - imrec_tmp["mapdev"]])
        imrec_tmp["tmax"]   = np.min([mapCM + config["halfWindow"], mapct + config["center"] + imrec_tmp["mapdev"]])
        #imrec_tmp["wt"]     = weight_function(300, 3, sigma=30, center=25) # trapezoid with 300 pix for HW = 15 deg
        imrec_tmp["wt"]     = weights[ds] #wf #weight_function(300, 6, sigma=30, gamma=30, center=25)
        # temporary, remove after debugging:
        imrec_tmp["cadence"] = cadences[ds] #wf #weight_function(300, 6, sigma=30, gamma=30, center=25)
        imrec_tmp["crln_obs"] = cmLong #wf #weight_function(300, 6, sigma=30, gamma=30, center=25)
   
        
        imrec.append(imrec_tmp)
        idx += 1
    
    ngood = idx
    
    config["ngood"] = ngood
    config["DIFROT_A"] = diffrotA
    config["DIFROT_B"] = diffrotB
    config["DIFROT_C"] = diffrotC
    config["CARSTRCH"] = carrStretch
    
    print("\n######### SECOND PASS #################\n")

    wt   = np.zeros(length[0], dtype=int)
    ww   = np.zeros(length[0] * length[1], dtype=int)                 # UNUSED
    epts = np.zeros(length[0] * length[1], dtype=float)

    synopBr = np.zeros(length[0] * length[1], dtype=float)
    synopBt = np.zeros(length[0] * length[1], dtype=float)
    synopBp = np.zeros(length[0] * length[1], dtype=float)
    #losSynop = np.zeros(length[0] * length[1], dtype=float)
        
    sortedMagCol = init_sortedMagCol(length[0]) # sortedMagCol[3600][] empty list []

    started = 0
    ended   = 0
    nxtSyncol = length[0] - 1
    synRange  = 60.0

    # Longitude range in degree in synoptic chart;
    # divide the synoptic chart into pieces to avoid reading too much data
    nsynop = rint(360.0 / synRange)
    
    for ds in range (0, nsynop): #(ds = 0; ds < nsynop; ds++)

        subSynopStart = synstart + ds * synRange
        subSynopEnd = synstart + (ds + 1) * synRange - synstep
        SyncolStart = rint((synend - subSynopStart) / synstep)
        SyncolEnd   = rint((synend - subSynopEnd) / synstep)
        
        print("ds=%d\n" %ds)
        
        for idx in range (0, ngood): # (idx = 0; idx < ngood; idx++)

            magtype = 0.0
            equivPts = 0.0
            inRec = imrec[idx]["ds"] # inRD->records[imrec[idx].ds];
            
            # tmax < subSynopStart = stripe is to the left of subSynop area
            # tmin > subSynopEnd = stripe is to the right of subSynop area
            if (imrec[idx]["tmax"] <= subSynopStart or imrec[idx]["tmin"] >= subSynopEnd):
                continue

            #/* truncate the magnetogram's CT range at synstart or synend if necessary */
            #maprightct = np.max([subSynopStart, imrec[idx]["tmin"]])
            #mapleftct  = np.min([subSynopEnd, imrec[idx]["tmax"]])
            
            # truncating magnetograms at _subSynop_ borders produces NaN stripes with sparse PHI data
            maprightct = np.max([synstart, imrec[idx]["tmin"]])
            mapleftct  = np.min([synend, imrec[idx]["tmax"]])
            mapcols = int(drms_getkey[inRec]["MAPMMAX"]) + 1
            
            mapmidcol  = rint((mapcols - 1.0) / 2 + config["center"] / synstep)
            cols2right = rint((imrec[idx]["mapct"] - maprightct) / synstep)
            cols2left  = rint((imrec[idx]["mapct"] - mapleftct) / synstep)
            synmidcol  = rint((synend - imrec[idx]["mapct"]) / synstep)
            
            ##/* NOT the middle column of the
            # * synoptic chart, but essentially
            # * the column of the synoptic chart
            # * that corresponds to the middle
            # * column of the remapped img. */
            mrc = mapmidcol + cols2right
            mlc = mapmidcol + cols2left
            #/* src - right column of synoptic chart that matches with mrc */
            #/* slc - left column of synoptic chart that matches with mlc */
            src = synmidcol + cols2right
            slc = synmidcol + cols2left
            
            #/* For each column of the synoptic chart, push the corresponding input magnetogram's 
            # * column of data to the stack at that column.  The stack is an array of 2D 
            # * input images that will be averaged to make the synoptic chart.  The dimensions 
            # * of these images match the final dimensions of the synoptic chart.  Upon 
            # * completion of all input series, wt is the depth of the stack at each synoptic column. 
            # */

            equivPts = 1.0

            # Read inArray from current frame
            inArrayBr = fits.open(drms_getkey[inRec]["Br"])
            inArrayBt = fits.open(drms_getkey[inRec]["Bt"])
            inArrayBp = fits.open(drms_getkey[inRec]["Bp"])
            
            
            # synoptic columns/segments are processed from RIGHT to LEFT
            # weights are allocated from LEFT to RIGHT for each magnetogram
            # magnetograms are stored LEFT TO RIGHT -> fine

            # The next block of code requires symmetrical halfWindow sizes!
            # dwt offsets the weights for asymmetric slices (part of the window out of bounds)
            # abs() for the case where both are negative/postive
            # eg. cols2left = -20 / cols2right = -10 
            # here the slice is off the CM (eg boundary condition frames)
            dwt = 0            
            width = len(imrec[idx]["wt"][0])
            
            if abs(cols2right)+abs(cols2left) < width-1: # -1 to remove the middle column                                                           
                if abs(cols2right) > abs(cols2left):     # processing starts left, so left > right doesn't matter
                    dwt = width - (mrc+1-mlc)            # shift weights to align with data
            #else:                                        # right part out of segment
            #    dwt = 0                                  # no shift required
            
            # first column of each segment is missing if mrc+1 not used 
            for col in range(mlc, mrc+1): #(col = mlc; col <= mrc; ++col)
                mMagCol = init_MagCol(length)  # MagCol_t mMagCol;

                mMagCol["dist"]     = ((col - mapmidcol) * synstep + imrec[idx]["mapct"]) - imrec[idx]["mapCM"]
                mMagCol["datacolBr"]  = inArrayBr[0].data[:, col].copy() # (float *)malloc(sizeof(float) * length[1])
                mMagCol["datacolBt"]  = inArrayBt[0].data[:, col].copy() # (float *)malloc(sizeof(float) * length[1])
                mMagCol["datacolBp"]  = inArrayBp[0].data[:, col].copy() # (float *)malloc(sizeof(float) * length[1])
                mMagCol["equivPts"] = equivPts
                mMagCol["ds"]       = imrec[idx]["ds"]
                mMagCol["col"]      = col
                mMagCol["valid"]    = 1
                mMagCol["wt"]       = imrec[idx]["wt"][:, dwt+col-mlc]

                # col-mlc gives me the Nth column with respect to the current [mlc,mrc] window
                # dwt offsets this by the remainder of the window in the current segment
                # mrc+1-mlc gives me the frame width for the current segment
                # dwt = width - (mrc-mlc)
                syncol = col + slc - mlc

                sortedMagCol[syncol].append(mMagCol)
                wt[syncol] += 1 

            inArrayBr.close()
            inArrayBt.close()
            inArrayBp.close()
            
        calcsynret = CalcSynCols(SyncolStart,
                                 SyncolEnd,
                                 -1,
                                 sortedMagCol,
                                 synopBr,
                                 synopBt,
                                 synopBp,
                                 wt,
                                 ww,
                                 epts,
                                 #losSynop,
                                 length,
                                 config["center"],
                                 config["nEquivPtsReq"],
                                 config["los"],
                                 #radialFound,
                                 sensAdj,
                                 config["noiseS"],
                                 config["nsig"],
                                 config["maxNoiseAdj"],
                                 config["minOutPts"],
                                 config["dlog"],
                                 kNOISE_EQ)


        #FreeMagColsData(SyncolStart, SyncolEnd, -1, wt, sortedMagCol, length)

    #smallSynop = np.zeros([int(length[1]/config["nbin"]), int(length[0]/config["nbin"])])
    #smallEpts  = np.zeros([int(length[1]/config["nbin"]), int(length[0]/config["nbin"])])

    #frebinbox(synop, smallSynop, length[0], length[1], config["nbin"], config["nbin"] - 1)
    #frebinbox(epts,  smallEpts,  length[0], length[1], config["nbin"], config["nbin"] - 1)
    
    return synopBr, synopBt, synopBp, epts, length, imrec

    # data ready in synop/epts and smallSynop/smallEpts


# Synoptic Column calculation

def CalcSynCols(start, #int start,
                end,   #int end,
                incr,  #int incr,
                smc,   #MagCol_t **smc,
                synopBr,
                synopBt,
                synopBp,
                wt,    #int *wt,
                ww,    #char *ww,               # UNUSED
                epts,  #float *epts,
                #losSynop, #float *losSynop,
                length,   #int *len,
                center,   #float center,
                nEquivPtsReq, #float nEquivPtsReq,
                los,          #int los,
                #radialFound,  #int radialFound,
                sensAdj,  #float sensAdj,
                noiseS,   #float noiseS,
                nsig,     #float nsig,
                maxNoiseAdj,  #float maxNoiseAdj,
                minOutPts,    #int minOutPts,
                dlog,         #int dlog
                kNOISE_EQ):   # added since not global in python


    #float cosrho; #/* equal cos(magnetogram latitude) * cos(magnetogram dlatitude) 
    #              # *   where dlatitude is positive delta between CM and point.
    #              # * approximate dlatitude with 'center' (assume for all 
    #              # * magnetograms, data comes from CM - center, even though
    #              # *   they will come from points surrounding this column. */

    
    #DRMS_MISSING_FLOAT = np.nan    
    nrej = 0            #  UNUSED
      
    midSynRow = float(length[1] - 1) / 2.0
    cosCenter = np.cos(center * np.pi / 180)
    rejDescFormat = "      magnetogram: ds=%d, sn=%d, magcol=%d, magrow=%d\n" # this will crash
    
    if (minOutPts < 2): 
        minOutPts = 2
    
    #/* loop over synoptic chart column */
    if incr < 0:
        incl = -1
    else:
        incl = 1

    for col in range(start, end+incl, incr):
        valBr = np.zeros(wt[col])        #float *valBr = (float *)malloc(sizeof(float) * wt[col]);
        valBt = np.zeros(wt[col])        #float *valBt = (float *)malloc(sizeof(float) * wt[col]);
        valBp = np.zeros(wt[col])        #float *valBp = (float *)malloc(sizeof(float) * wt[col]);
        
        ept = np.zeros(wt[col])        #float *ept = (float *)malloc(sizeof(float) * wt[col]);
        wti = np.zeros(wt[col])        #float *ept = (float *)malloc(sizeof(float) * wt[col]);

        # *pcols = NULL;
        SortMagCols(smc[col])     # confirmed to work 

        #/* loop over synoptic chart row */
        for row in range(0, length[1]):       #for (row = 0; row < len[1]; ++row)
            
            sinLat = (row - midSynRow) / midSynRow             #float sinLat = (row - midSynRow) / midSynRow;
            cosLat = np.sqrt(1 - sinLat * sinLat)                 #float cosLat = sqrt(1 - sinLat * sinLat);

            sumfinalBr = 0.0                                     #float sumfinalBr = 0.0;
            sumfinalBt = 0.0                                     #float sumfinalBt = 0.0;
            sumfinalBp = 0.0                                     #float sumfinalBp = 0.0;
            
            nptsfinal = 0                                      #int nptsfinal = 0;
            Maxnepts = nEquivPtsReq + 10                       #int Maxnepts = nEquivPtsReq + 10;
            wtfinal = 0.0
            
            #if (radialFound):
            #    cosrho = cosLat * cosCenter
    
            sum_ = 0.0
            npts = 0
            j = 0
            nEquivPts = 0.0
    
            #/* Loop over synoptic chart stack above col, row, averaging the values. */
            #/* Take the magnetograms with the best values first (smallest dist to CM) 
            # * and take only the fewest possible until nEquivPtsReq one-minute-equivalent 
            # * points are attained. */
            
            # this loops over all possible sources for a single [col][row] datapoint
            # check if there is valid data in each source and add/average them
            # wt tracking necessary for i sources of each [col][row]
            i = 0
            nrej = 0            #  new implementation
            
            # TODO BUG FIX
            # val, ept, wti are defined with np.zeros length wt[col] which might be > Maxnepts
            # this leads to initialised zeros in the data array that shouldn't be there
            # and causes problems after qsorting the values.
            # median and average will get distorted by this
            # fix this and everything should work
            # this is not an issue at 2h cadence because wt[col] is always < Maxnepts
            
            while (i < wt[col] and nEquivPts < Maxnepts):           # for (i = 0; i < wt[col] && nEquivPts < Maxnepts; i++)

                magValBr = smc[col][i]["datacolBr"][row]                 # float magVal = *(smc[col][i].datacolBr + row);
                magValBt = smc[col][i]["datacolBt"][row]                 # float magVal = *(smc[col][i].datacolBt + row);
                magValBp = smc[col][i]["datacolBp"][row]                 # float magVal = *(smc[col][i].datacolBp + row);
                                        
                if not drms_ismissing_float(magValBr):
                    
                    nEquivPts += smc[col][i]["equivPts"]
                    sum_  += magValBr
                    valBr[j] = magValBr
                    valBt[j] = magValBt
                    valBp[j] = magValBp
                    
                    ept[j] = smc[col][i]["equivPts"]
                    wti[j] = smc[col][i]["wt"][row]                 # TODO track wti[j] for averaging later wt col

                    j = j + 1
                    npts = npts + 1

                i = i + 1
                
            # discard initialised but unfilled columns
            #valBr = valBr[:j]
            #valBt = valBt[:j]
            #valBp = valBp[:j]
            
            #ept = ept[:j] 
            #wti = wti[:j] 
            # this was moved to statVals = copy(val[:j]) 
            
            #/* Calculate summary statistics */
            if (npts > 1 and nsig > 0.0):

                avg = 0.0        # double avg = 0.0;
                ssqr = 0.0       # double ssqr = 0.0;

                nStatPts = 0     # int nStatPts = 0;

                statsDone = 0    # int statsDone = 0;
                sIdx = 0         # int sIdx = 0;
                dev = 0.0        # float dev = 0.0;
                nPtsB4Rej = npts # int nPtsB4Rej = npts;
    
                #/* calculate threshold - below this, point values are within noise levels -
                # * we don't want to reject them under any circumstances */
            
                noiseLevel = kNOISE_EQ * noiseS * sensAdj #// noiseLevel not be used so far.
                #if (radialFound):
                #    noiseLevel = noiseLevel * int(np.min(1 / cosrho, maxNoiseAdj))
                    
                statVals = copy(valBr[:j])            
                statVals, nStatPts, avg, med = magStats(statVals, npts, sum_, minOutPts)

                #/* Reject outliers whose values exceeds the noise threshold */
                for j in range(0, nPtsB4Rej):   #for (j = 0; j < nPtsB4Rej; ++j)

                    if not statsDone:
                        for sIdx in range(0, nStatPts): #for (sIdx = 0; sIdx < nStatPts; sIdx++)
                            ssqr += statVals[sIdx] * statVals[sIdx]
                            
                        sig = np.sqrt((ssqr - nStatPts * avg * avg) / (nStatPts - 1))
                        statsDone = 1

                    dev = np.fabs(valBr[j] - med)
                    if (nptsfinal >= nEquivPtsReq):
                        break
 
                    if npts > 10:                            # deactivate outlier rejection for low number datasets
                        if (dev < nsig * sig):
                            sumfinalBr  += valBr[j] * wti[j]
                            sumfinalBt  += valBt[j] * wti[j]
                            sumfinalBp  += valBp[j] * wti[j]

                            nptsfinal += 1
                            wtfinal   += wti[j] 

                            #npts -= 1 #--npts;               # npts seems to count the remaining data records. Why?
                                                              # repurposed to deactivate outlier rejection
                        else:
                            nrej += 1 #++nrej;               # UNUSED
                    else:
                        sumfinalBr  += valBr[j] * wti[j]
                        sumfinalBt  += valBt[j] * wti[j]
                        sumfinalBp  += valBp[j] * wti[j]
                            
                        nptsfinal += 1
                        wtfinal   += wti[j] 

                del(statVals) #free(statVals);

            #/* Calcuate the average value for each x,y in the stack */
            if (nptsfinal):
                #TODO: check if this is correct: RuntimeWarning: invalid value encountered in scalar divide
                synValBr = sumfinalBr / wtfinal #nptsfinal          #float synVal = sumfinal / nptsfinal;
                synValBt = sumfinalBt / wtfinal #nptsfinal          #float synVal = sumfinal / nptsfinal;
                synValBp = sumfinalBp / wtfinal #nptsfinal          #float synVal = sumfinal / nptsfinal;

                minVal = (SHRT_MIN + 1) #// * kOutScale;        #float minVal = (SHRT_MIN + 1); // * kOutScale;
                maxVal = (SHRT_MAX - 1) #// * kOutScale;        #float maxVal = (SHRT_MAX - 1); // * kOutScale;
        
                #/* The desired output will be a 16 bpp image with bscale == 0.1.
                #    * If 16 bits cannot hold the float value, then cap the value at 
                #    * the largest value (in magnitude) that 16 bits can hold. */
                
                if (synValBr < minVal):
                    synopBr[row * length[0] + col] = minVal
                
                elif (synValBr > maxVal):
                    synopBr[row * length[0] + col] = maxVal
                
                else:
                    synopBr[row * length[0] + col] = synValBr
                    
                
                if (synValBt < minVal):
                    synopBt[row * length[0] + col] = minVal
                
                elif (synValBt > maxVal):
                    synopBt[row * length[0] + col] = maxVal
                
                else:
                    synopBt[row * length[0] + col] = synValBt
                    
                    
                if (synValBp < minVal):
                    synopBp[row * length[0] + col] = minVal
                
                elif (synValBp > maxVal):
                    synopBp[row * length[0] + col] = maxVal
                
                else:
                    synopBp[row * length[0] + col] = synValBp
                
            else:
                synopBr[row * length[0] + col] = DRMS_MISSING_FLOAT;
                synopBt[row * length[0] + col] = DRMS_MISSING_FLOAT;
                synopBp[row * length[0] + col] = DRMS_MISSING_FLOAT;
    
            ww[row * length[0] + col] = npts
            #//	 epts[row * len[0] + col] = nEquivPts;
            epts[row * length[0] + col] = nptsfinal

            #if (los and radialFound):
            #    
            #    offset = int(row * length[0] + col)
            #    if (drms_ismissing_float(synopBr[offset])):
            #        losSynop[offset] = DRMS_MISSING_FLOAT
            #    
            #    else:
            #        losSynop[offset] = synopBr[offset] * cosLat
            
        del(valBr) #free(valBr);
        del(valBt) #free(valBt);
        del(valBp) #free(valBp);
        
        del(ept) #free(ept);

    #return 0


# Image statistics

def fstats(npix, synop, small=False):

    statMin  = np.nanmin(synop)
    statMax  = np.nanmax(synop)
    statMedn = np.nanmedian(synop)
    statMean = np.nanmean(synop)
    statSig  = np.nanstd(synop)
    statSkew = sp.stats.skew(synop, nan_policy='omit')#.compressed()[0]
    statKurt = sp.stats.kurtosis(synop, nan_policy='omit')
    statNgood = len(synop[~np.isnan(synop)])
    
    
    stats = {"statMin": statMin,  
             "statMax": statMax, 
             "statMedn": statMedn, 
             "statMean": statMean,  
             "statSig": statSig, 
             "statSkew": statSkew, 
             "statKurt": statKurt,  
             "statNgood": statNgood}
    
    return stats


# Synoptic map header
def create_header(outRec, config, stats, imrec, small=False):
    
    if small:
        xout = config["length"][0] // config["xbin"]
        yout = config["length"][1] // config["ybin"]
    else:
        xout = config["length"][0]
        yout = config["length"][1]

    eph = np.zeros(30)
    tstart = CarringtonTime(config["cr"], 360.0)
    tstop  = CarringtonTime(config["cr"], 0.0)
    trot   = CarringtonTime(config["cr"], 180.0)
    delta_T = sscan_time("1977.01.01_00:00:00_TAI") - sscan_time("1601.01.01_00:00:00_UT")
    
    firstidx = 0
    lastidx = config["ngood"] - 1
    
    outRec["DATE"] = date.today().strftime("%Y-%m-%d")
    outRec["BUNIT"] = "Mx/cm^2"     #       drms_setkey_string(outRec["BUNIT", "Mx/cm^2")
    
    #for image coordinate mapping keywords
    historyofthemodule = "Module version added -- Feb 2014; Carrington-Time conversion corrected; o2helio.c bug corrected; CRPIX, CRVAL corrected -- Jan. 2014"
    jsoc_version = "(MISSING) Code release build number of program"
    cvsinfo = "(MISSING) Code version"
    
    outRec["HISTORY"] = historyofthemodule
    outRec["BLD_VERS"] = jsoc_version
    outRec["CODEVER"] = cvsinfo
    
    outRec["CTYPE1"] = "CRLN-CEA"
    outRec["CTYPE2"] = "CRLT-CEA"
    #        i=len[0]/2+0.5
    

    # 1. CRVAL is defined as 180 degree longitude.
    # 2. Carrington longitude goes from right to the left.
    # 3. The counting begins with 1 but *not* 0.
    # 4. The pixel of interest is (len[0]/2+1.0) if counting starts from right to left.
    # 5. Flipping to left to right, this pixel is len[0]-(len[0]/2+1.0)+1.0.
    if small: tmp = xout - ((180.0 - ((config["xbin"] + 1) / 2.0 - 1.0) * (360.0 / xout)) / (360.0 / xout) + 1.0) + 1.0
    else :    tmp = xout - (xout / 2 + 1.0) + 1.0
    outRec["CRPIX1"] = tmp
    # origin is at the center of the first pixel. The counting is 1.
    outRec["CRPIX2"] = (yout + 1.0) / 2
    # origin is at center of the first pixel.
    #        carrtime = (cr-1)*360.0 + 180.0 - (double)(0.5 * 360.0/config["length"][0])
    carrtime = (config['cr']- 1) * 360.0 + 180.0 # CARRTIME is defined as 180 degree longitude.
    outRec["CRVAL1"] = carrtime
    outRec["CRVAL2"] = 0.0
    outRec["CDELT1"] = -360.0 / xout
    
    outRec["CDELT2"] = 1.0 / config["sinbdivs"]
    if small: outRec["CDELT2"] = config["ybin"] * 1.0 / config["sinbdivs"]
        
    outRec["CUNIT1"] = "degree"
    outRec["CUNIT2"] = "Sine Latitude"
    outRec["WCSNAME"] = "Carrington Heliographic"

    #HMI observables keywords
    #sprint_at(tstr, trot - delta_T) # time at 180 degree longitude
                                   #        drms_setkey_string(outRec["T_REC", tstr)
                                   #        outRec["CADENCE", 27.2753*24.*60.*60.)
                                   #        outRec["T_REC_step", 27.2753*24.*60.*60.)

    # image statistics
    #TODO config["length"] not right for small synoptic
    outRec["TOTVALS"]  = xout * yout
    outRec["DATAVALS"] = stats["statNgood"]
    outRec["MISSVALS"] = xout * yout - stats["statNgood"]
    outRec["DATAMIN"]  = stats["statMin"]
    outRec["DATAMAX"]  = stats["statMax"]
    outRec["DATAMEDN"] = stats["statMedn"]
    outRec["DATAMEAN"] = stats["statMean"]
    outRec["DATARMS"]  = stats["statSig"]
    outRec["DATASKEW"] = stats["statSkew"]
    outRec["DATAKURT"] = stats["statKurt"]

    #Synoptic map keywords
    # TODO AUF COMBINED ANPASSEN
    outRec["T_OBS"]   = trot - delta_T
    outRec["T_ROT"]   = trot - delta_T
    outRec["T_START"] = tstart - delta_T
    outRec["T_STOP"]  = tstop - delta_T

    #outRec["T_EARTH"] = tearth
    outRec["CAR_ROT"]  = config["cr"]
    outRec["CARRTIME"] = carrtime
    solephem(trot, eph)
    outRec["B0_ROT"] = eph[9] / RADSINDEG
    
    solephem(tstart, eph)
    outRec["B0_FRST"] = eph[9] / RADSINDEG
    
    solephem(tstop, eph)
    outRec["B0_LAST"] = eph[9] / RADSINDEG
    #        outRec["EARTH_B0", bearth)
    
    if small:  l = (config['cr']- 1) * 360.0 + ((config["xbin"] + 1) / 2.0 - 1.0) * (360.0 /xout)
    else:      l = (config['cr']- 1) * 360.0
    outRec["LON_FRST"] = l
    
    if small: l = config['cr'] * 360.0 - 360.0 / xout - ((config["xbin"] + 1) / 2.0 - 1.0) * (360.0 / xout)
    else:     l = config['cr'] * 360.0 - 360.0 / xout
    outRec["LON_LAST"] = l

    outRec["LON_STEP"] = -360.0 / xout
    outRec["W_OFFSET"] = config["center"]
    outRec["W_WEIGHT"] = "HMI: Even | PHI: %s%% at adjacent meridian" %config["awf_cmin"] #"Even"
    outRec["IMG_NUM"] = lastidx - firstidx + 1
    #TODO
    #sprint_at(tstr, imrec[firstidx].tobs)
    outRec["IMG_FRST"] = imrec[firstidx]["tobs"]
    #sprint_at(tstr, imrec[lastidx].tobs)
    outRec["IMG_LAST"] = imrec[lastidx]["tobs"]
    #sprint_at(tstr, magtime)
    #magtime = imrec[(int)(ngood / 2)].tobs;
    outRec["IMG_ROT"]  = imrec[config["ngood"] // 2]["tobs"] #magtime
    outRec["HWNWIDTH"] = config["halfWindow"]
    outRec["EQPOINTS"] = config["nEquivPtsReq"]
    outRec["NSIGMA"]   = config["nsig"]
    outRec["CALVER64"] = config["calVer"]

    #        drms_copykey(outRec, inRec, "CALVER64")

    # save the differential rotation correction parameters
    if config["CARSTRCH"] > 0:
        outRec["CARSTRCH"] = config["CARSTRCH"]
        outRec["DIFROT_A"] = config["DIFROT_A"]
        outRec["DIFROT_B"] = config["DIFROT_B"]
        outRec["DIFROT_C"] = config["DIFROT_C"]
 
# Image array conversion
def convert_image_array(img_in, img_out, nx, ny):

    for col in range(0, nx):
        for row in range(0, ny):
            img_out[row][col] = img_in[row * nx + col] 


# TODO MOVE TO CONFIG
def get_arg_parameters(global_config):

    # IMPORTANT: CHECK IF MAPMMAX AND SINBDIVS MATCH THE PROJECTION RESOLUTION
    config = {
        # 
        "cr":   global_config.cr,
        "proj": global_config.proj,  # "Mr" or "Ml"
        # TODO B3comp dataseries
        "input_ds_hmi":        global_config.data_series_remap_hmi, #"mps_loeschl.B3comp_disambR_remap_final_720s"bin_070au", 
        "input_ds_phi":        global_config.data_series_remap_phi, #"mps_loeschl.Mr_remap_CR2258_FDT_test_release_june_2022_defri", #"mps_loeschl.mr_remap_cr2240_fdt_test_release_sup_conj_2021", #"mps_loeschl.Mr_remap_CR2240_trl_v01", #"mps_loeschl.Ml_remap_CR2240_rev02_ideal",#"mps_loeschl.Mr_remap_CR2240_rev03", #"mps_loeschl.Ml_remap_CR2240_rev02",#"mps_loeschl.Ml_remap_CR2240_fast", #"mps_loeschl.Ml_remap_720s", #"mps_loeschl.Ml_remap_720s_1440p_1xbin_070au", #"mps_loeschl.Ml_remap_720s",#_720p_2xbin_070au", #mps_loeschl.Ml_remap_720s #mps_loeschl.Ml_remap_CR2255
        "input_ds_phi_origin": global_config.data_series_phi,
        "timestring_hmi":      global_config.timestring_hmi, 
        "timestring_phi":      global_config.timestring_phi,
        "interval_hmi":        global_config.interval_hmi,
        "interval_phi":        global_config.interval_phi, 
        "synop_name":          global_config.synop_name,
        "synop_small_name":    global_config.synop_small_name,

        "synop_path": global_config.synop_path,

        # Adjacent Meridian Contribution for Weight Function Shape
        "awf_nimg": global_config.awf_nimg , # ODD number of images considered for the weightfunction, ODD number: center + N on each side
        "awf_cmin": global_config.awf_cmin , # minimum contribution %
        "awf_cmax": global_config.awf_cmax , # maximum contribution % set equal to awf_cmin for none lattitude speicfic weights
        "awf_dmin": global_config.awf_dmin , # latitude border until which minimum contribution is used
        "awf_dmax": global_config.awf_dmax , # latitude border from which maximum contribution is used
        "awf_lim":  global_config.awf_lim  ,
        "awf_nlim": global_config.awf_nlim, # TODO define size limit for awf slice (still unused)
        
        # don't have to touch these
        # rebinning
        "bin":  global_config.bin,
        "xbin": global_config.xbin,
        "ybin": global_config.ybin,
        
        # classic hmisynoptic parameters
        "nsig":         global_config.nsig,      #3.0, 
        "mapmmax":      global_config.mapmmax,   #1800, half size 3600
        "sinbdivs":     global_config.sinbdivs,  #720,  half size 1440
        "lgmin":        global_config.lgmin,     # -90,
        "lgmax":        global_config.lgmax,     # +90,
        "checkqual":    global_config.checkqual, # 0,
        "center":       global_config.center,    # 0.0,
        "los":          0,                       # 0, # obsolete variable
        "dlog":         global_config.dlog,      # 0,
        "nEquivPtsReq": global_config.nEquivPtsReq, # 20, 
        "noiseS":       global_config.noiseS,       # 3.0, 
        "maxNoiseAdj":  global_config.maxNoiseAdj,  # 3.0,
        "minOutPts":    global_config.minOutPts    # 4.0,
        
        #"halfWindow":15, # now dynamically calculated. obsolete
        #"force": 0,   # unused / obsolete
    }
    
    return config    


def main(global_config, session_folder):
    config = get_arg_parameters(global_config)    
    synop_outpath = os.path.join(session_folder, config["synop_path"])

    synopBr, synopBt, synopBp, epts, length, imrec =  synoptic_map(config)

    #synopBr_img = np.zeros([length[1], length[0]])
    #synopBt_img = np.zeros([length[1], length[0]])
    #synopBp_img = np.zeros([length[1], length[0]])  

    #convert_image_array(synop, synop_img, length[0], length[1])    
    synopBr_img = np.reshape(synopBr, (length[1], length[0])) # confirmed to work identical to convert_image_array()
    synopBt_img = np.reshape(synopBt, (length[1], length[0])) # confirmed to work identical to convert_image_array()
    synopBp_img = np.reshape(synopBp, (length[1], length[0])) # confirmed to work identical to convert_image_array()
    
    stats = fstats(length[1]*length[0], synopBr, small=False)
    
    hduBr = fits.PrimaryHDU(synopBr_img)
    hduBt = fits.PrimaryHDU(synopBt_img)
    hduBp = fits.PrimaryHDU(synopBp_img)

    table_hdu = create_src_fits_table(imrec)

    create_header(hduBr.header, config, stats, imrec)
    create_header(hduBt.header, config, stats, imrec)
    create_header(hduBp.header, config, stats, imrec)

    hdulBr = fits.HDUList([hduBr, table_hdu])
    hdulBt = fits.HDUList([hduBt, table_hdu])
    hdulBp = fits.HDUList([hduBp, table_hdu])

    hdulBr.writeto(os.path.join(synop_outpath,'synopBr.fits'), overwrite=True)
    hdulBt.writeto(os.path.join(synop_outpath,'synopBt.fits'), overwrite=True)
    hdulBp.writeto(os.path.join(synop_outpath,'synopBp.fits'), overwrite=True)

    plot_synoptic_sources(synopBr_img, 'B_r', synop_outpath, 'synopBr', config['cr'], table_hdu.data, save=True) 
    plot_synoptic_sources(synopBt_img, 'B_t', synop_outpath, 'synopBt', config['cr'], table_hdu.data, save=True) 
    plot_synoptic_sources(synopBp_img, 'B_p', synop_outpath, 'synopBp', config['cr'], table_hdu.data, save=True)   
    
    if config["bin"]:
        # create small synoptic map
        # length  = [x,y]
        xbin = config["xbin"]
        ybin = config["ybin"] 

        smallSynopBr = np.zeros(int(length[1]/(ybin))* int(length[0]/xbin))
        smallSynopBt = np.zeros(int(length[1]/(ybin))* int(length[0]/xbin))
        smallSynopBp = np.zeros(int(length[1]/(ybin))* int(length[0]/xbin))

        frebinbox(synopBr, smallSynopBr, length[0], length[1], xbin, ybin)
        frebinbox(synopBt, smallSynopBt, length[0], length[1], xbin, ybin)
        frebinbox(synopBp, smallSynopBp, length[0], length[1], xbin, ybin)

        smallSynopBr_img = np.zeros([int(length[1]/ybin), int(length[0]/xbin)])
        smallSynopBt_img = np.zeros([int(length[1]/ybin), int(length[0]/xbin)])
        smallSynopBp_img = np.zeros([int(length[1]/ybin), int(length[0]/xbin)])

        smallSynopBr_img = np.reshape(smallSynopBr, (int(length[1]/ybin), int(length[0]/xbin)))
        smallSynopBt_img = np.reshape(smallSynopBt, (int(length[1]/ybin), int(length[0]/xbin)))
        smallSynopBp_img = np.reshape(smallSynopBp, (int(length[1]/ybin), int(length[0]/xbin)))
        
        #smallEpts  = np.zeros(int(length[1]/(ybin))* int(length[0]/xbin))
        #frebinbox(epts,  smallEpts,  length[0], length[1], xbin, ybin)
        #convert_image_array(smallSynop, smallSynop_img, int(length[0]/xbin), int(length[1]/ybin))
        
        stats_small = fstats(length[1]//ybin*length[0]//xbin, smallSynopBr)

        hduBr_small = fits.PrimaryHDU(smallSynopBr_img)
        hduBt_small = fits.PrimaryHDU(smallSynopBt_img)
        hduBp_small = fits.PrimaryHDU(smallSynopBp_img)

        table_hdu = create_src_fits_table(imrec)

        create_header(hduBr_small.header, config, stats, imrec)
        create_header(hduBt_small.header, config, stats, imrec)
        create_header(hduBp_small.header, config, stats, imrec)

        hdulBr_small = fits.HDUList([hduBr_small, table_hdu])
        hdulBt_small = fits.HDUList([hduBt_small, table_hdu])
        hdulBp_small = fits.HDUList([hduBp_small, table_hdu])

        hdulBr_small.writeto(os.path.join(synop_outpath,'synopBr_small.fits'), overwrite=True)
        hdulBt_small.writeto(os.path.join(synop_outpath,'synopBt_small.fits'), overwrite=True)
        hdulBp_small.writeto(os.path.join(synop_outpath,'synopBp_small.fits'), overwrite=True)

        plot_synoptic_sources(smallSynopBr_img, 'B_r', synop_outpath, 'synopBr_small', config['cr'], table_hdu.data, save=True) 
        plot_synoptic_sources(smallSynopBt_img, 'B_t', synop_outpath, 'synopBt_small', config['cr'], table_hdu.data, save=True) 
        plot_synoptic_sources(smallSynopBp_img, 'B_p', synop_outpath, 'synopBp_small', config['cr'], table_hdu.data, save=True)   

    print('%s complete' %__file__)

    return STATUS_OK

if __name__ == "__main__":
    from config import Config
    import argparse
    from utils import create_session_folder, create_session_structure
    
    def parse_args():
        parser = argparse.ArgumentParser(
            description="Run the synoptic pipeline with optional config and session paths."
        )
        parser.add_argument(
            "--config",
            type=str,
            help="Path to config.yaml (uses default parameters if no config is provided)."
        )
        parser.add_argument(
            "--session",
            type=str,
            help="Path to an existing session folder (creates new session if no folder is provided)."
        )
        return parser.parse_args()

    #set cwd to file directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    args = parse_args()

    # Load config from YAML
    global_config = Config(config_path=args.config) if args.config else Config()

    # Determine session folder
    if args.session:
        session_folder = os.path.abspath(args.session)
        create_session_structure(global_config, session_folder)
    else:
        session_folder = create_session_folder(global_config) 

    config = get_arg_parameters(global_config)    
    synop_outpath = os.path.join(session_folder, config["synop_path"])

    synopBr, synopBt, synopBp, epts, length, imrec =  synoptic_map(config)

    #synopBr_img = np.zeros([length[1], length[0]])
    #synopBt_img = np.zeros([length[1], length[0]])
    #synopBp_img = np.zeros([length[1], length[0]])  

    #convert_image_array(synop, synop_img, length[0], length[1])    
    synopBr_img = np.reshape(synopBr, (length[1], length[0])) # confirmed to work identical to convert_image_array()
    synopBt_img = np.reshape(synopBt, (length[1], length[0])) # confirmed to work identical to convert_image_array()
    synopBp_img = np.reshape(synopBp, (length[1], length[0])) # confirmed to work identical to convert_image_array()
    
    stats = fstats(length[1]*length[0], synopBr, small=False)
    
    hduBr = fits.PrimaryHDU(synopBr_img)
    hduBt = fits.PrimaryHDU(synopBt_img)
    hduBp = fits.PrimaryHDU(synopBp_img)

    table_hdu = create_src_fits_table(imrec)

    create_header(hduBr.header, config, stats, imrec)
    create_header(hduBt.header, config, stats, imrec)
    create_header(hduBp.header, config, stats, imrec)

    hdulBr = fits.HDUList([hduBr, table_hdu])
    hdulBt = fits.HDUList([hduBt, table_hdu])
    hdulBp = fits.HDUList([hduBp, table_hdu])

    hdulBr.writeto(os.path.join(synop_outpath,'synopBr.fits'), overwrite=True)
    hdulBt.writeto(os.path.join(synop_outpath,'synopBt.fits'), overwrite=True)
    hdulBp.writeto(os.path.join(synop_outpath,'synopBp.fits'), overwrite=True)

    plot_synoptic_sources(synopBr_img, 'B_r', synop_outpath, 'synopBr', config['cr'], table_hdu.data, save=True) 
    plot_synoptic_sources(synopBt_img, 'B_t', synop_outpath, 'synopBt', config['cr'], table_hdu.data, save=True) 
    plot_synoptic_sources(synopBp_img, 'B_p', synop_outpath, 'synopBp', config['cr'], table_hdu.data, save=True) 
    
    if config["bin"]:
        # create small synoptic map
        # length  = [x,y]
        xbin = config["xbin"]
        ybin = config["ybin"] 

        smallSynopBr = np.zeros(int(length[1]/(ybin))* int(length[0]/xbin))
        smallSynopBt = np.zeros(int(length[1]/(ybin))* int(length[0]/xbin))
        smallSynopBp = np.zeros(int(length[1]/(ybin))* int(length[0]/xbin))

        frebinbox(synopBr, smallSynopBr, length[0], length[1], xbin, ybin)
        frebinbox(synopBt, smallSynopBt, length[0], length[1], xbin, ybin)
        frebinbox(synopBp, smallSynopBp, length[0], length[1], xbin, ybin)

        smallSynopBr_img = np.zeros([int(length[1]/ybin), int(length[0]/xbin)])
        smallSynopBt_img = np.zeros([int(length[1]/ybin), int(length[0]/xbin)])
        smallSynopBp_img = np.zeros([int(length[1]/ybin), int(length[0]/xbin)])

        smallSynopBr_img = np.reshape(smallSynopBr, (int(length[1]/ybin), int(length[0]/xbin)))
        smallSynopBt_img = np.reshape(smallSynopBt, (int(length[1]/ybin), int(length[0]/xbin)))
        smallSynopBp_img = np.reshape(smallSynopBp, (int(length[1]/ybin), int(length[0]/xbin)))
        
        #smallEpts  = np.zeros(int(length[1]/(ybin))* int(length[0]/xbin))
        #frebinbox(epts,  smallEpts,  length[0], length[1], xbin, ybin)
        #convert_image_array(smallSynop, smallSynop_img, int(length[0]/xbin), int(length[1]/ybin))
        
        stats_small = fstats(length[1]//ybin*length[0]//xbin, smallSynopBr)

        hduBr_small = fits.PrimaryHDU(smallSynopBr_img)
        hduBt_small = fits.PrimaryHDU(smallSynopBt_img)
        hduBp_small = fits.PrimaryHDU(smallSynopBp_img)

        create_header(hduBr_small.header, config, stats, imrec)
        create_header(hduBt_small.header, config, stats, imrec)
        create_header(hduBp_small.header, config, stats, imrec)

        hdulBr_small = fits.HDUList([hduBr_small])
        hdulBt_small = fits.HDUList([hduBt_small])
        hdulBp_small = fits.HDUList([hduBp_small])

        hdulBr_small.writeto(os.path.join(synop_outpath,'synopBr_small.fits'), overwrite=True)
        hdulBt_small.writeto(os.path.join(synop_outpath,'synopBt_small.fits'), overwrite=True)
        hdulBp_small.writeto(os.path.join(synop_outpath,'synopBp_small.fits'), overwrite=True)

        plot_synoptic_sources(smallSynopBr_img, 'B_r', synop_outpath, 'synopBr_small', config['cr'], table_hdu.data, save=True) 
        plot_synoptic_sources(smallSynopBt_img, 'B_t', synop_outpath, 'synopBt_small', config['cr'], table_hdu.data, save=True) 
        plot_synoptic_sources(smallSynopBp_img, 'B_p', synop_outpath, 'synopBp_small', config['cr'], table_hdu.data, save=True)  
             
        #TODO plot_synoptic_b3c script
        
    print('%s complete' %__file__)
