#!/usr/bin/env python

from __future__ import print_function
import sys,json,shutil,os,glob,re,copy
import ortho
from ortho.handler import Handler
from ortho.imports import importer
from ortho.misc import listify,str_types
from .chooser import collect_experiments

### CLASSIFY EXPERIMENTS

classify_fail = \
	'cannot find an experiment handler that accepts these keys: %(args)s'

def execute(steps,script='script.py',metarun_num=-1):
	"""Call the execution routines."""
	#! steps needs to be retired. currently setting metarun_num to manage metaruns

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
				if sys.version_info<(3,0) and key=='amx.runner.execution': continue
				del sys.modules[key]
		#! when we import amx it needs to get the experiment and state so we move the files
		#!   when there is only one step expt.json should exist but it would be good to handle except here
		#! previously started by running directly: os.system('python script.py')
		import ortho
		# this is the entire point at which the script is executed, and it is nearly identical to running it 
		#   at the terminal. the only difference is that we get the environment, and conf from ortho
		if metarun_num>=0:
			if os.path.islink('expt.json'): os.unlink('expt.json')
			os.symlink('expt_%d.json'%metarun_num,'expt.json')
		mod = ortho.importer(script,strict=True)
	#! note that this is dealing with "steps" but it is really one step only
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
	for key in ['params','extensions','tags','script']:
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
	# note that the meta keyword is routed separately in the handler
	# hence the taxonomy keys match the yaml file exactly
	#! retiring the taxonomy because the Handler is updated
	#!   note that the run, quick, metarun functions all need updated and tested
	#! taxonomy = {
	#!	'run':{'base':{'settings','script'},'opts':{'extensions','tags','params','extends'}},
	#!	'quick':{'base':{'quick'},'opts':{'params','tags','extensions','settings'}},
	#!	'metarun':{'base':{'metarun'},'opts':{'random'}}}
	def _prep_step(self,expt,meta,no=None):
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
	def run(self,settings,script,extends=None,tags=None,
		params=None,extensions=[],notes=None,no=None):
		"""Prepare a single run without numbering."""
		#! see taxonomy above, retired opts
		#! we need kwargs for the _prep_step function
		#!   this is an artefact of a Handler update
		kwargs = dict(tags=tags,extends=extends,settings=settings,
			script=script,extensions=extensions,params=params)
		# extends = kwargs.pop('extends',None)
		# use settings from one experiment as a base for the other
		if extends: populate_experiment(extends,kwargs,self.meta)
		self._prep_step(expt=kwargs,meta=self.meta,no=no)
		return [None]
	def quick(self,quick): 
		"""Run without writing experiment or script files."""
		#! see taxonomy above, retired opts
		# write the settings directly to the experiment
		# as with the magic importer, we know amx is in modules at this point
		import amx
		from amx.amxstate import AMXState
		settings = amx.AMXState(me='settings',underscores=True)
		state = AMXState(settings,me='state',upnames={0:'settings'})
		if 'settings' in kwargs: settings.update(**kwargs['settings'])
		amx.state = state
		return state
	def metarun(self,metarun,notes=None):
		"""Handle metaruns i.e. a sequence of runs."""
		#! see taxonomy above, retired opts
		order,seq = standardize_metarun(metarun)
		seq_out = []
		expts = [{} for s in seq]
		for ss,s in enumerate(seq):
			expts[ss].update(**s)
			populate_experiment(s['extends'],expts[ss],self.meta)
			#! previously self._prep_step(expt=expt,meta=self.meta,no=num)
			#!   this might make more sense since it queues everything up
			# add a number (use natural numbering from 1 instead of 0)
			expts[ss]['no'] = ss+1
		return list(zip(order,expts))

def runner(expt,meta,run=True):
	"""
	Prepare and/or run a simulation.
	"""
	# handler completes the preparation
	handler = ExperimentHandler(meta=meta,classify_fail=classify_fail,**expt)
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
			for snum,(name,step) in enumerate(steps):
				# number from 1 instead of 0
				snum_this = snum + 1
				# pass along a step number for make_step
				step['settings']['stepno'] = snum_this
				# this handles the recursion
				#! note that the cwd and experiment_source might be wrong 
				#!   if the metarun components came from elsewhere?
				meta_this = copy.deepcopy(meta)
				meta_this['experiment_name'] = name
				handler = ExperimentHandler(meta=meta_this,
					classify_fail=classify_fail,**step).solve
				#! hacking the expt and script file handling
				execute(handler,script='script_%d.py'%
					snum_this,metarun_num=snum_this)
