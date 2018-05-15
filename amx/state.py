#!/usr/bin/env python

import re

class DotDict(dict):
	"""
	Use dots to access dictionary items.
	"""
	def __init__(self,*args,**kwargs):
		if args: raise Exception('DotDict cannot accept arguments')
		extra_protect_keys = kwargs.pop('extra_protected_keys',['_fallbacks','_fallbacks_order'])
		# special sauce that maps the dictionary self to its own attributes list
		self.__dict__ = self
		# maintain a list of protected keywords used by the dict object
		self.__dict__['_protect'] = list(dict.__dict__.keys())+extra_protect_keys
		# load the dictionary with incoming args and kwargs
		for key,val in args: self.__dict__[key] = val
		self.update(**kwargs)
	def __setattr__(self,key,val):
		if key in self.get('_protect',[]): 
			raise Exception('cannot use key %s as an attribute %s'%key)
		# special sauce that allows you to set new attributes
		super(dict,self).__setattr__(key,val)
	def __repr__(self): 
		# hide the underscore attributes
		return str(dict([(i,j) for i,j in self.items() if not i.startswith('_')]))

"""
Development notes:
- we need to gut all uses of state.q and replace with state.get
- we need to document the use cases for required keys, which should use get
	note that it is far more common to check for missing keys than to insist on a key,
		so that should be the design priority
	you cannot ask of a setting key is in state directly, you have to look for none
"""

class AMXState(DotDict):
	def __init__(self,*args,**kwargs):
		"""Initialize with "fallback" dictionaries so state falls back to settings."""
		fallbacks = kwargs.pop('fallbacks',[])
		_except_on_missing = kwargs.pop('except_on_missing',False)
		name_self = kwargs.pop('me','AMXState (anonymous)')
		kwargs['extra_protected_keys'] = kwargs.pop('extra_protected_keys',[])+['_except_on_missing','_name']
		kwargs = self._key_map_checker(kwargs)
		# initialize after popping from kwargs but before setting them back again
		DotDict.__init__(self,*args,**kwargs)
		# add fallbacks to the dictionary only after init and only using manual entry to skip protect check
		# note that fallbacks are not named so using e.g. state._fallbacks just gives list of fallback dicts
		self.__dict__['_fallbacks'] = fallbacks
		self.__dict__['_except_on_missing'] = _except_on_missing
		# name the object on declaration for lookup failures. this is clearer than inferring the name later
		self.__dict__['_name'] = name_self
	def _key_map_checker(self,kwargs):
		# change spaces in keys to underscore and check for duplicates after the mapping
		keys_simple = dict([(j,re.sub(' ','_',j)) for j in kwargs.keys()])
		if len(keys_simple.values())!=len(set(keys_simple.values())):
			keys_redundant = [i for i,j in keys_simple.items() 
				if sum([k==j for k in keys_simple.values()])>1]
			raise Exception('some keys are redundant after '
				'replacing spaces with underscores %s'%keys_redundant)
		kwargs = dict([(re.sub(' ','_',i),j) for i,j in kwargs.items()])
		return kwargs
	def __getattr__(self,key):
		"""Get attributes and fall back to other dictionaries."""
		#! current default behavior returns None instead of key failure
		#! make the default return value malleable on init depending on the primary use-cases
		if key in self['_protect']: return self[key]
		elif key in self: return self[key]
		else: 
			# parse fallback dictionaries in order and check for the key
			for fallback in self._fallbacks:
				if key in fallback: return fallback[key]			
			else:
				if self.__dict__['_except_on_missing']: raise Exception(
					'The DotDict(AMXState) named "%s" is missing key "%s"'%(self.__dict__['_name'],key))
				else: return None
	def update(self, *args, **kwargs):
		if args and len(args)>1:
			raise TypeError("update expected at most 1 arguments, got %d"%len(args))
		elif args: 
			incoming = dict(args[0])
			incoming.update(**kwargs)
		else: incoming = kwargs
		# merge and check mapping
		kwargs = self._key_map_checker(incoming)
		for key,val in kwargs.items(): self[key] = kwargs[key]
