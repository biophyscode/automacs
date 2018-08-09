#!/usr/bin/env python

from __future__ import print_function
import re,os
# entrypoint for yaml
try: import yaml
except: pass #! exception waits until later. raise Exception('missing yaml at experiments.py')
##! import yaml #! protect against no yaml?
from ortho import listify,str_types,check_repeated_keys
from ortho.requires import requires_python

controlmsg = {
	'json':'found either (a) repeated keys or (b) JSON error in a string. '+
		'we require incoming dict literals to be convertible to JSON '+
		'so we can check for repeated keys. this means that single quotes must be converted to '+
		'double quotes, which means that you should use escaped double quotes where possible. '+
		'see the jsonify function for more information on how things are checked. otherwise '+
		'try `make codecheck <file>` to debug the JSON error in your file. ',}

def collect_experiment_files(finder):
	"""
	Search for experiment files in this subtree. 
	Instructions for finding these files can be found in the "inputs" key in config.json via ortho. 
	This key can be (1) a single file, (2) a glob for many files, (3) a list of files or globs, or (4) a 
	regex pattern written into extractable from the string if it matches ``^@regex(.+)``. The last option is 
	the most flexible and allows users to find all files named ``anything_expt.py``, for example.
	"""
	# read all of the dictionaries in the scripts pointed to by inputs into a single space
	# the inputs argument can be a string with a glob, a list of globs, or a special regex
	if type(finder) in str_types and re.match('^@',finder):
		regex_rule = re.match('^@regex(.+)$',finder).group(1)
		input_sources = []
		for root_dn,dns,fns in os.walk('./'):
			input_sources.extend([os.path.join(root_dn,fn) for fn in fns if re.match(regex_rule,fn)])
	else: input_sources = listify(finder)
	return input_sources

def intepret_experiment_file_python(fn,toc,sources):
	"""
	Interpret a python experiment file.
	"""
	with open(fn) as fp: text_spec = fp.read()
	if not check_repeated_keys(text_spec):
		raise Exception(controlmsg['json']+' error is located in: %s'%fn)
	inputlib_ins = eval(text_spec)
	# attach location to each incoming hash
	for key,val in inputlib_ins.items():
		if 'cwd' in val: raise Exception('file %s has key %s with cwd already defined'%(fn,key))
		val['cwd'] = os.path.dirname(fn)
		# populate the master inputlib
		# sequential overwriting happens here
		if key in toc: raise Exception('input file %s contains a key "%s" that we already found!'%(fn,key))
		else: toc[key],sources[key] = val,fn
	return

@requires_python('yaml')
def intepret_experiment_file_yaml(fn,toc,sources):
	"""
	Interpret a YAML experiment file.
	"""
	import yaml
	with open(fn) as fp: spec = yaml.load(fp)
	for key,val in spec.items():
		if 'cwd' in val: raise Exception('file %s has key %s with cwd already defined'%(fn,key))
		val['cwd'] = os.path.dirname(fn)
		if key in toc: raise Exception('input file %s contains a key "%s" that we already found!'%(fn,key))
		else: toc[key],sources[key] = val,fn
	return

def collect_experiments(conf,silent=False,verbose=False):
	"""
	Collect all available experiments.
	"""
	finder = conf.get('inputs',None)
	if not finder: raise Exception('we require a key `inputs` in `config.json` that sets the experiment '
		'file naming scheme')
	fns = collect_experiment_files(conf.get('inputs'))
	# the table of contents is passed by reference and accumulates experiments; sources collects paths
	toc,sources = {},{}
	for fn in fns:
		ext = os.path.splitext(os.path.basename(fn))[1]
		if ext=='.py': intepret_experiment_file_python(fn,toc,sources)
		elif ext=='.yaml': intepret_experiment_file_yaml(fn,toc,sources)
		else: raise Exception('invalid experiment file %s'%fn)
	return dict(experiments=toc,sources=sources)
