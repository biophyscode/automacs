#!/usr/bin/env python

"""
The write_continue_script function gets its own file to hold the BASH continue script and to avoid importing
the full automacs when writing cluster scripts.

! logging is to ../continue.log for now. it would be good to register this with automacs for later ...
"""

#---! tried and failed to hide this from "import amx"
_not_all = ['continue_script','write_continue_script_master']

import os,sys,json,re
from calls import gmx_get_machine_config

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

def interpret_walltimes(walltime):
	"""
	Turn walltime into a number of hours so we can gently stop gromacs.
	Torque uses dd:hh:mm:ss (or, more precisely "[[DD:]HH:]MM:SS")
		while SLURM uses dd-hh:mm:ss or just time in minutes.
	To disambiguate we interpret any walltime string or integer and return it in the most specific formats.
	"""
	regex_times = [
		'^(?P<days>\d{1,2}):(?P<hours>\d{1,2}):(?P<minutes>\d{1,2}):(?P<seconds>\d{1,2})$',
		'^(?P<hours>\d{1,2}):(?P<minutes>\d{1,2}):(?P<seconds>\d{1,2})$',
		'^(?P<minutes>\d{1,2}):(?P<seconds>\d{1,2})$',]
	times = dict([(k,None) for k in 'days hours minutes seconds'.split()])
	#---integers mean hours
	if type(walltime) in [int,float]:
		times['hours'] = float(walltime)
		for key in 'days minutes seconds'.split(): times[key] = 0.0
		maxhours = ('%f'%walltime).rstrip('0').rstrip('.')
	else:
		#---try several regexes
		for regex in regex_times:
			if re.match(regex,walltime):
				extract = re.match(regex,walltime).groupdict()
				times.update(**dict([(k,float(v)) for k,v in extract.items()]))
				times.update(**dict([(k,0.0) for k in times if k not in extract]))
				maxhours = times['days']*24.0+times['hours']+times['minutes']/60.+times['seconds']/60.**2
				break
	if any([v==None for v in times.values()]):
		raise Exception('times list is incomplete, hence we cannot interpret the walltime: %s'%times)
	#---formulate an unambiguous walltime string
	walltime_strict = '%(days)02d:%(hours)02d:%(minutes)02d:%(seconds)02d'%times
	return {'walltime':walltime_strict,'maxhours':maxhours}

def write_continue_script_master(script='script-continue.sh',
	machine_configuration=None,here=None,hostname=None,override=False,gmxpaths=None,**kwargs):
	"""
	Uses a template in amx/procedures to write a bash continuation script.
	"""
	this_script = str(continue_script)
	#---remote import to avoid large packages
	import makeface
	#---we pass gmxpaths through so we do not need to load modules twice
	if not gmxpaths:
		#get_gmx_paths = makeface.import_remote('amx/gromacs/calls.py')
		#import ipdb;ipdb.set_trace()#['gmx_get_paths']
		#from calls import gmx_get_paths
		#---the gmx_get_paths function is an explicit import in amx.__init__._import_instruct
		gmxpaths = gmx_get_paths(hostname=hostname,override=override)
	if not machine_configuration: machine_configuration = gmx_get_machine_config()
	#---CONTINUATION DEFAULTS HERE
	settings = {
		'maxhours':interpret_walltimes(machine_configuration.get('walltime',24))['maxhours'],
		'extend':machine_configuration.get('extend',1000000),
		'start_part':1,
		'tpbconv':gmxpaths['tpbconv'],
		'mdrun':gmxpaths['mdrun'],
		'grompp':gmxpaths['grompp'],
		'maxwarn':0}
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
	this_script = re.sub('#---SETTINGS OVERRIDES HERE\n',setting_text,this_script,re.M)
	#---most calls come from amx.cli.write_continue_script which has the state during a regular run
	if here: pass
	#---calls to e.g. cluster lack the state so we read it manually and avoid importing amx
	elif not os.path.isfile('state.json'): raise Exception('write_continue_script requires state.json')
	else: here = json.load(open('state.json'))['here']
	with open(here+script,'w') as fp: fp.write(this_script)
	os.chmod(here+script,0o744)
	return here+script
