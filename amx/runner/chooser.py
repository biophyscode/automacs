#!/usr/bin/env python

"""
This chooser code exposes the `prep` and `go` functions to the command-line.
It uses an experiment module to interpret the experiments and sends the result to an execution module.
Both experiment and execution modules can be overloaded.
"""

from __future__ import print_function

__all__ = ['prep','go','clean']

import os,sys
import ortho

### MODULE ROUTING

# import the experiment handler
experiment_handler_path = ortho.conf.get('experiment_handler',None)
# custom experiment handler can be specified in config.json and remotely imported
if experiment_handler_path:
	experiment_handler = ortho.importer(experiment_handler_path,verbose=True)	
	collect_experiments = experiment_handler['collect_experiments']
# standard import for the local module so it can use ortho
else: from .experiments import collect_experiments

# import the experiment runners currently hardcoded
from .execution import runner

### GENERIC CLI (needed by go)

import shutil,os,sys,glob,re

def cleanup(sure=False):
	"""
	Clean files from the current directory.
	"""
	print('status','cleaning this simulation')
	config = ortho.conf
	if 'cleanup' not in config: raise Exception('configuration is missing cleanup instructions')
	fns = []
	#! special handling for links
	if os.path.islink('expt.json'): 
		os.unlink('expt.json')
	for pat in config['cleanup']: 
		if isinstance(pat,dict):
			if set(pat.keys())=={'regex'}:
				fns.extend([i for i in glob.glob('*') if re.match(pat['regex'],i)])
			else: raise Exception('unclear cleanup rule: %s'%str(pat))
		else: fns.extend(glob.glob(pat))
	if not sure: print('note','cleaning: %s'%', '.join(fns))
	from ortho import confirm
	if sure or confirm('okay to remove','confirm'):
		for fn in fns: 
			if os.path.isfile(fn): os.remove(fn)
			else: shutil.rmtree(fn)
	# we have to remove amx to reload the state in case we just cleaned it and it lingers in memory
	import amx
	del sys.modules['amx']

def clean(sure=False): cleanup(sure=sure)

### CHOOSE EXPERIMENTS

def experiment(procname,run=False,get=False):
	"""
	Prepare an experiment from inputs specified by the config.
	There are two modes: a "metarun" or a single program.
	"""
	collected = collect_experiments(conf=ortho.conf)
	experiments,sources = [collected[k] for k in ['experiments','sources']]
	if procname not in experiments: raise Exception('cannot find experiment %s'%procname)
	else: experiment = experiments[procname]
	# save metadata for later, including the experiment name and location
	metadata = dict(experiment_name=procname,experiment_source=sources[procname],
		cwd=os.path.dirname(sources[procname]))
	#! 
	if get: return experiment
	# send the experiment to the runner
	else: runner(experiment,meta=metadata,run=run)

def prep(procname=None,terse=False,json=False):
	"""Prepare an experiment or show the list."""
	import json as JSON
	if procname==None: 
		experiments = collect_experiments(conf=ortho.conf)
		if terse: ortho.treeview(
			dict(experiments=experiments['experiments'].keys()))
		elif json:
			# format expected by interface.simulator.views.detail_simulation
			# we dump sources and experiments
			print('json:\n%s'%JSON.dumps(experiments))
		else: ortho.treeview(dict(experiments=experiments))
	else: experiment(procname=procname,run=False)

def go(procname,clean=False): 
	"""Typical method for running an experiment."""
	if clean: cleanup(sure=True)
	experiment(procname,run=True)
