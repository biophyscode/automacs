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
	# getargspec will be deprecated by Python 3.6
	if sys.version_info<(3,3): 
		if isinstance(func,str_types): raise Exception(messsage)
		args,varargs,varkw,defaults = inspect.getargspec(func)
		if defaults: 
			std,var = args[:-len(defaults)],args[-len(defaults):]
			packed = dict(args=tuple(std),kwargs=dict(zip(var,defaults)))
		else: packed = dict(args=tuple(args),kwargs={})
		return packed
	else:
		#! might need to validate this section for python 3 properly
		sig = inspect.signature(func) # pylint: disable=no-member
		packed = {'args':tuple([key for key,val in sig.parameters.items() 
			if val.default==inspect._empty])}
		keywords = [(key,val.default) for key,val in sig.parameters.items() 
			if val.default!=inspect._empty]
		packed['kwargs'] = dict(keywords)
		return packed

class Handler(object):
	taxonomy = {}
	def classify(self,*args):
		matches = [name for name,keys in self.taxonomy.items() if (
			(isinstance(keys,set) and keys==set(args)) or 
			(isinstance(keys,dict) and set(keys.keys())=={'base','opts'} 
				and (set(args)-keys['opts'])==keys['base']
				and (set(args)-keys['base'])<=keys['opts']))]
		if len(matches)==0: 
			raise Exception(
				('cannot classify instructions with keys: %(args)s. '
					'be careful with the "name" keyword, which is not allowed'
				if not self.classify_fail else self.classify_fail)%
				{'args':args})
		elif len(matches)>1: 
			raise Exception('redundant matches: %s'%matches)
		else: return matches[0]
	def _taxonomy_inference(self):
		"""
		Infer a taxonomy from constituent functions. The taxonomy enumerates
		which functions are called when required (base) and optional (opts)
		arguments are supplied. Historically we set the class attribute 
		taxonomy to specify this, but we infer it here.
		"""
		_protected = {'classify','__init__'}
		methods = dict([(i,j) for i,j in 
			inspect.getmembers(self,predicate=inspect.ismethod)
			if i not in _protected])
		expected = dict([(name,introspect_function(methods[name])) 
			for name in methods])
		#! this is not useful in python 3 because the self argument is 
		#!   presumably ignored by the introspection
		if sys.version_info<(3,0):
			for name,expect in expected.items():
				if 'self' not in expect['args']:
					print('debug expect=%s'%expect)
					raise Exception('function "%s" lacks the self argument'%
						name)
		# convert to a typical taxonomy structure
		self.taxonomy = dict([(name,{
			'base':set(expect['args'])-set(['self']),
			'opts':set(expect['kwargs'].keys())
			}) for name,expect in expected.items()
			if not name.startswith('_')])
	def __init__(self,name=None,meta=None,
		classify_fail=None,inspect=False,**kwargs):
		# leaving taxonomy blank means that it is inferred from args,kwargs
		#   of the constitutent methods in the class
		if not self.taxonomy: self._taxonomy_inference()
		# allow a blank instance of a Handler subclass, sometimes necessary
		#   to do the taxonomy_inference first
		#! note that some use-case for Handler needs to be updated with inspect
		#!   in which we need the taxonomy beforehand. perhaps a replicator?
		if not kwargs and inspect: return
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
