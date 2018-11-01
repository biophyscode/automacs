#!/usr/bin/env python

"""
Use ortho MultiDict objects to represent the "state" in automacs.
We add minor modifications to MultiDict in order to ensure keys do not have underscores.
That feature is currently not canon in ortho.dictionary.
"""

from __future__ import print_function
import re,sys
from ortho.dictionary import MultiDict,DotDict

class AMXState(MultiDict):
	def __init__(self,*args,**kwargs):
		super(AMXState,self).__init__(*args,**kwargs)
		self._protect.add('q')
	def q(self,*args,**kwargs):
		"""Legacy AUTOMACS used q in place of get because immature code. Retain this for compatibility."""
		#! consider retiring this function. we want the code to look pythonic. AMXState shoud resemble dict
		return self.get(*args,**kwargs)

def amx_excepthook(type,value,tb,state):
	"""On exception we dumpt the state with automatic debugging if terminal."""
	state._dump('state.json',overwrite=True)
	# debugging via https://stackoverflow.com/questions/242485
	if hasattr(sys, 'ps1') or not sys.stderr.isatty():
		sys.__excepthook__(type,value,tb)
	else:
		import traceback, pdb
		traceback.print_exception(type,value,tb)
		print('debug','welcome to the debugger')
		pdb.post_mortem(tb)
