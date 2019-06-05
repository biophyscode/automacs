#!/usr/bin/env python

from __future__ import print_function
import re,os
from .handler import Handler
from .misc import str_types,listify
from .imports import importer

class HookHandler(Handler):
	#! remove from omni after port
	# when calling this handler, send the kwargs from the compute function
	#   through to the meta kwarg so the hook can access everything in compute
	#! taxonomy = {'standard':{'import_target','function'}}
	#! remove taxonomy on HookHandler update from current factor/dev.py
	def standard(self,import_target,function):
		from .imports import importer
		# assume import targets are in calcs
		#!!!! hardcoded in omni mod = importer(os.path.join('calcs',import_target))
		mod = importer(import_target)
		func = mod[function]
		# some functions may not wish to receive meta or kwargs
		if self.meta: kwargs = {'kwargs':self.meta}
		else: kwargs = {}
		return func(**kwargs)
	def short(self,s,f): 
		"""Alias for standard with shorter keys."""
		return self.standard(import_target=s,function=f)
	def merger(self,s,collect=True):
		mod = importer(s)
		return mod
		#!! import ipdb;ipdb.set_trace()
		#!! raise Exception('!!!! YAYYY')

def hook_handler(conf,this=None,strict=True):
	"""
	Convert hooks in the config.

	To use this hook to set an alternate gromacs, use:
		make set_hook gmx_call_handler="gmx_mpi"
	Undo with:
		make unset "@gmx_call_handler"
	To use this hook to check for gromacs first, use:
		make set_hook gmx_call="\"argument\""
		where argument is the following on a single line:
			{'import_target':'amx/gromacs/machine_config.py',
				'function':'check_installed'}
	Note that hooks can be handled "just in time" because you have to send
	the hooks flag to read_config to actually process them. This means that 
	there is some amount of decision on the request side of things. You have
	to *know* there is a possibility of a hook to be ready for you to load
	the config with hooks and get the right answer or behavior (since the whole
	point of hooks is to run a function). This could be changed by a flag
	of some kind. The problem is circular: we cannot use a flag in config to 
	tell config to always unpack the hooks. In any case, the things that could
	accept a hook should be well-documented anyway.
	"""
	regex_hook = r'^@(.+)$'
	hook_keys = [(i,re.match(regex_hook,i).group(1))
		for i in conf.keys() if re.match(regex_hook,i)]
	# prevent @-syntax collisions
	for i,j in hook_keys:
		if j in conf: 
			raise ValueError('cannot use keys %s and %s together'%(i,j))
	if this!=None and not this.startswith('@'): this = '@'+this
	if this!=None and this not in dict(hook_keys).keys(): 
		# we request hooks without the @-syntax and add it here if missing
		if strict: 
			raise Exception(
				'cannot find the requested hook "%s" in the list: %s'%(
				this,dict(hook_keys)))
		else: 
			print('warning failed to find hook "%s"'%this)
			return None
	# if we request a specific hook, we only process that hook
	elif this: hook_keys = [(i,j) for i,j in hook_keys if i==this]
	# loop over hooks
	# note that we assign the result to key and key_simple so the user
	#   does not have to use the @-syntax to look things up. we prevent
	#   collisions above, so this assignment does not cause problems
	for key,key_simple in hook_keys:
		hook_defn = conf.pop(key)
		# if the value of the hook is a string, then this is the result
		if isinstance(hook_defn,str_types):
			conf[key] = conf[key_simple] = hook_defn
		elif isinstance(hook_defn,dict):
			conf[key] = conf[key_simple] = HookHandler(**hook_defn).solve
		# ignore hooks that are False
		elif isinstance(hook_defn,bool) and not hook_defn: 
			conf[key] = conf[key_simple] = hook_defn
		else: raise Exception('dev')
	return True

def hook_merge(hook,namespace):
	"""
	This is also a minimal working example of using a hook.
	"""
	#! for some reason this has to be imported here?
	from .config import config_hook_get
	collected = config_hook_get(hook,None)
	if collected: 
		print('status hook_merge collected hooks for "%s": %s'%(hook,list(collected.keys())))
		namespace.update(**collected)
	return 
