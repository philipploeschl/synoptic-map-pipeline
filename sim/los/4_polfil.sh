#!/bin/bash

path=$1
cr=2240

echo -e "\nIngesting $path/synopMr.fits .."
set_info -c ds=mps_loeschl.synoptic_mr CR=$cr synopMr=$path/synopMr.fits

echo -e "\nPole filling..."
jpolfil in=mps_loeschl.synoptic_mr[2240] out=mps_loeschl.synoptic_mr_polfil LAT0=65 LATFIL=75

polpath=$(show_info -P mps_loeschl.synoptic_mr_polfil[2240] | grep /SUM)
polfile=$(ls -a $polpath | grep ".fits")

nfile=${#polfile}
nfits=5
((n=$nfile-$nfits))

echo -e "\nCopying files..."
cp $polpath/$polfile $path/

echo "done"