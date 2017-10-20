#!/usr/bin/env python

#---native connections to GROMACS
#from gromacs.calls import gmx,get_gmx_paths
#from gromacs.commands import gmx_call_templates,get_last_gmx_call,commands_interpret

#---native connection to GROMACS via a submodule
#---note that gromacs/__init__.py exposes the automacs-GROMACS interface functions required here
#---...and that other integrators can be added to the generic automacs functions here in a similar way
#from gromacs import gmx_get_paths,gmx,gmx_call_templates,gmx_get_last_call,gmx_commands_interpret

"""
Automacs library for automatic GROMACS simulations.
Note: this docstring is not caught by sphinx.
"""

_not_reported = ['deepcopy']

import os,sys,shutil,glob,re,json
from copy import deepcopy

def register(func):
	"""
	Collect utility functions in the state.
	Note that typically this would be a decorator, but the import scheme makes that unworkable.
	"""
	fname = func.__name__
	if '_funcs' not in state: state._funcs = []
	state._funcs.append(fname)
	state[fname] = func

def q(key,val=None):
	"""
	Check either settings or the state for a variable name with this alias for a dictionary "get".
	This takes the place of (indiscriminately) loading all settings into the state.
	"""
	return state.get(key,settings.get(key,val))

def init():
	"""
	Initialize the automacs state.
	Note that all automacs variables are defined here.
	Structure of the state Cursors: here = current directory with trailing slash 
	step = current step name
	stepno = current step number
	History: steps = list of steps in order
	State-only interactors: calls.py make_step
	"""
	print('[STATUS] initializing automacs')
	#---figure out the right paths for gromacs execution
	gmx_get_paths()
	#---interpret the call templates
	if type(gmx_call_templates)==str: state.gmxcalls = gmx_commands_interpret(gmx_call_templates)
	else: state.gmxcalls = gmx_call_templates
	#---previously registered `gmx` and `component` here before implementing advanced import scheme
	#---we register signal functions that should not be serialized and stored in the state.json
	register(q)
	#---check for previous states
	prev_states = glob.glob('state_*.json')
	if prev_states: 
		state.before = []
		for fn in sorted(prev_states):
			with open(fn) as fp: state.before.append(json.load(fp))
	#---store settings for posterity minus the _protect
	state.settings = dict(settings)
	state.expt = dict(expt)
	#---no need to save the _protect list from the DotDict here
	del state.settings['_protect']
	del state.expt['_protect']

def make_step(name):
	"""Make a new step folder. See automacs.py docstring for defining variables in the state."""
	#---note any previous states
	if state.before:
		#---TRANSMIT DATA FROM ONE STATE TO THE NEXT
		#---get step information from the last state
		prev_state = state.before[-1]
		if state.stepno: state.stepno += 1
		else: state.stepno = prev_state['stepno'] + 1
		state.steps = list(prev_state['steps'])
	else:
		if 'stepno' not in state: state.stepno = 1
		if 'steps' not in state: state.steps = []
		else: state.stepno += 1
	state.step = 's%02d-%s'%(state.stepno,name)
	os.mkdir(state.step)
	state.here = os.path.join(state.step,'')
	#---register a log file for this step.
	#---log files are in the step folder, and use the step name with ".log"
	state.step_log_file = os.path.join(state.here,state.step+'.log')
	state.steps.append(state.step)
	#---the hook is a string that points to a function possibly from an extension code that runs here
	hook = settings.get('make_step_hook',None)
	if hook!=None:
		#---this feature uses the self-referential encoding of the amx module as a dictionary in the state
		#---...which has been added to importer.py to make sure we can get parts of amx with a wildcard import
		if hook not in state.amx: 
			raise Exception('received make_step_hook %s but this function is not available in amx.state. '%hook+
				'are you sure that you have connected to all necessary extension codes?')
		else: state.amx[hook]()
	#---! note that files are not recopied on re-run because make-step only runs once
	#---copy all files
	for fn in state.q('files',[]):
		if not os.path.isfile(fn): raise Exception('cannot find an item requested in files: %s'%fn)
		shutil.copyfile(fn,os.path.join(state.here,os.path.basename(fn)))
	#---copy all sources
	for dn in state.q('sources',[]):
		if os.path.basename(dn)=='.': raise Exception('not a valid source: %s'%dn)
		if not os.path.isdir(dn): raise Exception('requested source %s is not a directory'%dn)
		shutil.copytree(dn,os.path.join(state.here,os.path.basename(dn)))
	#---retrieve files from the file registry
	if state.before and state.file_registry:
		for fn in state.file_registry: 
			shutil.copyfile(prev_state['here']+fn,state.here+fn)

def make_sidestep(name):
	"""Make a new step folder which is off-pathway."""
	if os.path.isfile(name): raise Exception('sidestep %s already exists'%name)
	os.mkdir(name)
	state.sidestep = name
	#---! formalize this 

def copy_file(src,dst,**kwargs):
	"""Wrapper for copying files."""
	cwd = os.path.join(kwargs.get('cwd',state.here),'')
	shutil.copyfile(cwd+src,cwd+dst)
	
def copy_files(src,dst):
	"""Wrapper for copying files with a glob."""
	if not os.path.isdir(dst): raise Exception('destination for copy_files must be a directory: %s'%dst)
	for fn in glob.glob(src): shutil.copy(fn,dst)

def move_file(src,dest,**kwargs):
	"""Wrapper for moving files."""
	cwd = os.path.join(kwargs.get('cwd',state.here),'')
	shutil.move(cwd+src,cwd+dest)

def register_file(fn):
	"""
	Maintain a list of new, essential files. 
	These have no specific categories (in contrast to e.g. ITP files).
	New steps copy all files in the registry.
	"""
	if not state.file_registry: state.file_registry = []
	if not os.path.isfile(state.here+fn):
		raise Exception('cannot register file because it does not exist: %s'%fn)
	if fn in state.file_registry:
		raise Exception('file %s is already in the file registry'%fn)
	state.file_registry.append(fn)

