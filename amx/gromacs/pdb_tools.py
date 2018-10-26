#!/usr/bin/env python

import os,re

def remove_hetero_atoms(structure,out):
	"""
	Remove heteroatoms from a PDB.
	"""
	if not os.path.isfile(state.here+structure): 
		raise Exception('cannot find input %s'%(state.here+structure))
	with open(state.here+structure) as fp: original = fp.read()
	if os.path.isfile(state.here+out): raise Exception('refusing to overwrite %s'%(state.here+out))
	with open(state.here+out,'w') as fp: 
		fp.write('\n'.join(i for i in original.splitlines() if re.match('^ATOM',i)))
