#!/usr/bin/env python

import re,os
from ortho import Handler
from .misc import str_types

def hook_handler(conf):
	"""
	Convert hooks in the config.

	To use this hook to set an alternate gromacs, use:
		make set_hook gmx_call_handler="gmx_mpi"
	To use this hook to check for gromacs first, use:
		make set_hook gmx_call_handler="{'import_target','function'}"
	"""
	regex_hook = r'^@(.+)$'
	hook_keys = [(i,re.match(regex_hook,i).group(1))
		for i in conf.keys() if re.match(regex_hook,i)]
	for i,j in hook_keys:
		if j in conf: 
			raise Exception('cannot use keys %s and %s together'%(i,j))
	# loop over hooks
	for key,key_simple in hook_keys:
		hook_defn = conf.pop(key)
		# if the value of the hook is a string, then this is the result
		if isinstance(hook_defn,str_types):
			conf[key_simple] = hook_defn
		else: raise Exception('dev')

#! this is being ported into ortho in automacs
class HookHandler(Handler):
	# when calling this handler, send the kwargs from the compute function
	#   through to the meta kwarg so the hook can access everything in compute
	taxonomy = {'standard':{'import_target','function'}}
	def standard(self,import_target,function):
		from ortho import importer
		# assume import targets are in calcs
		mod = importer(os.path.join('calcs',import_target))
		func = mod[function]
		return func(kwargs=self.meta)
