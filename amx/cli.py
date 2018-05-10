#!/usr/bin/env python

"""
AUTOMACS command-line interface
"""

__all__ = ['prep','clean']

import ortho
from runner import prep
import shutil,os,sys,glob,re

def cleanup(sure=False):
	"""
	Clean files from the current directory.
	"""
	config = ortho.conf
	if 'cleanup' not in config: raise Exception('configuration is missing cleanup instructions')
	fns = []
	for pat in config['cleanup']: fns.extend(glob.glob(pat))
	if sure or all(re.match('^(y|Y)',(input if sys.version_info>(3,0) else raw_input)
		('question','%s (y/N)? '%msg))!=None for msg in ['okay to remove','confirm']):
		for fn in fns: 
			if os.path.isfile(fn): os.remove(fn)
			else: shutil.rmtree(fn)

def clean(sure=False): cleanup(sure=sure)
