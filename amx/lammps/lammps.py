#!/usr/bin/env python

"""
INTERFACE TO LAMMPS
"""

import copy,re

def lammps_get_call():
	"""
	Get the instructions for calling LAMMPS.
	"""
	#---piggybacking off GROMACS configuration which is fairly general anyway
	machine_config = gmx_get_machine_config()
	caller = copy.deepcopy(machine_config.get('lammps',{}))
	#---! custom internal regex substitution method needs to be generalized then you move the 
	#---! ...machine configuration to a more central place in automacs
	#---! note that upper doesn't work in a string so it must be explicit here for now!
	injector = lambda x : '@%s'%(str(x).upper())
	call = caller.pop('call','lammps')
	for key,val in caller.items(): call = re.sub(injector(key),str(val),call)
	return call

def lammps_run_simple(script):
	"""
	Run a LAMMPS script with overriding variables from settings.
	needs:
	-- state needs better history of the call! put this in init!
	-- path from config
	"""
	injector = eval(settings.get('injector',"lambda x : '@%s'%x"))
	fn = os.path.basename(script)
	with open(script) as fp: text = fp.read()
	subs = settings.get('variables',{})
	for key,val in subs.items(): text = re.sub(injector(key),str(val),text,flags=re.M+re.DOTALL)
	with open(os.path.join(state.here,fn),'w') as fp: fp.write(text)
	bash('%s -in %s'%(lammps_get_call(),fn),cwd=state.here,show=True)
