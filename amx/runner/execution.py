#!/usr/bin/env python

from __future__ import print_function
import json,shutil,os

### CLASSIFY EXPERIMENTS

# use keys to classify experiment styles
experiment_classifier = [
	({'settings','params','tags','script','cwd'},'run'),]

def classify_experiment(expt):
	"""
	Use keys to classify the experiment.
	"""
	matches = []
	for keys,name in experiment_classifier:
		if keys==set(expt.keys()): matches.append(name)
	matches = list(set(matches))
	if len(matches)==0: raise Exception('failed to classify experiment %s'%expt)
	elif len(matches)>1: raise Exception('matched experiment %s to multiple styles %s'%(expt,matches))
	else: return matches[0]

### PREPARE EXPERIMENTS

def prep_step(expt,meta,no=None):
	"""
	Prepare a single step in an experiment.
	"""
	data = dict(expt)
	data['meta'] = meta
	# write the experiment file
	with open('expt_%d.json'%no if no!=None else 'expt.json','w') as fp: fp.write(json.dumps(data))
	# collect the script
	shutil.copyfile(os.path.join(meta['cwd'],expt['script']),'script_%d.py'%no if no!=None else 'script.py')

def prep_run(expt,meta):
	"""Prepare a single run without numbering."""
	prep_step(expt=expt,meta=meta,no=None)
	return [None]

def prep_metarun(expt,meta):
	"""
	"""
	import ipdb;ipdb.set_trace()

### RUN EXPERIMENTS

def execute(steps):
	"""Call the execution routines."""
	#! developing standard running now and then later supervised execution
	if steps==[None]: 
		#! when we import amx it needs to get the experiment and state so we move the files
		#! ... when there is only one step expt.json should exist but it would be good to handle except here
		#! previously started by running directly: os.system('python script.py')
		# run the script by importing it
		import ortho
		# this is the entire point at which the script is executed, and it is nearly identical to running it 
		# ... at the terminal. the only difference is that we get the environment, and conf from ortho
		mod = ortho.importer('script.py',strict=True)
	else: raise Exception('dev')

def runner(expt,meta,run=True):
	"""
	Prepare and/or run a simulation.
	"""
	expt_style = classify_experiment(expt)
	prep_func = {'run':prep_run,'metarun':prep_metarun}.get(expt_style,None)
	if not prep_func: raise Exception(
		'cannot find function to prep an experiment with style %s: %s'%(expt_style,expt))
	steps = prep_func(expt=expt,meta=meta)
	if run: execute(steps)
	return
