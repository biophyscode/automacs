#!/usr/bin/env python

import inspect,sys
from .misc import str_types
from .misc import treeview

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
		double_star = [i for i in sig.parameters 
			if str(sig.parameters[i]).startswith('**')]
		if double_star: packed['**'] = double_star
		return packed

class Handler(object):
	_taxonomy = {}
	# internals map to special structures in the Handler level
	_internals = {'name':'name','meta':'meta'}
	# whether to allow inexact matching (we still prefer strict matching)
	lax = True
	def _report(self):
		print('debug Handler summary follows')
		print(
			'debug the Handler parent class allows the child to define methods '
			'one of which is automatically called with the args and kwargs '
			'given to the child class constructor. The _protected keys are '
			'diverted into attributes common to all child clas instances. For '
			'example the name and meta flags are common to all.')
		print('debug _protected keys not sent to methods: %s'%
			list(self._internals.keys()))
		if not self._taxonomy: print('debug There are no methods.')
		else: 
			for k,v in self._taxonomy.items():
				print('debug A method named "%s" has arguments: %s'%(k,v))
	def _matchless(self,args):
		"""Report that we could not find a match."""
		#! note that we need a more strict handling for the name keyword
		#!   which incidentally might be worth retiring
		name_child = self.__class__.__name__ 
		self._report()
		raise Exception(
			('%(name)s cannot classify instructions with '
				'keys: %(args)s. See the report above for details.'
			if not self.classify_fail else self.classify_fail)%
			{'args':args,'name':name_child})
	def _classify(self,*args):
		matches = [name for name,keys in self._taxonomy.items() if (
			(isinstance(keys,set) and keys==set(args)) or 
			(isinstance(keys,dict) and set(keys.keys())=={'base','opts'} 
				and (set(args)-keys['opts'])==keys['base']
				and (set(args)-keys['base'])<=keys['opts']))]
		if len(matches)==0: 
			if not self.lax: self._matchless(args)
			else:
				# collect method target that accept spillovers
				# where spillover means we have extra kwargs going to **kwargs
				# and not that we do not allow arguments in this dev stage
				spillovers = [i for i,j in self._taxonomy.items() 
					if j.get('kwargs',False)]
				spills = [(i,
					set.difference(set(args),set.union(j['base'],j['opts']))) 
					for i,j in self._taxonomy.items() if i in spillovers]
				if not spills: self._matchless(args)
				scores = dict([(i,len(j)) for i,j in spills])
				try: score_min = min(scores.values())
				except:
					import ipdb;ipdb.set_trace()
				matches_lax = [i for i,j in scores.items() if j==score_min]
				if len(matches_lax)==0: self._matchless(args)
				elif len(matches_lax)==1: return matches_lax[0]
				else:
					# if we have redundant matches and one is the default
					#   then the default is the tiebreaker
					#! the following logic needs to be checked more carefully
					if self._default and self._default in matches_lax: 
						return self._default
					# if no default tiebreaker we are truly stuck
					self._report()
					raise Exception('In lax mode we have redundant matches. '
						'Your arguments (%s) are equally compatible with these '
						'methods: %s'%(list(args),matches_lax))
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
		# note that all functions that start with "_" are invalid target methods
		methods = dict([(i,j) for i,j in 
			inspect.getmembers(self,predicate=inspect.ismethod)
			if not i.startswith('_')])
		expected = dict([(name,introspect_function(methods[name])) 
			for name in methods])
		# decorated handler subclass methods should save introspect as an attr
		for key in methods:
			if hasattr(methods[key],'_introspected'): 
				expected[key] = methods[key]._introspected
		#! this is not useful in python 3 because the self argument is 
		#!   presumably ignored by the introspection
		if sys.version_info<(3,0):
			for name,expect in expected.items():
				if 'self' not in expect['args']:
					print('debug expect=%s'%expect)
					raise Exception('function "%s" lacks the self argument'%
						name)
		# convert to a typical taxonomy structure
		self._taxonomy = dict([(name,{
			'base':set(expect['args'])-set(['self']),
			'opts':set(expect['kwargs'].keys())
			}) for name,expect in expected.items()
			if not name.startswith('_')])
		"""
		exceptions to the taxonomy
		any functions with kwargs as a base argument via "**kwargs" are allowed
		to accept any arbitrary keyword arguments, as is the 
		"""
		for key in self._taxonomy:
			if ('kwargs' in self._taxonomy[key]['base'] 
				and 'kwargs' in expected[key].get('**',[])):
				self._taxonomy[key]['base'].remove('kwargs')
				self._taxonomy[key]['kwargs'] = True
		# check for a single default handler that only accespts **kwargs
		defaults = [i for i,j in self._taxonomy.items() 
			if j.get('kwargs',False) and len(j['base'])==0 
			and len(j['opts'])==0]
		if len(defaults)>1: 
			raise Exception('More than one function accepts only **kwargs: %s'%defaults)
		elif len(defaults)==1: self._default = defaults[0]
		else: self._default = None
		# check valid taxonomy
		# note that using a protected keyword in the method arguments can
		#   be very confusing. for example, when a method that takes a name
		#   is used, the user might expect name to go to the method but instead
		#   it is intercepted by the parent Handler class and stored as an
		#   attribute. hence we have a naming table called _internals and we
		#   protect against name collisions here
		collisions = {}
		for key in self._taxonomy:
			argnames = (list(self._taxonomy[key]['base'])+
				list(self._taxonomy[key]['opts']))
			collide = [i for i in self._internals.values()
				if i in argnames]
			if any(collide): collisions[key] = collide
		if any(collisions):
			# we print the internals so you can see which names you cannot use
			print('debug internals are: %s'%self._internals)
			raise Exception((
				'Name collisions in %s (Handler) method '
				'arguments: %s. See internals above.')%(
					self.__class__.__name__,collisions))
		fallbacks = []
	def __init__(self,*args,**kwargs):
		if args: 
			raise Exception(
				'Handler classes cannot receive arguments: %s'%list(args))
		classify_fail = kwargs.pop('classify_fail',None)
		inspect = kwargs.pop('inspect',False)
		# safety check that internals include the values we require
		#   including a name and a meta target
		required_internal_targets = set(['meta','name'])
		if not set(self._internals.keys())==required_internal_targets:
			raise Exception(
				'Handler internals must map to %s but we received: %s'%(
				required_internal_targets,set(self._internals.keys())))
		name = kwargs.pop(self._internals['name'],None)
		meta = kwargs.pop(self._internals['meta'],{})
		self.meta = meta if meta else {}
		#! name is a common key. how are we using it here?
		if not name: self.name = "UnNamed"
		else: self.name = name
		# kwargs at this point are all passed to the subclass method
		# leaving taxonomy blank means that it is inferred from args,kwargs
		#   of the constitutent methods in the class
		if not self._taxonomy: self._taxonomy_inference()
		# allow a blank instance of a Handler subclass, sometimes necessary
		#   to do the taxonomy_inference first
		#! note that some use-case for Handler needs to be updated with inspect
		#!   in which we need the taxonomy beforehand. perhaps a replicator?
		if not kwargs and inspect: return
		self.classify_fail = classify_fail
		fname = self._classify(*kwargs.keys())
		self.style = fname
		self.kwargs = kwargs
		if not hasattr(self,fname): 
			raise Exception(
				'development error: taxonomy name "%s" is not a member'%fname)
		# before we run the function to generate the object, we note the 
		#   inherent attributes assigned by Handler, the parent, so we can
		#   later identify the novel keys
		self._stock = dir(self)+['_stock','solution']
		# introspect on the function to make sure the keys 
		#   in the taxonomy match the available keys in the function?
		self.solution = getattr(self,fname)(**kwargs)
		# make a list of new class attributes set during the method above
		self._novel = tuple(set(dir(self)) - set(self._stock))
	def __repr__(self):
		"""Look at the subclass-specific parts of the object."""
		#! this is under development
		if hasattr(self,'_novel'): 
			report = dict(object=dict(self=dict([(i,getattr(self,i)) for i in self._novel])))
			if self.meta: report['object']['meta'] = self.meta
			report['object']['name'] = self.name
			treeview(report) #! is it silly to print trees?
			return "%s [a Handler]"%self.name
		else: return super(Handler,self).__repr__()
	@property
	def solve(self): 
		return self.solution
	@property
	def result(self): 
		# an alias for solve
		# instantiating a Handler subclass runs the function
		# the solve, result properties return the result
		return self.solution
