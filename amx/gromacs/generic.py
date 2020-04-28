#!/usr/bin/env python

import os,shutil,sys,glob,re

def get_start_structure(path):
	"""
	Get a start structure or auto-detect a single PDB in the inputs folder.
	"""
	# note that passing islink without isfile means broken link
	if path: 
		altpath = os.path.join(globals().get(
			'expt',{}).get('cwd_source','./'),path)
	else: altpath = None
	if path and os.path.isfile(os.path.expanduser(path)):
		fn = os.path.expanduser(path)
	elif altpath and os.path.isfile(os.path.expanduser(altpath)): 
		fn = os.path.expanduser(altpath)
	else: 
		fns = glob.glob('inputs/*.pdb')
		if len(fns)>1: raise Exception('multiple PDBs in inputs')
		elif len(fns)==0: raise Exception('no PDBs in inputs')
		else: fn = fns[0]
	shutil.copy(fn,os.path.join(state.here,''))
	shutil.copyfile(fn,os.path.join(state.here,'start-structure.pdb'))

def interpret_start_structure():
	"""
	Standard interface to a start_structure key in the settings which checks to
	see if it's a PDB or copies it from a relative path. The default value will
	trigger a check for a single PDB file in the inputs folder.
	"""
	# note that passing islink without isfile means broken link
	# check for PDB code or path
	#! port this to protein.py
	is_pdb = (settings.start_structure!=None 
		and re.match('^[A-Za-z0-9]{4}$',settings.start_structure.strip())!=None)
	is_path = (settings.start_structure==None 
		or os.path.isfile(os.path.expanduser(settings.start_structure)))
	if is_path + is_pdb != 1:
		raise Exception(
			'is_pdb = %s, is_path = %s, settings.start_structure = %s'%(
			is_path,is_pdb,settings.start_structure))
	# collect the structure
	if is_path or settings.start_structure==None:
		#! fix the above
		get_start_structure(settings.start_structure)
	elif is_pdb:
		# clean the PDB code here
		settings.start_structure = settings.start_structure.strip().upper()
		get_pdb(settings.start_structure)
