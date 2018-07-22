#!/usr/bin/env python

"""
Use ortho MultiDict objects to represent the "state" in automacs.
We add minor modifications to MultiDict in order to ensure keys do not have underscores.
That feature is currently not canon in ortho.dictionary.
"""

import re
from ortho.dictionary import MultiDict,DotDict

class AMXState(MultiDict):
	def __init__(self,*args,**kwargs):
		super(AMXState,self).__init__(*args,**kwargs)
		self._protect.add('q')
	def q(self,*args,**kwargs):
		"""Legacy AUTOMACS used q in place of get because immature code. Retain this for compatibility."""
		#! consider retiring this function. we want the code to look pythonic. AMXState shoud resemble dict
		return self.get(*args,**kwargs)
