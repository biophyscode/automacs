#!/usr/bin/env python

from __future__ import print_function
import sys,json,shutil,os,glob
from ortho.handler import Handler
from ortho.imports import importer
from ortho.misc import listify

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
		del sys.modules['amx']
		#! when we import amx it needs to get the experiment and state so we move the files
		#! ... when there is only one step expt.json should exist but it would be good to handle except here
		#! previously started by running directly: os.system('python script.py')
		import ortho
		# this is the entire point at which the script is executed, and it is nearly identical to running it 
		# ... at the terminal. the only difference is that we get the environment, and conf from ortho
		mod = ortho.importer('script.py',strict=True)
	else: 
		import pdb;pdb.set_trace()
		raise Exception('dev')

class ExperimentHandler(Handler):
	# note that the meta keywrord is routed separately in the handler
	# hence the taxonomy keys match the yaml file exactly
	taxonomy = {
		'run':{'base':{'settings','script'},'opts':{'extensions','tags','params'}},
		'quick':{'base':{'settings','quick'},'opts':{'params','tags','extensions'}},}
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
		self.prep_step(expt=kwargs,meta=self.meta,no=None)
		return [None]
	def quick(self,**kwargs): 
		"""Run without writing experiment or script files."""
		# write the settings directly to the experiment
		# as with the magic importer, we know amx is in modules at this point
		import amx
		from amx.state import AMXState
		settings = amx.AMXState(me='settings',underscores=True)
		state = AMXState(settings,me='state',upnames={0:'settings'})
		settings.update(**kwargs['settings'])
		amx.state = state
		return state

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
		if handler.style=='run': execute(steps)
		elif handler.style=='quick':
			outgoing = sys.modules['amx'].__dict__
			from amx.importer import magic_importer
			_import_instruct = {
				'modules':['amx/gromacs','amx/utils','amx/automacs'],
				'decorate':{'functions':['gmx'],'subs':[('gromacs.calls','gmx_run')]},
				'initializers':['gromacs_initializer']}
			import amx
			state = amx.state
			settings = amx.state._up[0]
			imported = magic_importer(expt=expt,instruct=_import_instruct,
				distribute=dict(state=state,settings=settings,expt=expt))
			outgoing.update(**imported['functions'])
			exec(handler.kwargs['quick'],outgoing,outgoing)
