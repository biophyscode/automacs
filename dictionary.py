#!/usr/bin/env python

from __future__ import print_function
import sys,re

#!!!!!!!!
str_types = [str] if (sys.version_info>(3,0)) else [str,unicode]

class DotDict(dict):
	"""
	Use dots to access dictionary items.
	"""
	def __init__(self,*args,**kwargs):
		if args: raise Exception('DotDict cannot accept arguments')
		#! remove fallbacks defaults not necessary
		extra_protect_keys = kwargs.pop('extra_protected_keys',['_fallbacks','_fallbacks_order','_up'][:-1])
		# special sauce that maps the dictionary self to its own attributes list
		self.__dict__ = self
		# maintain a list of protected keywords used by the dict object
		self.__dict__['_protect'] = set(list(dict.__dict__.keys())+extra_protect_keys)
		# load the dictionary with incoming args and kwargs
		for key,val in args: self.__dict__[key] = val
		self.update(**kwargs)
	def __setattr__(self,key,val):
		"""Attributes act as dictionary keys and vis-versa."""
		if key in self.get('_protect',[]): 
			raise Exception('cannot use key %s as an attribute %s'%key)
		# special sauce that allows you to set new attributes
		super(dict,self).__setattr__(key,val)
	def __repr__(self): 
		"""Support the __setattr__ function which makes keys into attributes."""
		# hide the underscore attributes but allow non-strings as keys
		#! note however you actually cannot set non-strings as keys except with self.__dict__
		# note that this function means self.__dict__ hides _protect
		return str(dict([(i,j) for i,j in self.items() if (type(i) 
			not in str_types or not i.startswith('_'))]))

class MultiDict(DotDict):
	"""
	Alternate dictionary object which has layers of additional dictionaries to fall back on missing keys.
	Behaves like a DotDict, except the contents should come in via `base` kwarg and
	the args list should be a list of dictionaries to consult in sequence when the contents lack a key.
	"""
	def __init__(self,*args,**kwargs):
		"""
		Arguments should be a sequence of dictionaries for providing missing hashes.
		Keyword arguments include:
		  - strict ensures exception on missing key otherwise e.g. self.not_there gives None
		  - name is useful for debugging when using multiple MultiDict
		  - upnames is a hash from position in the arguments list to the name of the fallback
		      where the existence of upnames means we report whenever we fall back to that dict
		"""
		name = kwargs.pop('me','nameless MultiDict')
		strict = kwargs.pop('strict',False)
		base = kwargs.pop('base',{})
		upnames = kwargs.pop('upnames',{})
		underscores = kwargs.pop('underscores',False)
		if kwargs: raise Exception('unprocessed kwargs: %s'%str(kwargs))
		# we check keys in place so that upstream dicts are referenced by pointer
		if underscores: self._key_map_checker(base)
		super(MultiDict,self).__init__(**base)
		self.check_dict(*args)
		# send arguments to protected _up attribute
		self._up = args
		self._protect.add('_up')
		# other intrinsic parameters must be set after super init
		self._strict = strict
		self._protect.add('_strict')
		self._name = name
		self._protect.add('_name')
		# check upnames keys are indices of up dictionaries
		mismatch_keys = [ii for ii,i in upnames.items() if ii not in range(len(args))]
		if any(mismatch_keys):
			raise Exception(('received upstream dictionary naming %s with %d items for upstream '
				'dictionary list of length %d')%(upnames,len(upnames),len(args)))
		self._upnames = upnames
		self._protect.add('_upnames')
		self._underscores = underscores
		self._protect.add('_underscores')
	def check_dict(self,*args):
		# check that args are dict
		for aa,a in enumerate(args):
			#! note that we are strictly (not duck) typing as dict here
			if not isinstance(a,dict): 
				raise Exception('all arguments to MultiDict must be dict. '+
					'argument %d is not a dict: type %s, value is: %s'%(aa,type(a),a))
	def _getattr(self,key,d=None):
		if key in self.__dict__: return super(MultiDict,self).get(key)
		elif '_up' in self.__dict__: 
			for unum,up in enumerate(self._up):
				if key in up:
					if self._upnames and unum in self._upnames:
						print('note','using upstream dictionary %s for key %s'%(self._upnames[unum],key))
					return up[key]
		if super(MultiDict,self).get('_strict'): raise Exception('missing key %s'%key)
		else: return d
	def __getattr__(self,key): return self._getattr(key)
	def __getitem__(self,key): return self._getattr(key)
	def get(self,k,d=None):
		if k in self.__dict__: return super(MultiDict,self).get(k,d)
		else: return self._getattr(k,d=d)
	def _key_map_checker(self,kwargs):
		# change spaces in keys to underscore and check for duplicates after the mapping
		keys_simple = dict([(j,re.sub(' ','_',j)) for j in kwargs.keys()])
		if len(keys_simple.values())!=len(set(keys_simple.values())):
			keys_redundant = [i for i,j in keys_simple.items() 
				if sum([k==j for k in keys_simple.values()])>1]
			raise Exception('some keys are redundant after '
				'replacing spaces with underscores %s'%keys_redundant)
		# we must make a copy to ensure that we retain base as a pointer
		kwargs_side = dict([(i,j) for i,j in kwargs.items()])
		for k in kwargs_side: del kwargs[k]
		for k,v in kwargs_side.items(): 
			kwargs[re.sub(' ','_',k)] = v
		# keys changed in place
		return
	def update(self,*args,**kwargs):
		# unlike init we do not need to ensure the incoming dictionary remains a pointer
		if args and len(args)>1:
			raise TypeError("update expected at most 1 arguments, got %d"%len(args))
		elif args: 
			incoming = dict(args[0])
			incoming.update(**kwargs)
		else: incoming = kwargs
		# merge and check mapping
		self._key_map_checker(incoming)
		for key,val in incoming.items(): self[key] = kwargs[key]
