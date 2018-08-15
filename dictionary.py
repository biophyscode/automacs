#!/usr/bin/env python

from __future__ import print_function
import sys,re
import unittest,io
from .misc import str_types

class DotDict(dict):
	"""
	Use dots to access dictionary items.
	Any key is allowed but only pythonic strings 
	Previous versions of this class used the `self.__dict__ = self` trick.
	Many thanks to: https://stackoverflow.com/questions/47999145/48001538#48001538
	"""
	def __init__(self,*args,**kwargs):
		protect_keys = kwargs.pop('protected_keys',[])
		self._protect = set(dir(dict)+dir(object)+protect_keys)
		self._protect.add('_protect')
		super(DotDict,self).__init__(*args,**kwargs)
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__
	def __repr__(self): return str(dict([(i,self[i]) 
		for i in self.keys() if i not in self._protect]))
	def __dir__(self): 
		return [i for i in self.keys() if i not in self._protect 
			and isinstance(i,str_types)]

class TestDotDict(unittest.TestCase):
	"""
	Tests for the ortho module.
	test via: `make unit_tester name="^Test.+Dict"`
	#! make a centralized location for these tests because the regexes are ungainly
	"""
	seed = {'a':1,'b':2}
	def test(self):
		this = DotDict(self.seed)
		this.c = 3
		this[1] = 4
		this[('a','b')] = 5
		self.assertTrue(this.a==1)
		self.assertTrue('c' in this)
		self.assertTrue(this.c==3)
		self.assertTrue(1 in this)
		self.assertTrue('a' in this)
		#! currently causing TypeError: unicode argument expected, got 'str' on stylized_print
		if False: 
			# checking __repr__
			capture = io.StringIO()
			sys.stdout = capture
			capture.write(str(this).decode() if sys.version_info<(3,0) else str(this))
			sys.stdout = sys.__stdout__
			val = {'a': 1, 'b': 2, 'c': 3, 1: 4, ('a', 'b'): 5}
			self.assertTrue(eval(capture.getvalue())==val)
		self.assertTrue(dir(this)==['a','b','c'])
	@unittest.expectedFailure
	def test_fail(self):
		this = DotDict(self.seed)
		this[b'c'] = 1
		self.assertTrue(this.b==1)

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
		  - underscores changes spaces to underscores for easy access
		"""
		self._name = kwargs.pop('me','nameless MultiDict')
		self._strict = kwargs.pop('strict',False)
		base = kwargs.pop('base',{})
		self._upnames = kwargs.pop('upnames',{})
		self._underscores = kwargs.pop('underscores',False)
		self._silent = kwargs.pop('silent',False)
		if kwargs: raise Exception('unprocessed kwargs: %s'%str(kwargs))
		# we check keys in place so that upstream dicts are referenced by pointer
		if self._underscores: self._key_map_checker(base)
		protected_keys = ['_name','_strict','_upnames','_underscores','_silent','_up','_check_dict']
		super(MultiDict,self).__init__(base,protected_keys=protected_keys)
		self._check_dict(*args)
		# send arguments to protected _up attribute
		# note that we have to register _up in __dict__ which is otherwise empty for parent class dict
		self._up = self.__dict__['_up'] = args
		# check upnames keys are indices of up dictionaries
		mismatch_keys = [ii for ii,i in self._upnames.items() if ii not in range(len(args))]
		if any(mismatch_keys):
			raise Exception(('received upstream dictionary naming %s with %d items for upstream '
				'dictionary list of length %d')%(upnames,len(upnames),len(args)))
	def _check_dict(self,*args):
		"""Ensure all incoming arguments are dict."""
		for aa,a in enumerate(args):
			#! note that we are strictly (not duck) typing as dict here
			if not isinstance(a,dict): 
				raise Exception('all arguments to MultiDict must be dict. '+
					'argument %d is not a dict: type %s, value is: %s'%(aa,type(a),a))
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
	def __setitem__(self,key,val):
		"""Handle underscores."""
		DotDict.__setattr__(self,key if not self._underscores else re.sub(' ','_',key),val)
	def _get(self,k,d=None):
		"""
		Nested dictionary lookups that consult backup dictionaries (up) on missing key.
		Note that this is the purpose of MultiDict, namely to keep sets of keys in categories for later,
		particularly in the case of settings/state in automacs simulations.
		"""
		if k in self.__dict__.get('_protect',{}): 
			return self.__dict__[k]
		elif k in self: return dict.get(self,k)
		else:
			for unum,up in enumerate(self.__dict__.get('_up',[])):
				if k in up:
					if self._upnames and unum in self._upnames:
						print('note','using upstream dictionary %s for key %s'%(self._upnames[unum],k))
					return up[k]
		if self._strict: raise KeyError('missing key %s'%k)
		else: return d
	__getattr__ = _get
	def __getitem__(self,k): return self._get(k)
	def get(self,k,d=None):
		"""Special sauce to ensure backups work."""
		if k in self.__dict__: return super(MultiDict,self).get(k,d)
		else: return self._get(k,d=d)

class TestMultiDict(unittest.TestCase):
	"""
	Tests for MultiDict
	test via: `make unit_tester name="^Test.+Dict"`
	"""
	base = {'a':1,'b':2}
	back = {'u':100,'v':101}
	final = {'y':99,'z':100}
	def test(self):
		# build with two fallbacks in order and base dict
		this = MultiDict(self.back,self.final,base=self.base,me='MyMultiDict')
		this.c = 3
		this['d'] = 4
		self.assertTrue(this.c==3)
		self.assertTrue(this.d==4)
		self.assertTrue(this.__getattr__('z')==100)
		self.assertTrue(this['z']==100)
		self.assertTrue(this.get('z')==100)
		self.assertTrue(this.get('w',1000)==1000)
		self.assertTrue(this.get('w')==None)
		self.assertTrue(this['w']==None)
		self.assertTrue(this._name=='MyMultiDict')
		# test strict mode which forbids any get or getattr on missing keys
		this_strict = MultiDict(self.back,self.final,base=self.base,strict=True,me='MyMultiDict')
		self.assertRaises(KeyError,this_strict.get,'w')
		self.assertRaises(KeyError,this_strict.get,'w',1000)
		# name the upstream dicts
		this_named = MultiDict(self.back,self.final,base=self.base,strict=True,me='MyMultiDict',
			upnames={0:'back',1:'final'})
		self.assertTrue(this_named.a==1)
		#! currently causing TypeError: unicode argument expected, got 'str' on stylized_print
		if False:
			capture = io.StringIO()
			sys.stdout = capture
			this_named['z']
			sys.stdout = sys.__stdout__
			# upstream dicts with names get a message on lookup (unless you set silent)
			message = '[NOTE] found key "z" in upstream dictionary "final" in "MyMultiDict (MultiDict)"\n'
			self.assertTrue(capture.getvalue()==message)
		# dictionaries are pointers
		self.assertTrue(this._up[0] is self.back)
		self.assertTrue(this._up[1] is self.final)
		# underscores sub for spaces with the underscores flag otherwise you cannot access with dot
		this = MultiDict(self.back,self.final,base=self.base,
			strict=True,underscores=True,me='MyMultiDict')
		this['some key'] = 'some value'
		self.assertTrue(this.some_key=='some value')
		self.assertFalse('some key' in this)
	@unittest.expectedFailure
	def test_forbid(self):
		this_named = MultiDict(self.back,self.final,base=self.base,strict=True,me='MyMultiDict',
			upnames={3:'missing_index_dict'})
