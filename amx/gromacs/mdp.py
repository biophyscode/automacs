#!/usr/bin/env python

import os,re,sys
from copy import deepcopy
#---amx is already in the path when importing amx/gromacs
from ortho import str_types

_not_reported = ['deepcopy']

def write_mdp(param_file=None,rootdir='./',outdir='',extras=None,verbose=False):

	"""
	Universal MDP file writer which creates input files based on a unified dictionary.
	All MDP parameters should be stored in *mdpdefs* within ``inputs/input_specs_mdp.py``. 
	We assemble MDP files according to rules that can be found in the *mdp* entry for the specs 
	dictionary contained in the ``input_specs_PROCEDURE.py`` file. Other simulation steps may 
	use this function to access the mdp_section entry from the same specs dictionary in order 
	to write more MDP files for e.g. equilibration steps.

	In the ``inputs/input_specs_mdp.py`` file we define the "mdpdefs" (read: Molecular Dynamics 
	Parameter DEFinitionS) dictionary, which is a customizable description of how to run the GROMACS 
	integrator. The mdpdefs variable has a few specific kinds of entries denoted by comments and
	and described here.
	
	The top level of mdpdefs is a "group" set in the *mdp* entry of the specs dictionary. This allows us
	to organize our parameters into distinct groups depending on the task. For example, we might have 
	different groups of parameters for coarse-grained and atomistic simulations. We whittle the full
	mdpspecs dictionary by the group name below.
	
	Our whittled dictionary then contains three kinds of entries.
	
	1. The entry called ``defaults`` is a dictionary which tells you which dictionaries to use if no extra information 
		is provided. Each key in the defaults dictionary describes a type of parameters (e.g. 
		"output" refers to the parameters that specify how to write files). If the associated value is "None" 
		then we assume that the key is found at the top level of mdpdefs. Otherwise the value allows us to 
		descend one more level and choose between competing sets of parameters.
	2. Other entries with keys defined in ``defaults`` contain either a single dictionary for that default 
		(recall that we just use None to refer to these) or multiple dictionaries with names referred to by 
		the defaults. These entries are usually grouped by type e.g. output or coupling parameters.
	3. Override keys at the top level of mdpdefs which do not appear in defaults contain dictionaries which 
		are designed to override the default ones wholesale. They can be used by including their names in the 
		list associated with a particular mdp file name in specs. If they contain a dictionary, then this 
		dictionary will override the default dictionary with that key. Otherwise, they should contain 
		key-value pairs that can lookup a default in the same way that the defaults section does.
	
	Except for the "group" entry, the specs key mdp_section (remember that this is defined in 
	``input_specs_PROCEDURE.py``) should include keys with desired MDP file names pointing to lists that 
	contain override keys and dictionaries. If you include a dictionary in the value for a particular MDP 
	file then its key-value pairs will either override an MDP setting directly or override a key-value
	pair in the defaults.
	Note that this function was updated from the original automacs to be more explicit.
	"""

	#---! we should use jsonify on parameters.py to check for repeated keys !
	#---get mdp specs from the settings unless overridden by the call

	#mdpspecs = state.get('mdp_specs',{}) if not extras else ([] if not extras else extras)
	mdpspecs = settings.get('mdp_specs',state.get('mdp_specs',{}))
	mdpspecs = extras if extras else mdpspecs

	#---retrieve the master inputs file
	mdpfile = {}
	#---figure out the path to the parameter file
	if not param_file: 
		if re.match('^@',expt.params): 
			from runner.acme import get_path_to_module
			param_file = get_path_to_module(expt.params)
		#---if no module syntax then the path must be local
		else: param_file = param_file = os.path.join(expt.meta['cwd'],expt.params)
	#---path lookups from config.py are triggerd with the "@" syntax
	with open(param_file) as fp: param_text = fp.read()
	#---eval the param_file otherwise exec tuple errors in python <2.7.9 
	#---make sure that the parameter file only contains a dictionary (easier than forcing a variable name)
	mdpdefs = eval(param_text)

	#---STEP 1:	whittle the master dictionary according the group keyword
	if type(mdpspecs) in str_types:
		raise Exception('mdpspecs must be a dictionary but instead it is a string. '+
			'there is probably a syntax error in your settings block')
	group_name = mdpspecs.get('group',None)
	if group_name:
		if group_name not in mdpdefs:
			raise Exception('cannot find user-requested group %s in mdp_specs'%group_name)
		else: mdpdefs = mdpdefs[group_name]

	#---check target MDP names
	target_mdps = mdpspecs.get('mdps',None)
	if not target_mdps: raise Exception('cannot find any mdps in mdp_specs')
	mdps_misnamed = [i for i in target_mdps if not re.match('.+\.mdp$',i)]
	if any([i for i in target_mdps if not re.match('.+\.mdp$',i)]):
		raise Exception('all mdp files must have the mdp file extension: %s'%str(mdps_misnamed))

	for mdpname in target_mdps:
		settings_this = {}
		#---run through defaults and add them to our MDP file dictionary
		#---the defaults list contains keys that name essential sections of every MDP file
		for key,val in mdpdefs['defaults'].items():
			#---if default says None then we get the parameters for that from the top level
			if val==None: settings_this[key] = deepcopy(mdpdefs[key])
			else: settings_this[key] = deepcopy(mdpdefs[key][val])
		#---refinements are given in the mdpspecs dictionary
		if mdpspecs['mdps'][mdpname] != None:
			#---all refinements should be a list of strings and dictionaries so we promote a dict to list
			refine_loop = mdpspecs['mdps'][mdpname]
			refine_loop = [refine_loop] if type(refine_loop) in [dict]+str_types else refine_loop
			for refinecode in refine_loop:
				#---if the refinement code in the list given at mdpspecs[mdpname] is a string then we
				#---...navigate to mdpdefs[refinecode] and use its children to override settings_this[key] 
				if type(refinecode) in str_types:
					for key,val in mdpdefs[refinecode].items():
						#---if the value for an object in mdpdefs[refinecode] is a dictionary, we 
						#---...replace settings_this[key] with that dictionary
						if type(val)==dict: settings_this[key] = deepcopy(val)
						#---otherwise the value is really a lookup code and we search for a default value
						#---...at the top level of mdpdefs where we expect mdpdefs[key][val] to be 
						#---...a particular default value for the MDP heading given by key
						elif type(val) in str_types: settings_this[key] = deepcopy(mdpdefs[key][val])				
						else: raise Exception('unclear refinecode = '+refinecode+', '+key+', '+str(val))
				#---if the refinement code is a dictionary, we iterate over each rule
				else:
					for key2,val2 in refinecode.items():
						settings_this_flat = [j for k in [settings_this[i].keys() for i in settings_this] for j in k]
						#---if the rule is in the top level of mdpdefs then it selects groups of settings_this
						if key2 in mdpdefs.keys(): 
							if verbose: print('[NOTE] using MDP override collection: '+key2+': '+str(val2))
							settings_this[key2] = deepcopy(mdpdefs[key2][val2])
						#---if not, then we assume the rule is meant to override a native MDP parameter
						#---...so we check to make sure it's already in settings_this and then we override
						elif key2 in settings_this_flat:
							if verbose: print('[NOTE] overriding MDP parameter: '+key2+': '+str(val2))
							for sub in settings_this:
								if key2 in settings_this[sub]: settings_this[sub][key2] = deepcopy(val2)
						else: 
							#---! note that GROMACS parameters might be case-insensitive
							raise Exception(
								'cannot comprehend one of your overrides: "%r"="%r"'%(key2,val2)+
								'\nnote that the settings_this list is: "%r"'%settings_this_flat)
		#---completely remove some items if they are set to -1, specifically the flags for trr files
		for key in ['nstxout','nstvout']:
			for heading,subset in settings_this.items():
				if key in subset and subset[key] == -1: subset.pop(key)
		#---always write to the step directory
		with open(os.path.join(rootdir,state.here+mdpname),'w') as fp:
			for heading,subset in settings_this.items():
				if subset: fp.write('\n;---'+heading+'\n')
				for key,val in subset.items():
					fp.write(str(key)+' = '+str(val)+'\n')

