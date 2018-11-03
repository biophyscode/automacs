#!/usr/bin/env python

from __future__ import print_function
import sys,json,shutil,os,glob,re
import ortho
from ortho.handler import Handler
from ortho.imports import importer
from ortho.misc import listify,str_types
from .chooser import collect_experiments


### CLASSIFY EXPERIMENTS

def execute(steps):
	"""Call the execution routines."""
	#! developing standard running now and then later supervised execution
	if steps==[None]: 
		# arriving at the execute function via `make go` means that we used a single python execution loop
		#   to write an experiment and then import the script below to run it. this means that amx is imported
		#   only once, and without the experiment. we delete the module here to ensure that it is imported
		#   from scratch at the beginning of script.py below to ensure this mimics the usual execution of
		#   the script from python at the terminal. note that execution by os.system would work equally well
		#! note that the deletions here need to track the modules in the amx framework so that 
		#!   we properly clean up the environment before running script.py. any changes to bootstrap.py or
		#!   the modules list for importing automacs proper should 		
		del_keys = ['amx']
		for key in sys.modules:
			if re.match(r'^amx\.',key): del_keys.append(key)
		for key in del_keys: 
			if key in sys.modules: 
				#! python 2 has quirky imports: you cannot delete yourself!
				if sys.version<(3,0) and key=='amx.runner.execution': continue
				del sys.modules[key]
		#! when we import amx it needs to get the experiment and state so we move the files
		#!   when there is only one step expt.json should exist but it would be good to handle except here
		#! previously started by running directly: os.system('python script.py')
		import ortho
		# this is the entire point at which the script is executed, and it is nearly identical to running it 
		#   at the terminal. the only difference is that we get the environment, and conf from ortho
		mod = ortho.importer('script.py',strict=True)
	else: 
		raise Exception('dev')

def populate_experiment(extends,details,meta):
	"""
	When one experiment extends another, as a single run or a metarun, 
	we get the other experiment here.
	"""
	expts = collect_experiments(ortho.conf)
	if extends not in expts['experiments']:
		raise Exception(
			'cannot find experiment %s which extends this one: %s'%(
				extends,meta['experiment_name']))
	new_settings = expts['experiments'][extends]['settings']
	new_settings.update(**details.get('settings',{}))
	details['settings'] = new_settings
	# inherit some items from the parent
	for key in ['params','extensions','tags']:
		if (key not in details 
			and key in expts['experiments'][extends]):
			details[key] = expts['experiments'][extends][key]
	# note that details is populated in-place above
	return

def standardize_metarun(seq,namer=None,sorter=None):
	"""
	Given a YAML object for a metarun, we standardize several formats.
	"""
	# the default namer below uses two digits but can overflow
	if not namer: namer = lambda number,name: 's%02d-%s'%(number+1,name)
	# note that all metarun items must be valid experiments for the handler
	#   except for the inclusion of a name key for naming if desired
	reseq = []
	# list items are assigned numbers in order
	if isinstance(seq,list):
		order = []
		for ss,s in enumerate(seq):
			if 'extends' not in s: 
				raise Exception('each metarun item needs at least an "extends" key. we got: %s'%s)
			name = s.pop('name',s['extends'])
			order.append(namer(number=ss,name=name))
			reseq.append(s)
	elif isinstance(seq,dict):
		if sorter: raise Exception('dev')
		# if the user supplies a dictionary we sort by the keys
		#   which is perfectly fine if you send along integers
		else: sorter = sorted
		keys = sorter(seq.keys())
		reseq = []
		for key in keys:
			val = seq[key]
			if isinstance(val,dict): raise Exception('dev')
			elif isinstance(val,str_types): reseq.append({'extends':val})
			else: raise Exception('format error in the metarun: %s'%seq)
		order = [namer(number=ss,name=reseq[ss]) 
			for ss,key in enumerate(keys)]
		reseq = [seq[key] for key in keys]
	else: raise Exception('cannot interpret metarun: %s'%seq)
	# the order here provides the name for the metarun, which does not respect
	#   the name in the settings name key for each extended run that comprises
	#   a single metarun
	return order,reseq

class ExperimentHandler(Handler):
	# note that the meta keywrord is routed separately in the handler
	# hence the taxonomy keys match the yaml file exactly
	taxonomy = {
		'run':{'base':{'settings','script'},'opts':{'extensions','tags','params','extends'}},
		'quick':{'base':{'quick'},'opts':{'params','tags','extensions','settings'}},
		'metarun':{'base':{'metarun'},'opts':{'random'}}}
	def prep_step(self,expt,meta,no=None):
		"""
		Prepare a single step in an experiment.
		"""
		data = dict(expt)
		data['meta'] = meta
		# make sure the expt gets the tags
		expt.update(**meta)
		# write the experiment file
		with open('expt_%d.json'%no if no!=None else 'expt.json','w') as fp: 
			fp.write(json.dumps(data))
		# collect the script
		shutil.copyfile(os.path.join(meta['cwd'],expt['script']),
			'script_%d.py'%no if no!=None else 'script.py')
	def run(self,**kwargs):
		"""Prepare a single run without numbering."""
		extends = kwargs.pop('extends',None)
		# use settings from one experiment as a base for the other
		if extends: populate_experiment(extends,kwargs,self.meta)
		self.prep_step(expt=kwargs,meta=self.meta,no=None)
		return [None]
	def quick(self,**kwargs): 
		"""Run without writing experiment or script files."""
		# write the settings directly to the experiment
		# as with the magic importer, we know amx is in modules at this point
		import amx
		from amx.amxstate import AMXState
		settings = amx.AMXState(me='settings',underscores=True)
		state = AMXState(settings,me='state',upnames={0:'settings'})
		if 'settings' in kwargs: settings.update(**kwargs['settings'])
		amx.state = state
		return state
	def metarun(self,**kwargs):
		"""Handle metaruns i.e. a sequence of runs."""
		order,seq = standardize_metarun(kwargs.pop('metarun'))
		seq_out = []
		if kwargs: raise Exception('unprocessed kwargs: %s'%kwargs)
		expts = [{} for s in seq]
		import pdb;pdb.set_trace()
		for ss,s in enumerate(seq):
			populate_experiment(s['extends'],expts[ss],self.meta)
		import pdb;pdb.set_trace()
		handlers = [ExperimentHandler(meta=self.meta,classify_fail=
			'cannot find an experiment handler that accepts these keys: %(args)s',
			**expt_this) for expt_this in expts]
		import pdb;pdb.set_trace()
		if False:
			for num,(key,expt) in enumerate(seq.items()):
				if not expt: expt = {}
				populate_experiment(key,expt)
				seq_out.append(expt)
				self.prep_step(expt=expt,meta=self.meta,no=num)
			import pdb;pdb.set_trace()

def runner(expt,meta,run=True):
	"""
	Prepare and/or run a simulation.
	"""
	# handler completes the preparation
	handler = ExperimentHandler(meta=meta,classify_fail=
		'cannot find an experiment handler that accepts these keys: %(args)s',
		**expt)
	steps = handler.solve
	# after preparation we may run directly
	if run:
		if handler.style=='quick':
			outgoing = sys.modules['amx'].__dict__
			from amx.importer import magic_importer,get_import_instructions
			_import_instruct = get_import_instructions(config=ortho.conf)
			import amx
			state = amx.state
			settings = amx.state._up[0]
			imported = magic_importer(expt=expt,instruct=_import_instruct,
				distribute=dict(state=state,settings=settings,expt=expt))
			outgoing.update(**imported['functions'])
			exec(handler.kwargs['quick'],outgoing,outgoing)
		elif handler.style=='run': 
			execute(steps)
		elif handler.style=='metarun':
			for step in steps:
				execute(steps)
