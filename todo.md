This is currently abused as a todo list


# Merge ToDo List
## Release blockers
- confirm that all new parameters have default values in config.py

## Misc
- throw out everything that's obsolete from this list
- update readme.md

## General
- implement smaller intermediate reprojection dimensions
- merge diagnostics
- fix and merge data planning

## diagnostics
- HMI only functionality
- Add HMI 4h stripes to the fits table! -> Francisca 

## PHI_DRMS_INTERFACE
- add new WCS check (see gherardo email)
  - PWCSCORR= '1       '           / WCS entries corrected 1 = yes
  - discard dataset if not 1

## hmisynoptic.py
  - remove CarringtonTime() dependencies?

## Data Selection
## Notes
- link to drms installation
- link to synotpic map c code
- header excel sheet
- epxlain bash script drms commands and default parameters


# TODO

- phi_drms_interface.py
  - figure out why some files are leftover in the duplicate filtering. possibly first and last

- DATA SELECTION: 
  - maybe throw out CR check in hmiphisynoptic instead of overwriting it
  - or just give it +-1 CR as margin  
    - this won't work with overlapping HMI timestamps, as they will just be sorted next to each other and averaged together
    - sort by real CR and CRLN?
    - use accurate decimal CR?
  - DRMS_TIMESTRING: The problem is triggered by HMI wrapping around from 0 to 360, so essentially cases between two Carrington Rotations, where the high HMI longitudes are already from the next CR. The routines that select the fastest combinations for a given CR and create the timestring are affected by this as I currently only look for jumps between instruments. This will need an additional check for time jumps within HMI.
  
- Something's wrong with the instrument selection, causing the single instrument cases
- CR 2295 edge case
  -  PHI crosses in front of HMI giving the HMI/PHI/HMI/PHI transition in the middle
     -  2025-03-13T16:00:00	212.468880	PHI
        2025-03-13T15:59:59	212.857771	HMI
        2025-03-13T12:00:00	214.326613	PHI
        2025-03-13T11:59:59	215.054378	HMI
        2025-03-13T08:00:00	216.189384	PHI
        2025-03-13T07:59:59	217.250968	HMI

  -  HMI period wrongly enters NEXT CR!
  -  HMI from next period catches up with itself (possibly caused by cadence resolution!)
  -  HMI catching itself produces unexpected/unaccounted date transition
     -  2025-03-03T07:59:59	349.014711	HMI
        2025-03-30T11:59:59	350.909856	HMI


DRMS_TAI_TIMESTRING_HMI
2025.03.29_20:00:36_TAI-2025.03.13_08:00:36_TAI,2025.03.25_00:00:36_TAI-2025.03.29_16:00:36_TAI

DRMS_TAI_TIMESTRING_PHI
2025.03.13_12:00:37_TAI-2025.03.30_08:00:37_TAI


2025-03-13T16:00:00	212.468880	PHI
2025-03-13T15:59:59	212.857771	HMI
2025-03-13T12:00:00	214.326613	PHI
2025-03-13T11:59:59	215.054378	HMI
2025-03-13T08:00:00	216.189384	PHI
2025-03-13T07:59:59	217.250968	HMI


UTC	CARRINGTON_LONGITUDE	SOURCE
2025-03-29T15:59:59	1.901901	HMI
2025-03-29T15:59:59	1.901901	HMI
2025-03-29T15:59:59	1.901901	HMI
2025-03-29T15:59:59	1.901901	HMI
2025-03-29T11:59:59	4.100245	HMI
2025-03-29T11:59:59	4.100245	HMI
2025-03-29T07:59:59	6.298568	HMI
2025-03-29T07:59:59	6.298568	HMI
2025-03-29T03:59:59	8.496869	HMI
2025-03-29T03:59:59	8.496869	HMI
2025-03-28T23:59:59	10.695149	HMI
2025-03-28T23:59:59	10.695149	HMI
2025-03-28T19:59:59	12.893409	HMI
2025-03-28T19:59:59	12.893409	HMI
2025-03-28T19:59:59	12.893409	HMI
2025-03-28T15:59:59	15.091647	HMI
2025-03-28T15:59:59	15.091647	HMI
2025-03-28T11:59:59	17.289865	HMI
2025-03-28T11:59:59	17.289865	HMI
2025-03-28T07:59:59	19.488062	HMI
2025-03-28T07:59:59	19.488062	HMI
2025-03-28T03:59:59	21.686239	HMI
2025-03-28T03:59:59	21.686239	HMI
2025-03-27T23:59:59	23.884396	HMI
2025-03-27T23:59:59	23.884396	HMI
2025-03-27T23:59:59	23.884396	HMI
2025-03-27T19:59:59	26.082532	HMI
2025-03-27T19:59:59	26.082532	HMI
2025-03-27T15:59:59	28.280649	HMI
2025-03-27T15:59:59	28.280649	HMI
2025-03-27T11:59:59	30.478746	HMI
2025-03-27T11:59:59	30.478746	HMI
2025-03-27T07:59:59	32.676822	HMI
2025-03-27T07:59:59	32.676822	HMI
2025-03-27T03:59:59	34.874880	HMI
2025-03-27T03:59:59	34.874880	HMI
2025-03-27T03:59:59	34.874880	HMI
2025-03-26T23:59:59	37.072917	HMI
2025-03-26T23:59:59	37.072917	HMI
2025-03-26T19:59:59	39.270936	HMI
2025-03-26T19:59:59	39.270936	HMI
2025-03-26T15:59:59	41.468935	HMI
2025-03-26T15:59:59	41.468935	HMI
2025-03-26T11:59:59	43.666914	HMI
2025-03-26T11:59:59	43.666914	HMI
2025-03-26T07:59:59	45.864875	HMI
2025-03-26T07:59:59	45.864875	HMI
2025-03-26T07:59:59	45.864875	HMI
2025-03-26T03:59:59	48.062816	HMI
2025-03-26T03:59:59	48.062816	HMI
2025-03-25T23:59:59	50.260739	HMI
2025-03-25T23:59:59	50.260739	HMI
2025-03-25T19:59:59	52.458643	HMI
2025-03-25T19:59:59	52.458643	HMI
2025-03-25T15:59:59	54.656528	HMI
2025-03-25T15:59:59	54.656528	HMI
2025-03-25T11:59:59	56.854395	HMI
2025-03-25T11:59:59	56.854395	HMI
2025-03-25T11:59:59	56.854395	HMI
2025-03-25T07:59:59	59.052242	HMI
2025-03-25T07:59:59	59.052242	HMI
2025-03-25T03:59:59	61.250072	HMI
2025-03-25T03:59:59	61.250072	HMI
2025-03-24T23:59:59	63.447883	HMI
2025-03-30T08:00:00	64.700556	PHI
2025-03-30T04:00:00	65.824302	PHI
2025-03-30T00:00:00	66.949109	PHI
2025-03-30T00:00:00	66.949109	PHI
2025-03-29T20:00:00	68.075351	PHI
2025-03-29T16:00:00	69.203400	PHI
2025-03-29T12:00:00	70.333626	PHI
2025-03-29T08:00:00	71.466398	PHI
2025-03-29T04:00:00	72.602080	PHI
2025-03-29T00:00:00	73.741034	PHI
2025-03-28T20:00:00	74.883615	PHI
2025-03-28T20:00:00	74.883615	PHI
2025-03-28T16:00:00	76.030174	PHI
2025-03-28T12:00:00	77.181056	PHI
2025-03-28T08:00:00	78.336598	PHI
2025-03-28T04:00:00	79.497130	PHI
2025-03-28T00:00:00	80.662973	PHI
2025-03-27T20:00:00	81.834441	PHI
2025-03-27T20:00:00	81.834441	PHI
2025-03-27T16:00:00	83.011837	PHI
2025-03-27T12:00:00	84.195455	PHI
2025-03-27T08:00:00	85.385579	PHI
2025-03-27T04:00:00	86.582480	PHI
2025-03-27T00:00:00	87.786422	PHI
2025-03-26T20:00:00	88.997653	PHI
2025-03-26T20:00:00	88.997653	PHI
2025-03-26T16:00:00	90.216414	PHI
2025-03-26T12:00:00	91.442930	PHI
2025-03-26T08:00:00	92.677417	PHI
2025-03-26T04:00:00	93.920078	PHI
2025-03-26T04:00:00	93.920078	PHI
2025-03-26T00:00:00	95.171102	PHI
2025-03-25T20:00:00	96.430669	PHI
2025-03-25T16:00:00	97.698944	PHI
2025-03-25T12:00:00	98.976081	PHI
2025-03-25T12:00:00	98.976081	PHI
2025-03-25T08:00:00	100.262223	PHI
2025-03-25T04:00:00	101.557497	PHI
2025-03-25T00:00:00	102.862024	PHI
2025-03-25T00:00:00	102.862024	PHI
2025-03-24T20:00:00	104.175908	PHI
2025-03-24T16:00:00	105.499245	PHI
2025-03-24T12:00:00	106.832119	PHI
2025-03-24T12:00:00	106.832119	PHI
2025-03-24T08:00:00	108.174603	PHI
2025-03-24T04:00:00	109.526758	PHI
2025-03-24T00:00:00	110.888638	PHI
2025-03-24T00:00:00	110.888638	PHI
2025-03-23T20:00:00	112.260284	PHI
2025-03-23T16:00:00	113.641728	PHI
2025-03-23T16:00:00	113.641728	PHI
2025-03-23T12:00:00	115.032994	PHI
2025-03-23T08:00:00	116.434096	PHI
2025-03-23T04:00:00	117.845040	PHI
2025-03-23T04:00:00	117.845040	PHI
2025-03-23T00:00:00	119.265823	PHI
2025-03-22T20:00:00	120.696436	PHI
2025-03-22T20:00:00	120.696436	PHI
2025-03-22T16:00:00	122.136860	PHI
2025-03-22T12:00:00	123.587070	PHI
2025-03-22T12:00:00	123.587070	PHI
2025-03-22T08:00:00	125.047036	PHI
2025-03-22T04:00:00	126.516720	PHI
2025-03-22T00:00:00	127.996077	PHI
2025-03-22T00:00:00	127.996077	PHI
2025-03-21T20:00:00	129.485059	PHI
2025-03-21T16:00:00	130.983611	PHI
2025-03-21T16:00:00	130.983611	PHI
2025-03-21T12:00:00	132.491673	PHI
2025-03-21T12:00:00	132.491673	PHI
2025-03-21T08:00:00	134.009182	PHI
2025-03-21T04:00:00	135.536070	PHI
2025-03-21T04:00:00	135.536070	PHI
2025-03-21T00:00:00	137.072263	PHI
2025-03-20T20:00:00	138.617686	PHI
2025-03-20T20:00:00	138.617686	PHI
2025-03-20T16:00:00	140.172261	PHI
2025-03-20T12:00:00	141.735903	PHI
2025-03-20T12:00:00	141.735903	PHI
2025-03-20T08:00:00	143.308530	PHI
2025-03-20T04:00:00	144.890052	PHI
2025-03-20T04:00:00	144.890052	PHI
2025-03-20T00:00:00	146.480380	PHI
2025-03-20T00:00:00	146.480380	PHI
2025-03-19T20:00:00	148.079422	PHI
2025-03-19T16:00:00	149.687084	PHI
2025-03-19T16:00:00	149.687084	PHI
2025-03-19T12:00:00	151.303271	PHI
2025-03-19T08:00:00	152.927886	PHI
2025-03-19T08:00:00	152.927886	PHI
2025-03-19T04:00:00	154.560831	PHI
2025-03-19T04:00:00	154.560831	PHI
2025-03-19T00:00:00	156.202007	PHI
2025-03-18T20:00:00	157.851314	PHI
2025-03-18T20:00:00	157.851314	PHI
2025-03-18T16:00:00	159.508652	PHI
2025-03-18T16:00:00	159.508652	PHI
2025-03-18T12:00:00	161.173920	PHI
2025-03-18T08:00:00	162.847015	PHI
2025-03-18T08:00:00	162.847015	PHI
2025-03-18T04:00:00	164.527838	PHI
2025-03-18T04:00:00	164.527838	PHI
2025-03-18T00:00:00	166.216285	PHI
2025-03-17T20:00:00	167.912255	PHI
2025-03-17T20:00:00	167.912255	PHI
2025-03-17T16:00:00	169.615646	PHI
2025-03-17T16:00:00	169.615646	PHI
2025-03-17T12:00:00	171.326357	PHI
2025-03-17T12:00:00	171.326357	PHI
2025-03-17T08:00:00	173.044287	PHI
2025-03-17T04:00:00	174.769334	PHI
2025-03-17T04:00:00	174.769334	PHI
2025-03-17T00:00:00	176.501400	PHI
2025-03-17T00:00:00	176.501400	PHI
2025-03-16T20:00:00	178.240383	PHI
2025-03-16T16:00:00	179.986185	PHI
2025-03-16T16:00:00	179.986185	PHI
2025-03-16T12:00:00	181.738708	PHI
2025-03-16T12:00:00	181.738708	PHI
2025-03-16T08:00:00	183.497854	PHI
2025-03-16T08:00:00	183.497854	PHI
2025-03-16T04:00:00	185.263526	PHI
2025-03-16T04:00:00	185.263526	PHI
2025-03-16T00:00:00	187.035629	PHI
2025-03-15T20:00:00	188.814066	PHI
2025-03-15T20:00:00	188.814066	PHI
2025-03-15T16:00:00	190.598745	PHI
2025-03-15T16:00:00	190.598745	PHI
2025-03-15T12:00:00	192.389572	PHI
2025-03-15T12:00:00	192.389572	PHI
2025-03-15T08:00:00	194.186455	PHI
2025-03-15T04:00:00	195.989303	PHI
2025-03-15T04:00:00	195.989303	PHI
2025-03-15T00:00:00	197.798027	PHI
2025-03-15T00:00:00	197.798027	PHI
2025-03-14T20:00:00	199.612536	PHI
2025-03-14T20:00:00	199.612536	PHI
2025-03-14T16:00:00	201.432743	PHI
2025-03-14T16:00:00	201.432743	PHI
2025-03-14T12:00:00	203.258562	PHI
2025-03-14T12:00:00	203.258562	PHI
2025-03-14T08:00:00	205.089908	PHI
2025-03-14T04:00:00	206.926695	PHI
2025-03-14T04:00:00	206.926695	PHI
2025-03-14T00:00:00	208.768840	PHI
2025-03-14T00:00:00	208.768840	PHI
2025-03-13T20:00:00	210.616263	PHI
2025-03-13T20:00:00	210.616263	PHI
2025-03-13T16:00:00	212.468880	PHI
2025-03-13T16:00:00	212.468880	PHI
2025-03-13T15:59:59	212.857771	HMI
2025-03-13T12:00:00	214.326613	PHI
2025-03-13T11:59:59	215.054378	HMI
2025-03-13T08:00:00	216.189384	PHI
2025-03-13T07:59:59	217.250968	HMI
2025-03-13T03:59:59	219.447541	HMI
2025-03-13T03:59:59	219.447541	HMI
2025-03-12T23:59:59	221.644096	HMI
2025-03-12T23:59:59	221.644096	HMI
2025-03-12T19:59:59	223.840634	HMI
2025-03-12T19:59:59	223.840634	HMI
2025-03-12T19:59:59	223.840634	HMI
2025-03-12T15:59:59	226.037155	HMI
2025-03-12T15:59:59	226.037155	HMI
2025-03-12T11:59:59	228.233658	HMI
2025-03-12T11:59:59	228.233658	HMI
2025-03-12T07:59:59	230.430143	HMI
2025-03-12T07:59:59	230.430143	HMI
2025-03-12T03:59:59	232.626611	HMI
2025-03-12T03:59:59	232.626611	HMI
2025-03-11T23:59:59	234.823062	HMI
2025-03-11T23:59:59	234.823062	HMI
2025-03-11T23:59:59	234.823062	HMI
2025-03-11T19:59:59	237.019496	HMI
2025-03-11T19:59:59	237.019496	HMI
2025-03-11T15:59:59	239.215911	HMI
2025-03-11T15:59:59	239.215911	HMI
2025-03-11T11:59:59	241.412310	HMI
2025-03-11T11:59:59	241.412310	HMI
2025-03-11T07:59:59	243.608691	HMI
2025-03-11T07:59:59	243.608691	HMI
2025-03-11T03:59:59	245.805054	HMI
2025-03-11T03:59:59	245.805054	HMI
2025-03-11T03:59:59	245.805054	HMI
2025-03-10T23:59:59	248.001400	HMI
2025-03-10T23:59:59	248.001400	HMI
2025-03-10T19:59:59	250.197728	HMI
2025-03-10T19:59:59	250.197728	HMI
2025-03-10T15:59:59	252.394039	HMI
2025-03-10T15:59:59	252.394039	HMI
2025-03-10T11:59:59	254.590333	HMI
2025-03-10T11:59:59	254.590333	HMI
2025-03-10T07:59:59	256.786609	HMI
2025-03-10T07:59:59	256.786609	HMI
2025-03-10T03:59:59	258.982867	HMI
2025-03-10T03:59:59	258.982867	HMI
2025-03-10T03:59:59	258.982867	HMI
2025-03-09T23:59:59	261.179108	HMI
2025-03-09T23:59:59	261.179108	HMI
2025-03-09T19:59:59	263.375332	HMI
2025-03-09T19:59:59	263.375332	HMI
2025-03-09T15:59:59	265.571537	HMI
2025-03-09T15:59:59	265.571537	HMI
2025-03-09T11:59:59	267.767726	HMI
2025-03-09T11:59:59	267.767726	HMI
2025-03-09T07:59:59	269.963897	HMI
2025-03-09T07:59:59	269.963897	HMI
2025-03-09T07:59:59	269.963897	HMI
2025-03-09T03:59:59	272.160051	HMI
2025-03-09T03:59:59	272.160051	HMI
2025-03-08T23:59:59	274.356187	HMI
2025-03-08T23:59:59	274.356187	HMI
2025-03-08T19:59:59	276.552306	HMI
2025-03-08T19:59:59	276.552306	HMI
2025-03-08T15:59:59	278.748407	HMI
2025-03-08T15:59:59	278.748407	HMI
2025-03-08T11:59:59	280.944491	HMI
2025-03-08T11:59:59	280.944491	HMI
2025-03-08T11:59:59	280.944491	HMI
2025-03-08T07:59:59	283.140557	HMI
2025-03-08T07:59:59	283.140557	HMI
2025-03-08T03:59:59	285.336607	HMI
2025-03-08T03:59:59	285.336607	HMI
2025-03-07T23:59:59	287.532639	HMI
2025-03-07T23:59:59	287.532639	HMI
2025-03-07T19:59:59	289.728653	HMI
2025-03-07T19:59:59	289.728653	HMI
2025-03-07T15:59:59	291.924651	HMI
2025-03-07T15:59:59	291.924651	HMI
2025-03-07T15:59:59	291.924651	HMI
2025-03-07T11:59:59	294.120631	HMI
2025-03-07T11:59:59	294.120631	HMI
2025-03-07T07:59:59	296.316594	HMI
2025-03-07T07:59:59	296.316594	HMI
2025-03-07T03:59:59	298.512540	HMI
2025-03-07T03:59:59	298.512540	HMI
2025-03-06T23:59:59	300.708469	HMI
2025-03-06T23:59:59	300.708469	HMI
2025-03-06T19:59:59	302.904380	HMI
2025-03-06T19:59:59	302.904380	HMI
2025-03-06T19:59:59	302.904380	HMI
2025-03-06T15:59:59	305.100275	HMI
2025-03-06T15:59:59	305.100275	HMI
2025-03-06T11:59:59	307.296153	HMI
2025-03-06T11:59:59	307.296153	HMI
2025-03-06T07:59:59	309.492014	HMI
2025-03-06T07:59:59	309.492014	HMI
2025-03-06T03:59:59	311.687858	HMI
2025-03-06T03:59:59	311.687858	HMI
2025-03-05T23:59:59	313.883685	HMI
2025-03-05T23:59:59	313.883685	HMI
2025-03-05T23:59:59	313.883685	HMI
2025-03-05T19:59:59	316.079496	HMI
2025-03-05T19:59:59	316.079496	HMI
2025-03-05T15:59:59	318.275290	HMI
2025-03-05T15:59:59	318.275290	HMI
2025-03-05T11:59:59	320.471067	HMI
2025-03-05T11:59:59	320.471067	HMI
2025-03-05T07:59:59	322.666828	HMI
2025-03-05T07:59:59	322.666828	HMI
2025-03-05T03:59:59	324.862573	HMI
2025-03-05T03:59:59	324.862573	HMI
2025-03-05T03:59:59	324.862573	HMI
2025-03-04T23:59:59	327.058301	HMI
2025-03-04T23:59:59	327.058301	HMI
2025-03-04T19:59:59	329.254013	HMI
2025-03-04T19:59:59	329.254013	HMI
2025-03-04T15:59:59	331.449709	HMI
2025-03-04T15:59:59	331.449709	HMI
2025-03-04T11:59:59	333.645389	HMI
2025-03-04T11:59:59	333.645389	HMI
2025-03-04T07:59:59	335.841054	HMI
2025-03-04T07:59:59	335.841054	HMI
2025-03-04T07:59:59	335.841054	HMI
2025-03-04T03:59:59	338.036702	HMI
2025-03-04T03:59:59	338.036702	HMI
2025-03-03T23:59:59	340.232335	HMI
2025-03-03T23:59:59	340.232335	HMI
2025-03-03T19:59:59	342.427952	HMI
2025-03-03T19:59:59	342.427952	HMI
2025-03-03T15:59:59	344.623553	HMI
2025-03-03T15:59:59	344.623553	HMI
2025-03-03T11:59:59	346.819140	HMI
2025-03-03T11:59:59	346.819140	HMI
2025-03-03T11:59:59	346.819140	HMI
2025-03-03T07:59:59	349.014711	HMI
2025-03-30T11:59:59	350.909856	HMI
2025-03-30T11:59:59	350.909856	HMI
2025-03-30T11:59:59	350.909856	HMI
2025-03-30T07:59:59	353.108309	HMI
2025-03-30T07:59:59	353.108309	HMI
2025-03-30T03:59:59	355.306740	HMI
2025-03-30T03:59:59	355.306740	HMI
2025-03-29T23:59:59	357.505148	HMI
2025-03-29T23:59:59	357.505148	HMI
2025-03-29T19:59:59	359.703536	HMI

## Keywords
- CRLN_OBS now [-180,+180] -> BUG in header, but pipeline handles both now


## Pipeline 
- change --session argument to --output
- check if automatic session creation still uses config.cr
- check how session creation works vs output_path

## DRMS prep
- add retention file parameters for each template to config

## HMI PHI Synoptic
- try forcing start from half carrington rotation eg 2283.5 and check if it works
  - this will probably need a custom plot to get the x axis right

## PHI DRMS Interface


## M720 Processing


## Data selection output
- add CR start and end dates to the csv output
- DONE 2252	2022-01-04T10:55:49	25.79	0.934653	2022.01.11_22:56:26_TAI-2022.01.30_06:56:25_TAI,2022.01.04_10:56:26_TAI-2022.01.11_18:56:26_TAI	2022.01.29_02:56:25_TAI-2022.01.30_06:56:25_TAI
  - DONE why is the 2nd HMI string before the first string? -> ordered by clon not time
- DONE 2254: why is htere no PHI data -> 4h cadence eats the bit of PHI data


## Data selection 
- DONE add start time of phi obsevation and build the ET around that
- add data selection not depending on newest observation date but predetermined data set from config
- change CRXXXX txt output to be usable for phi/hmi data selection like in the yt video to the output.pdf

- plan for refactor:
  - CR determination depends on majority of HMI data
  - input
    - star date 
    - end date
    - cadence of new observation duration simulation to keep time reasonable (e.g. every 12h = 2 per day)
    - PHI observation cadence
    - HMI observation cadence
  - output
    - CR, CR start date, CR end date, observation start date, observation duration, solo distance, timestrings
    - CRXXX archive with detailed data selection in text files (current implementation)
      - one file for each simulated carrington observation
       


# FEATURES
## Updated session sandling
The session handling now is now done directly from the main wrapper synop_pipeline.py instead of drms_prep.py. This replaces the previous handover via session_path.txt

Full command:

   python synop_pipeline.py --config /path/to/config.yaml --session /path/to/previous/session_folder (optional)

  - required: config.yaml - uses default values for missing parameters or in case no config file is provided (defined in config.py)
  - optional: provide a previous session via --session


## Updated file structure

SYNOPTIC-MAP-PIPELINE
├─ DATA/
│  └─ DRMS/                  # JSD file templates
├─ OUTPUT/                   # set via config.output_path
│  └─ SESSION_FOLDER_NAME/
│     ├─ DATA/               # PHI data with updated headers for DRMS ingestion
│     ├─ JSD/                # JSD files for DRMS data series creation
│     ├─ LOGS/               # DRMS bash script log files
│     ├─ SCRIPTS/            # DRMS bash scripts
│     ├─ SYNOP/              # synoptic map output in .fits and .pdf
│     └─ config.yaml         # copy of config file of the last session rerun
└─ SRC/
   ├─ synop_pipeline.py
   ├─ data_selection.py
   ├─ CONFIG/
   │  ├─ config.py           # config parser class
   │  └─ example_config.yaml # example config, not read for defaults
   ├─ SYNOP/
   │  ├─ LOS/                # line-of-sight code
   │  │  ├─ drms_preparation.py
   │  │  ├─ m720s_drms_pipe.py
   │  │  ├─ phi_drms_interface.py
   │  │  └─ hmiphisynoptic.py
   │  └─ VECT/              # vector code (todo)
   └─ UTILS/
      ├─ solepehm.py        # ephemeris functions for hmiphisynoptic.py
      ├─ plots.py           # plotting scripts
      └─ utils.py           # formerly misc.py



## Known issues:
- Synoptic map processing cannot be aborted if launched together with run_bash_scripts()
- WARNING: hmisynoptic.py needs data at the same Carrington rotation number which will not always be the case for arbitrary combinations of PHI and HMI. There a common number is forced based on the majority of data. As a result nonsensical combinations like HMI from one year and PHI from another will currently work and not raise any errors! 
- UNTESTED: changing output_path to something outside of the project folder - try that at your own risk if necessary.
- awf_nlim = True has an issue that introduces NaNs into the synoptic map. I already have a lead but it's fairly low on the list since we can just use it without the limiter (set to False)
- python  path/synop_pipeline.py --config=/path/to/config.yaml
  - config path must be absolute or relative to synop_pipeline.py rather than relative to cwd


# TODO

- check if create_series paramters is still necessary after moving sesssion folder handling to the main wrapper. Will I ever run drms_prep.py without creating series now?

- remove previous scripts on rerun of m720s and phi_interface scripts
- consider phi duplicate detection safeguard

- force PHI start magnetogram into data combination (probably in optimisation task)


## Error Handling
- check if DRMS series exists in m720s_drms_pipe and phi_drms_interface and return an error if missing

## Quesitnos for Zhi-Chao
- should we use mps_production or can we define and arbitrary official nmae for us?
- how many parallel processes can we push into drms
- official synoptic map ml and mr remap and maybe the final synop series


## Data Selection
- How do we want to handle the output?
  - separate output folder?
  - skip session structure I guess

  
- provide some form of meta data that tracks the data used for each longitude
- data selection through file list that is provided wiht a start and end date and possibly respects exceptions
- get list of carrington rotation periods (start and end time) and find the fastest combination of data for each
- continuous scan of fastest combination independent of carrington rotation (with HMI data spanning 2 CR)

### Design:
- find best combination from existing data
    - from two continously running observations (HMI and PHI)
    - constrained within a single CR to improve HMI maps
    - arbitrary start and end dates crossing CR boundaries for fastest possible combination

- find best combination at defined cadence for a future time window for mission planning
- old design considers  equal spacing in carrington longitude, but in reality we will space in equal observation time increment
  
- refactor and rename carrington_observation_times and carrington_obsrevation_deg
  - clearer name
  - some of hte code is reused and can be outsourced into a function
  - confirm it's working as intended

- figure out why interp360 exists instead of using np.interp(period=360)

- remove obsolete LLD/RSW functionality
- maybe replace it with a list of available observatoin times if the observation cadence isn't constant

- CONTINUE WITH UNDERSTANDING carrington_observation_coverage 

  ### SPICE Kernel Setup
  - git clone --depth 1 https://repos.cosmos.esa.int/socci/scm/spice_kernels/solar-orbiter.git
  - link kernel directory via config.spice_kernel


## General
- check how synptic map pipeline handles noise outliers since PHI might come wiht sqrt(3) difference for onboard averaged data. make sure we don't lose data without noticing
- understand quality bits

### Log functionality
- set up proper logging using the python logging library
- top level log for verbose output of .py scripts
- possibly set up different levels of verbose output




### Session handling
- delete output scripts from previous run when reprocessing in an existing session
- figure out some form of processing history folder, maybe using the synop_pipeline.py log

- processing history - what do I need to save to reproduce the map?
  - config
  - file list of used phi data
  - hmi time stamps
  - phi time stamps
  - phi/hmi data selection
  - most of it can probably 
  - maybe add all this to a ./history/ folder 



## synop_pipeline.py
- check if /output can be replaced wiht an absolute path elsewhere
  

## 1_m720s_drms_pipe.py
- python script verbose output logging?
- add functionality for separate bash scripts created from nrt


## 2_phi_drms_interface.py
- option for .sh scripts only
- clean up old code
- python script verbose output logging?

- why is car_rot hard coded in calc_trec()?
  - logic doesn't seem to work in current implementation
  - Hard coding 2258 makes sure that the 0-86° data is assigned to 2258 instead of 2257.
  - not using this will result in missing data for lower longitudes for the 2258 test data



## 3_hmiphisynoptic.py
- change the data input to accept dedicated phi and hmi data series and do the T_REC remapping right there to allow for permanent production data series
  - this will require adaptations in 2_phi_drms_interface.py
  - no need to save phi.fits with updated header if it's possible to directly ADD keywords with set_info
    -> ingest and add keywords instead

    
- isolate adaptive weight function code to properly understand and document it again
- figure out why data in synoptic output is missing
- write synop.fits back into drms

- debug runtime warning on CR2258 synoptic processing:
  /scratch/slam/loeschl/dev/python/synop/sim/los/3_hmiphisynoptic.py:1087: RuntimeWarning: invalid value encountered in scalar divide
  synVal = sumfinal / wtfinal #nptsfinal          #float synVal = sumfinal / nptsfinal;

- identify los parameter for hmiphisynoptic.py
  - this seems to be tied to a discontinuied DRMS keyword FDRADIAL and only affects the noise thresholds of the synoptic map data selection
    if (radialFound)
          noiseLevel = noiseLevel * MIN(1 / cosrho, maxNoiseAdj);
  - noiseLevel seems to be an obsolete quantity that isn't used in the code anymore

- Adaptive Weight Function
  - code relies on images taken from the ecliptic
  - latitude specific weight function control needs to consider out of ecliptic observations
  - understand awf_lim and describe it properly
  - force uneven number for awf_nimg



## Notes on DRMS discussion with Zhi-Chao
- deleting a data series sets the retention of the stored data to 0, which will be purged during the next cleanup
- deleting a data series immediately deletes meta data

- cancelling DRMS modules with interrupt will CRASH the ENTIRE SYSTEM if it happens during any file ingestion process (e.g. module output writing back into data series)

- HMI.M_720s is updated daily at 7am. Data release lags behind a few days.
- HMI.M_720s_NRT available locally as mps_production.hmi_m_720s_nrt and updated hourly at hh:45
- see https://www2.mps.mpg.de/projects/seismo/GDC-SDO/sums-activity.htm

- DRMS metadata might be available but actual data will be corrupted if it was downloaded from Stanford during periods with GPFS filesystem problems at MPS


# NOTES

- identify los parameter for hmiphisynoptic.py
  - this seems to be tied to a discontinuied DRMS keyword FDRADIAL and only affects the noise thresholds of the synoptic map data selection
    if (radialFound)
          noiseLevel = noiseLevel * MIN(1 / cosrho, maxNoiseAdj);
  - noiseLevel seems to be an obsolete quantity that isn't used in the code anymore




