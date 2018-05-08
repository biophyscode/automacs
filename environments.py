#!/usr/bin/env python

from __future__ import print_function
from __future__ import unicode_literals
import sys,os

class Factory:
	def __init__(self,*args,**kwargs):
		self.where = kwargs.pop('where','./env')
		if not self.env_exists(): print('environment %s does not exist'%self.where)
		else: print('status','found environment at %s'%self.where)
	def env_exists(self):
		return os.path.isfile(self.where)

def manage(*args,**kwargs): 
	Factory(*args,**kwargs)
