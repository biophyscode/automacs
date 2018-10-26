#!/usr/bin/env python

import os,shutil,sys

def get_start_structure(path):
	"""
	Get a start structure or auto-detect a PDB in the inputs.
	"""
	if path: altpath = os.path.join(globals().get('expt',{}).get('cwd_source','./'),path)
	else: altpath = None
	if path and os.path.isfile(path): fn = path
	elif altpath and os.path.isfile(altpath): fn = altpath
	else: 
		fns = glob.glob('inputs/*.pdb')
		if len(fns)>1: raise Exception('multiple PDBs in inputs')
		elif len(fns)==0: raise Exception('no PDBs in inputs')
		else: fn = fns[0]
	shutil.copy(fn,os.path.join(state.here,''))
	shutil.copyfile(fn,os.path.join(state.here,'start-structure.pdb'))
