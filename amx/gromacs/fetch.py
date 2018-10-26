#!/usr/bin/env python

import sys

def get_pdb(code,path=None):
	"""
	Download a PDB from the database or copy from file.
	"""
	#!!! needs tested/extended
	#! previous version of this function checked some path for an already-downloaded copy
	#!   this might be worth adding back in. it also extracted the sequence 
	if sys.version_info<(3,0): from urllib2 import urlopen
	else: from urllib.request import urlopen
	response = urlopen('http://www.rcsb.org/pdb/files/'+code+'.pdb')
	pdbfile = response.read()
	if path==None: dest = state.here+'start-structure.pdb'
	else: 
		if os.path.isdir(path): dest = os.path.join(path,code+'.pdb')
		else: dest = path
	with open(dest,'w') as fp: fp.write(pdbfile.decode())
	#! we should log that the PDB was successfully got
