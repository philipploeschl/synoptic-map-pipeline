import os
from astropy.io import fits
from utils.diagnostics import diagnostics


STATUS_OK = 0

def main(config, session_folder):

    synop_outpath = os.path.join(session_folder, config.synop_path)
    synop_hdul = fits.open(synop_outpath + "synopBr.fits")

    synop_img  = synop_hdul[0].data
    table_data = synop_hdul[1].data
    carrington_number = synop_hdul[0].header['CAR_ROT']
    
    diagnostics(synop_img, table_data, synop_outpath, carrington_number, config)

    return STATUS_OK