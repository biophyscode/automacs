#!/usr/bin/env python

from __future__ import print_function
import os
from .bash import bash
from .requires import requires_program

@requires_program('git')
def sync(**kwargs):
	"""
	Ensure modules are fresh.
	"""
	modules = kwargs.pop('modules',{})
	if kwargs: raise Exception(kwargs)
	# check each module
	for spot,mod in modules.items():
		print('status','checking module at %s'%spot)
		if not isinstance(mod,dict):
			mod = {'address':mod}
		# address is required
		#! check address?
		address = mod.pop('address')
		# clone if missing
		if not os.path.isdir(spot): bash('git clone %s %s'%(address,spot),scroll=True,tag='[BASH] | ')
		# check branch
		branch = mod.pop('branch',None)
		if branch:
			branch_result = bash('git -C %s rev-parse --abbrev-ref HEAD'%spot,scroll=False)
			stderr = branch_result['stderr']
			if stderr: raise Exception(stderr)
			this_branch = branch_result['stdout'].strip()
			print('status','module %s is on branch %s'%(spot,this_branch))
			if this_branch!=branch:
				# if we need a new branch we first fetch it before checkout
				cmd = 'git -C %s fetch origin %s'%(spot,branch)
				print('bash',cmd)
				bash(cmd)
				cmd = 'git -C %s checkout %s'%(spot,branch)
			else: pass
		if mod: raise Exception('unprocessed module methods: %s'%str(mod))
