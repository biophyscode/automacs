#!/usr/bin/env python

"""
The write_continue_script function gets its own file to hold the BASH continue script and to avoid importing
the full automacs when writing cluster scripts.

! logging is to ../continue.log for now. it would be good to register this with automacs for later ...
"""

#---! tried and failed to hide this from "import amx"
_not_all = ['continue_script','write_continue_script_master']

import os,sys,json,re
from calls import get_machine_config

continue_script = """#!/bin/bash

#---SETTINGS: nprocs, maxhours (hours), extend (ps), tpbconv, mdrun
#---SETTINGS OVERRIDES HERE

#---find last CPT
PRUN=0
for file in md.part*.cpt
do
if [ $(echo ${file:7:4} | sed 's/^0*//') -gt $PRUN ]; 
then PRUN=$(echo ${file:7:4} | sed 's/^0*//')
fi
done
NRUN=$(($PRUN+1))

#---log to standard log
step=$(pwd | sed -r 's/.+\/(.+)/\1/')
metalog="../continuation.log"
echo "[STATUS] continuing simulation from part $PRUN in $step"
echo "[STATUS] logging to $metalog"
echo "[STATUS] running ... "

#---extend TPR
if [[ ! -z $EXTEND  ]]; then EXTEND_FLAG="-extend $EXTEND";
elif [[ ! -z $UNTIL ]]; then EXTEND_FLAG="-until $UNTIL";
else EXTEND_FLAG="-nsteps -1"; fi
log=$(printf tpbconv-%04d $NRUN)
cmd="$TPBCONV $EXTEND_FLAG -s $(printf md.part%04d.tpr $PRUN) -o $(printf md.part%04d.tpr $NRUN)"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec

#---continue simulation
log=$(printf mdrun-%04d $NRUN)
cmd="$MDRUN -s $(printf md.part%04d.tpr $NRUN) \
-cpi $(printf md.part%04d.cpt $PRUN) \
-cpo $(printf md.part%04d.cpt $NRUN) \
-g $(printf md.part%04d.log $NRUN) \
-e $(printf md.part%04d.edr $NRUN) \
-o $(printf md.part%04d.trr $NRUN) \
-x $(printf md.part%04d.xtc $NRUN) \
-c $(printf md.part%04d.gro $NRUN) -maxh $MAXHOURS"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec
echo "[STATUS] done continuation stage"
"""

def write_continue_script_master(script='script-continue.sh',
	machine_configuration=None,here=None,hostname=None,override=False,**kwargs):
	"""
	Uses a template in amx/procedures to write a bash continuation script.
	"""
	this_script = str(continue_script)
	#---remote import to avoid large packages
	import makeface
	get_gmx_paths = makeface.import_remote('amx/calls')['get_gmx_paths']
	gmxpaths = get_gmx_paths(hostname=hostname,override=override)
	#---CONTINUATION DEFAULTS HERE
	settings = {
		'maxhours':24,
		'extend':1000000,
		'start_part':1,
		'tpbconv':gmxpaths['tpbconv'],#state['gmxpaths']['tpbconv'],
		'mdrun':gmxpaths['mdrun'],#state['gmxpaths']['mdrun'],
		'grompp':gmxpaths['grompp'],#state['gmxpaths']['grompp'],
		'maxwarn':0}
	if not machine_configuration: machine_configuration = get_machine_config()
	settings_keys = list(settings.keys())
	#---cluster may use an alternate mdrun
	if 'mdrun_command' in machine_configuration: settings['mdrun'] = machine_configuration['mdrun_command']
	if 'ppn' in machine_configuration and 'nnodes'in machine_configuration:
		settings['nprocs'] = machine_configuration['ppn']*machine_configuration['nnodes']
		#---always define nprocs first in case there is an alternate mdrun_command
		settings_keys.insert(0,'nprocs')
	settings.update(**kwargs)
	setting_text = '\n'.join([
		str(key.upper())+'='+('"' if type(settings[key])==str else '')+str(settings[key])+
			('"' if type(settings[key])==str else '') for key in settings_keys])
	modules = machine_configuration.get('modules',None)
	if modules:
		modules = [modules] if type(modules)==str else modules
		#---if gromacs is in any of the modules we try to unload gromacs
		if any([re.search('gromacs',i) for i in modules]):
			setting_text += '\nmodule unload gromacs'
		for m in modules: setting_text += '\nmodule load %s'%m
	#---add settings overrides here
	this_script = re.sub('#---SETTINGS OVERRIDES HERE\n',setting_text,this_script,flags=re.M)
	#---most calls come from amx.cli.write_continue_script which has the state during a regular run
	if here: pass
	#---calls to e.g. cluster lack the state so we read it manually and avoid importing amx
	elif not os.path.isfile('state.json'): raise Exception('write_continue_script requires state.json')
	else: here = json.load(open('state.json'))['here']
	with open(here+script,'w') as fp: fp.write(this_script)
	os.chmod(here+script,0o744)
	return here+script
