#!/usr/bin/env python

import inspect,sys
from .misc import str_types

def introspect_function(func,**kwargs):
	"""
	Get arguments and kwargs expected by a function.
	"""
	message = kwargs.pop('message',(
		'function introspection received a string instead of a function '
		'indicating that we have gleaned the function without importing it. '
		'this indicates an error which requires careful debugging.'))
	#! section is repetitive with code in run_program used to introspect in Python 2 or 3. centralize it!
	if sys.version_info<(3,3): 
		#! the following getargspec will be removed by python 3.6
		if isinstance(func,str_types): raise Exception(messsage)
		args,varargs,varkw,defaults = inspect.getargspec(func)
		if defaults: std,var = args[:-len(defaults)],args[-len(defaults):]
		packed = dict(args=tuple(std),kwargs=dict(zip(var,defaults)))
		return packed
	else:
		raise Exception('dev')
		sig = inspect.signature(func) # pylint: disable=no-member
		argspec_args = [name for name,value in sig.parameters.items() 
			if value.default==inspect._empty or type(value.default)==bool] # pylint: disable=no-member
		return argspec_args

class Handler(object):
	taxonomy = {}
	def classify(self,*args):
		matches = [name for name,keys in self.taxonomy.items() if (
			(isinstance(keys,set) and keys==set(args)) or 
			(isinstance(keys,dict) and set(keys.keys())=={'base','opts'} 
				and set(args)>=keys['base']
				and set(args)-keys['base']<=keys['opts']))]
		if len(matches)==0: 
			raise Exception(
				('cannot classify instructions with keys: %(args)s'
				if not self.classify_fail else self.classify_fail)%
				{'args':args})
		elif len(matches)>1: 
			raise Exception('redundant matches: %s'%matches)
		else: return matches[0]
	def __init__(self,name=None,meta=None,classify_fail=None,**kwargs):
		# leaving taxonomy blank means that it is inferred from args,kwargs
		#   of the constitutent methods in the class
		if not self.taxonomy:
			_protected = {'classify','__init__'}
			methods = dict([(i,j) for i,j in 
				inspect.getmembers(self,predicate=inspect.ismethod)
				if i not in _protected])
			expected = dict([(name,introspect_function(methods[name])) 
				for name in methods])
			for name,expect in expected.items():
				if 'self' not in expect['args']:
					raise Exception('function "%s" lacks the self argument'%name)
			# convert to a typical taxonomy structure
			self.taxonomy = dict([(name,{
				'base':set(expect['args'])-set(['self']),'opts':set(expect['kwargs'].keys())
				}) for name,expect in expected.items()])
		#! name is a common key. how are we using it here?
		if not name: self.name = "UnNamed"
		self.meta = meta if meta else {}
		self.classify_fail = classify_fail
		fname = self.classify(*kwargs.keys())
		self.style = fname
		self.kwargs = kwargs
		if not hasattr(self,fname): 
			raise Exception(
				'development error: taxonomy name "%s" is not a member'%fname)
		# introspect on the function to make sure the keys 
		#   in the taxonomy match the available keys in the function?
		self.solution = getattr(self,fname)(**kwargs)
	@property
	def solve(self): 
		return self.solution
	@property
	def result(self): 
		# an alias for solve
		# instantiating a Handler subclass runs the function
		# the solve, result properties return the result
		return self.solution
