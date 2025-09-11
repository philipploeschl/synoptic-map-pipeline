###########################################################
###################### 0_drms_prep.py #####################
###########################################################

# This script prepares the necessary JSD files and creates the data series in DRMS.
# JSD file and runs the create_series command to create the required data series in 
# the local DRMS installation. 
# JSD file and data series creation can be indiviually toggled in config.py


import os, sys
import subprocess


def create_series(config, outpath, outname):
    if config.create_series:
        try:
            result = subprocess.run("create_series %s" %(outpath+outname), capture_output=True, text=True, shell=True)
            if config.verbose: 
                print(result.stdout)

        except FileNotFoundError:
            print("create_series %s failed: File not found" %(outname))


def main(config, session_folder):
        
    path_root      = os.path.normpath(os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/../../../"))
    path_templates = os.path.abspath(path_root + '/' + config.template_path)
    path_output    = os.path.join(session_folder, config.jsd_path)

    # PHI data series template
    if config.create_jsd_phi:

        with open(path_templates+'/'+config.phi_template) as f:
            phi_template = f.readlines()

        for i, line in enumerate(phi_template):
            if "Seriesname"  in line: phi_template[i] = phi_template[i] %config.data_series_phi
            if "Author"      in line: phi_template[i] = phi_template[i] %config.dataseries_owner
            if "Owner"       in line: phi_template[i] = phi_template[i] %config.dataseries_owner
            if "Keywords" in line:
                break

        outname = config.data_series_phi + ".jsd"
        with open (path_output + '/' + outname, 'w') as f:
            f.writelines(phi_template)

        create_series(config, path_output + '/', outname) 




    # Hiresmap data series template
    if config.create_jsd_hiresmap_phi:
        with open(path_templates+'/'+config.hiresmap_template) as f:
            hiresmap_template = f.readlines()

        for i, line in enumerate(hiresmap_template):
            if "Seriesname"  in line: hiresmap_template[i] = hiresmap_template[i] %config.data_series_jv2ts_phi
            if "Author"      in line: hiresmap_template[i] = hiresmap_template[i] %config.dataseries_owner
            if "Owner"       in line: hiresmap_template[i] = hiresmap_template[i] %config.dataseries_owner
            if "Description" in line: hiresmap_template[i] = hiresmap_template[i] %config.Btype 
            if "Data:"       in line: hiresmap_template[i] = hiresmap_template[i] %config.proj 
        
        outname = config.data_series_jv2ts_phi + ".jsd"
        with open (path_output + '/' + outname, 'w') as f:
            f.writelines(hiresmap_template)

        create_series(config, path_output + '/', outname)


    # Hiresmap data series template
    if config.create_jsd_hiresmap_hmi:
        with open(path_templates+'/'+config.hiresmap_template) as f:
            hiresmap_template = f.readlines()

        for i, line in enumerate(hiresmap_template):
            if "Seriesname"  in line: hiresmap_template[i] = hiresmap_template[i] %config.data_series_jv2ts_hmi
            if "Author"      in line: hiresmap_template[i] = hiresmap_template[i] %config.dataseries_owner
            if "Owner"       in line: hiresmap_template[i] = hiresmap_template[i] %config.dataseries_owner
            if "Description" in line: hiresmap_template[i] = hiresmap_template[i] %config.Btype 
            if "Data:"       in line: hiresmap_template[i] = hiresmap_template[i] %config.proj 
        
        outname = config.data_series_jv2ts_hmi + ".jsd"
        with open (path_output + '/' + outname, 'w') as f:
            f.writelines(hiresmap_template)

        create_series(config, path_output + '/', outname)



    # Remap data series template
    if config.create_jsd_remap_phi:
        with open(path_templates+'/'+config.remap_template) as f:
            remap_template = f.readlines()

        for i, line in enumerate(remap_template):
            if "Seriesname"  in line: remap_template[i] = remap_template[i] %config.data_series_remap_phi
            if "Author"      in line: remap_template[i] = remap_template[i] %config.dataseries_owner
            if "Owner"       in line: remap_template[i] = remap_template[i] %config.dataseries_owner
            if "Description" in line: remap_template[i] = remap_template[i] %config.Btype 
            if "Data:"       in line: remap_template[i] = remap_template[i] %config.proj 
        
        outname = config.data_series_remap_phi + ".jsd"

        with open (path_output + '/' + outname, 'w') as f:
            f.writelines(remap_template)

        create_series(config, path_output + '/', outname)


    # Remap data series template
    if config.create_jsd_remap_hmi:
        with open(path_templates+'/'+config.remap_template) as f:
            remap_template = f.readlines()
            
        for i, line in enumerate(remap_template):
            if "Seriesname"  in line: remap_template[i] = remap_template[i] %config.data_series_remap_hmi
            if "Author"      in line: remap_template[i] = remap_template[i] %config.dataseries_owner
            if "Owner"       in line: remap_template[i] = remap_template[i] %config.dataseries_owner
            if "Description" in line: remap_template[i] = remap_template[i] %config.Btype 
            if "Data:"       in line: remap_template[i] = remap_template[i] %config.proj 
    
        outname = config.data_series_remap_hmi + ".jsd"
        with open (path_output + '/' + outname, 'w') as f:
            f.writelines(remap_template)

        create_series(config, path_output + '/', outname)


    # Synoptic data series template
    if config.create_jsd_synoptic:
        with open(path_templates+'/'+config.synoptic_template) as f:
            synoptic_template = f.readlines()    

        for i, line in enumerate(synoptic_template):    
            if "Seriesname"  in line: synoptic_template[i] = synoptic_template[i] %config.data_series_synop
            if "Author"      in line: synoptic_template[i] = synoptic_template[i] %config.dataseries_owner
            if "Owner"       in line: synoptic_template[i] = synoptic_template[i] %config.dataseries_owner
            if "Description" in line: synoptic_template[i] = synoptic_template[i] %config.Btype 
            if "Data: synop" in line: synoptic_template[i] = synoptic_template[i] %config.proj 

        outname = config.data_series_synop + ".jsd"
        with open (path_output + '/' + outname, 'w') as f:
            f.writelines(synoptic_template)

        create_series(config, path_output + '/', outname)


    # Synoptic Mr polfil data series template
    if config.proj == "Mr" and config.create_jsd_polfil:
        with open(path_templates+'/'+config.polfil_template) as f:
            synoptic_mr_polfil_template = f.readlines()

        for i, line in enumerate(synoptic_mr_polfil_template):
            if "Seriesname"  in line: synoptic_mr_polfil_template[i] = synoptic_mr_polfil_template[i] %config.data_series_polfil
            if "Author"      in line: synoptic_mr_polfil_template[i] = synoptic_mr_polfil_template[i] %config.dataseries_owner
            if "Owner"       in line: synoptic_mr_polfil_template[i] = synoptic_mr_polfil_template[i] %config.dataseries_owner
            if "Keywords" in line: break

        outname = config.data_series_polfil + ".jsd"
        with open (path_output + '/' + outname, 'w') as f:
            f.writelines(synoptic_mr_polfil_template)

        create_series(config, path_output + '/', outname)


if __name__ == "__main__":
    main()
