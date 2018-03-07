#!/usr/bin/env python

"""
A collection of generic GROMACS interface functions.
"""

#---! central location
def delve(o,*k): 
	"""Read a nested dictionary like a tree."""
	return delve(o[k[0]],*k[1:]) if len(k)>1 else o[k[0]]

def component(name,count=None,top=False):
	"""
	Add or modify the composition of the system and return the count if none is provided.
	"""
	#---start a composition list if absent
	if 'composition' not in state: 
		state.composition = []
		try: state.composition.append([name,int(count)])
		except: raise Exception('[ERROR] the first time you add a component you must supply a count')
	#---if count is supplied then we change the composition
	names = list(zip(*state.composition))[0]
	if count != None:
		if name in names: state.composition[names.index(name)][1] = int(count)
		else: 
			if top: state.composition.insert(0,[name,int(count)])
			else: state.composition.append([name,int(count)])
	#---return the requested composition
	names = list(zip(*state.composition))[0]
	return state.composition[names.index(name)][1]

def include(name,ff=False):
	"""
	Add an ITP file to the itp (non-ff includes) list but avoid redundancies 
	which cause errors in GROMACS.
	"""
	which = 'ff_includes' if ff else 'itp'
	if which not in state: state[which] = []
	if name not in state[which]: state[which].append(name)
