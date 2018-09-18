#!/usr/bin/env python

class Handler:
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
