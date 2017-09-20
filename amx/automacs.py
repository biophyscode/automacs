#!/usr/bin/env python

from calls import get_gmx_paths,gmx,get_last_gmx_call

"""
Automacs library for automatic GROMACS simulations.
Note: this docstring is not caught by sphinx.
"""

_not_reported = ['deepcopy']

import os,sys,shutil,glob,re,json
from copy import deepcopy

#---command formulations
#---note gromacs has a tricky syntax for booleans so 
#---...we use TRUE and FALSE which map to -flag and -noflag
gmx_call_templates = """
pdb2gmx -f STRUCTURE -ff FF -water WATER -o GRO.gro -p system.top -i BASE-posre.itp -missing TRUE -ignh TRUE
editconf -f STRUCTURE.gro -o GRO.gro
grompp -f MDP.mdp -c STRUCTURE.gro -p TOP.top -o BASE.tpr -po BASE.mdp
mdrun -s BASE.tpr -cpo BASE.cpt -o BASE.trr -x BASE.xtc -e BASE.edr -g BASE.log -c BASE.gro -v TRUE
genbox -cp STRUCTURE.gro -cs SOLVENT.gro -o GRO.gro
solvate -cp STRUCTURE.gro -cs SOLVENT.gro -o GRO.gro
make_ndx -f STRUCTURE.gro -o NDX.ndx
genion -s BASE.tpr -o GRO.gro -n NDX.ndx -nname ANION -pname CATION
trjconv -f STRUCTURE.gro -n NDX.ndx -center TRUE -s TPR.tpr -o GRO.gro
genconf -f STRUCTURE.gro -nbox NBOX -o GRO.gro
"""

###---STATE VARIABLES

def register(func):

	"""
	Collect utility functions in the state.
	[Typically this would be a decorator, but the import scheme makes that unworkable.]
	"""

	fname = func.__name__
	if '_funcs' not in state: state._funcs = []
	#if fname in state: raise Exception('state already had function %s'%fname)
	state._funcs.append(fname)
	state[fname] = func

def q(key,val=None):

	"""
	Check either settings or the state for a variable name.
	This takes the place of (indiscriminately) loading all settings into the state.
	"""

	return state.get(key,settings.get(key,val))

def component(name,count=None,top=False):

	"""
	component(name,count=None)
	Add or modify the composition of the system and return the count if none is provided.
	Originally designed for protein_atomistic.py.
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
	include(name)
	Add an ITP file to the itp (non-ff includes) list but avoid redundancies 
	which cause errors in GROMACS.
	"""

	which = 'ff_includes' if ff else 'itp'
	if 'itp' not in state: state[which] = []
	if name not in state[which]: state[which].append(name)

def init():
	"""
	Initialize the automacs state.
	Note that all automacs variables are defined here.
	Structure of the state Cursors: here = current directory with trailing slash 
	step = current step name
	stepno = current step number
	History: steps = list of steps in order
	State-only interactors: calls.py make_step
	"""
	print('[STATUS] initializing automacs')
	#---figure out the right paths for gromacs execution
	get_gmx_paths()
	#---interpret the call templates
	if type(gmx_call_templates)==str: state.gmxcalls = commands_interpret(gmx_call_templates)
	else: state.gmxcalls = gmx_call_templates
	#---previously registered `gmx` and `component` here before implementing advanced import scheme
	#---we register signal functions that should not be serialized and stored in the state.json
	register(q)
	#---check for previous states
	prev_states = glob.glob('state_*.json')
	if prev_states: 
		state.before = []
		for fn in sorted(prev_states):
			with open(fn) as fp: state.before.append(json.load(fp))
	#---store settings for posterity minus the _protect
	state.settings = dict(settings)
	state.expt = dict(expt)
	#---no need to save the _protect list from the DotDict here
	del state.settings['_protect']
	del state.expt['_protect']

###---COMMAND INTERPRETATIONS

def commands_interpret_deprecated(block):

	"""
	Interpret a block of command templates for GROMACS.
	"""

	commands = {}
	for line in block.split('\n'):
		if not re.match('^\s*$',line):
			utility = re.findall('^([gmx\s+]?\w+)',line).pop() 
			flags_string = re.findall('^[gmx\s+]?\w+\s*(.+)',line).pop() 
			flags = flags_string.split()
			try: specs = dict([flags[2*i:2*i+2] for i in range(int(len(flags)/2))])
			except:
				import ipdb;ipdb.set_trace()
			commands[utility] = specs
	return commands

def commands_interpret(templates):
	"""
	"""
	gmxcalls = {}
	for raw in [i for i in templates.splitlines() if not re.match('^\s*$',i)]:
		extract = re.match('^(\w+)\s+(.*?)$',raw)
		command,flags = extract.groups()
		flags_extracted = []
		while flags:
			this_match = re.match('^\s*(-[a-z]+)\s+(.*?)\s*(?=\s-[a-z]|$)',flags)
			if not this_match: break
			groups = this_match.groups()
			if flags_extracted and groups[0] in list(zip(*flags_extracted))[0]:
				raise Exception('found repeated flag %s in the command templates'%groups[0])
			flags_extracted.append(groups)
			flags = this_match.string[:this_match.start()]+this_match.string[this_match.end():]
		#---convert True/False to the gromacs boolean notation: -flag vs -noflag
		for ii,i in enumerate(flags_extracted):
			if i[1].upper() in ['TRUE','FALSE']:
				if re.match('^no',i[0]): 
					raise Exception('refusing to accept a kwarg to a gmx flag that starts with "no": '%i[0])
				if i[1].upper() == 'TRUE': flags_extracted[ii] = (i[0],'')
				elif i[1].upper() == 'FALSE': flags_extracted[ii] = (re.sub('^-(.+)$',r'-no\1',i[0]),'')
		args_required = []
		def replace_name(x):
			abstract_name = x.group(1)
			args_required.append(abstract_name.lower())
			return r"%("+abstract_name.lower()+r")s"
		flags = list(flags_extracted)
		for flagno,flag in enumerate(flags):
			result,count = re.subn('([A-Z]+)',replace_name,flag[1])
			#---! check count?
			flags[flagno] = (flag[0],result)
		gmxcalls[command] = {'command':command,'flags':flags,'required':list(set(args_required))}
	return gmxcalls

###---INPUT PARAMETERS

def delve(o,*k): return delve(o[k[0]],*k[1:]) if len(k)>1 else o[k[0]]

def write_mdp(param_file=None,rootdir='./',outdir='',extras=None):

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

	str_types = [str] if sys.version_info>(3,0) else [str,unicode]

	#---get mdp specs from the settings unless overridden by the call
	mdpspecs = state.q('mdp_specs',[]) if not extras else ([] if not extras else extras)

	#---retrieve the master inputs file
	mdpfile = {}
	#---figure out the path to the parameter file
	if not param_file: 
		if re.match('^@',expt.params): 
			from runner.acme import get_path_to_module
			param_file = get_path_to_module(expt.params)
		#---if no module syntax then the path must be local
		else: param_file = param_file = os.path.join(expt.cwd_source,expt.params)
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
		settings = {}
		#---run through defaults and add them to our MDP file dictionary
		#---the defaults list contains keys that name essential sections of every MDP file
		for key,val in mdpdefs['defaults'].items():
			#---if default says None then we get the parameters for that from the top level
			if val==None: settings[key] = deepcopy(mdpdefs[key])
			else: settings[key] = deepcopy(mdpdefs[key][val])
		#---refinements are given in the mdpspecs dictionary
		if mdpspecs['mdps'][mdpname] != None:
			#---all refinements should be a list of strings and dictionaries so we promote a dict to list
			refine_loop = mdpspecs['mdps'][mdpname]
			refine_loop = [refine_loop] if type(refine_loop) in [dict]+str_types else refine_loop
			for refinecode in refine_loop:
				#---if the refinement code in the list given at mdpspecs[mdpname] is a string then we
				#---...navigate to mdpdefs[refinecode] and use its children to override settings[key] 
				if type(refinecode) in str_types:
					for key,val in mdpdefs[refinecode].items():
						#---if the value for an object in mdpdefs[refinecode] is a dictionary, we 
						#---...replace settings[key] with that dictionary
						if type(val)==dict: settings[key] = deepcopy(val)
						#---otherwise the value is really a lookup code and we search for a default value
						#---...at the top level of mdpdefs where we expect mdpdefs[key][val] to be 
						#---...a particular default value for the MDP heading given by key
						elif type(val) in str_types: settings[key] = deepcopy(mdpdefs[key][val])				
						else: raise Exception('unclear refinecode = '+refinecode+', '+key+', '+str(val))
				#---if the refinement code is a dictionary, we iterate over each rule
				else:
					for key2,val2 in refinecode.items():
						settings_flat = [j for k in [settings[i].keys() for i in settings] for j in k]
						#---if the rule is in the top level of mdpdefs then it selects groups of settings
						if key2 in mdpdefs.keys(): 
							print('[NOTE] using MDP override collection: '+key2+': '+str(val2))
							settings[key2] = deepcopy(mdpdefs[key2][val2])
						#---if not, then we assume the rule is meant to override a native MDP parameter
						#---...so we check to make sure it's already in settings and then we override
						elif key2 in settings_flat:
							print('[NOTE] overriding MDP parameter: '+key2+': '+str(val2))
							for sub in settings:
								if key2 in settings[sub]: settings[sub][key2] = deepcopy(val2)
						else: 
							#---! note that GROMACS parameters might be case-insensitive
							raise Exception(
								'cannot comprehend one of your overrides: "%r"="%r"'%(key2,val2)+
								'\nnote that the settings list is: "%r"'%settings_flat)
		#---completely remove some items if they are set to -1, specifically the flags for trr files
		for key in ['nstxout','nstvout']:
			for heading,subset in settings.items():
				if key in subset and subset[key] == -1: subset.pop(key)
		#---always write to the step directory
		with open(os.path.join(rootdir,state.here+mdpname),'w') as fp:
			for heading,subset in settings.items():
				fp.write('\n;---'+heading+'\n')
				for key,val in subset.items():
					fp.write(str(key)+' = '+str(val)+'\n')

###---SIMULATION STEPS

def minimize_deprecated(name,method='steep',top=None):

	"""
	minimize(name,method='steep')
	Standard minimization procedure.
	"""

	gmx('grompp',base='em-%s-%s'%(name,method),top=name if not top else re.sub('^(.+)\.top$',r'\1',top),
		structure=name,log='grompp-%s-%s'%(name,method),mdp='input-em-%s-in'%method,skip=True)
	tpr = state.here+'em-%s-%s.tpr'%(name,method)
	if not os.path.isfile(tpr): raise Exception('cannot find %s'%tpr)
	gmx('mdrun',base='em-%s-%s'%(name,method),log='mdrun-%s-%s'%(name,method))
	shutil.copyfile(state.here+'em-'+'%s-%s.gro'%(name,method),state.here+'%s-minimized.gro'%name)

def trim_waters_deprecated(structure='solvate-dense',gro='solvate',gap=3,boxvecs=None,method='aamd',boxcut=True):

	"""
	trim_waters(structure='solvate-dense',gro='solvate',gap=3,boxvecs=None)
	Remove waters within a certain number of Angstroms of the protein.
	#### water and all (water and (same residue as water within 10 of not water))
	note that we vided the solvate.gro as a default so this can be used with any output gro file
	"""

	raise Exception('you cannot use this correctly!')
	use_vmd = state.q('use_vmd',False)
	use_vmd = True
	if (gap != 0.0 or boxcut) and use_vmd:
		if method == 'aamd': watersel = "water"
		elif method == 'cgmd': watersel = "resname %s"%wordspace.sol
		else: raise Exception("\n[ERROR] unclear method %s"%method)
		#---! gap should be conditional and excluded if zero
		vmdtrim = [
			'package require pbctools',
			'mol new %s.gro'%structure,
			'set sel [atomselect top \"(all not ('+\
			'%s and (same residue as %s and within '%(watersel,watersel)+str(gap)+\
			' of not %s)))'%watersel]
		#---box trimming is typical for e.g. atomstic protein simulations but discards anything outside
		if boxcut:
			vmdtrim += [' and '+\
			'same residue as (x>=0 and x<='+str(10*boxvecs[0])+\
			' and y>=0 and y<= '+str(10*boxvecs[1])+\
			' and z>=0 and z<= '+str(10*boxvecs[2])+')']
		vmdtrim += ['"]','$sel writepdb %s-vmd.pdb'%gro,'exit',]			
		with open(wordspace['step']+'script-vmd-trim.tcl','w') as fp:
			for line in vmdtrim: fp.write(line+'\n')
		vmdlog = open(wordspace['step']+'log-script-vmd-trim','w')
		#---previously used os.environ['VMDNOCUDA'] = "1" but this was causing segfaults on green
		p = subprocess.Popen('VMDNOCUDA=1 '+gmxpaths['vmd']+' -dispdev text -e script-vmd-trim.tcl',
			stdout=vmdlog,stderr=vmdlog,cwd=wordspace['step'],shell=True,executable='/bin/bash')
		p.communicate()
		with open(wordspace['bash_log'],'a') as fp:
			fp.write(gmxpaths['vmd']+' -dispdev text -e script-vmd-trim.tcl &> log-script-vmd-trim\n')
		gmx_run(gmxpaths['editconf']+' -f %s-vmd.pdb -o %s.gro -resnr 1'%(gro,gro),
			log='editconf-convert-vmd')
	#---scipy is more reliable than VMD
	elif gap != 0.0 or boxcut:
		import scipy
		import scipy.spatial
		import numpy as np
		#---if "sol" is not in the wordspace we assume this is atomistic and use the standard "SOL"
		watersel = state.q('sol','SOL')
		incoming = read_gro(structure+'.gro')
		#---remove waters that are near not-waters
		is_water = np.array(incoming['residue_names'])==watersel
		is_not_water = np.array(incoming['residue_names'])!=watersel
		water_inds = np.where(is_water)[0]
		not_water_inds = np.where(np.array(incoming['residue_names'])!=watersel)[0]
		points = np.array(incoming['points'])
		residue_indices = np.array(incoming['residue_indices'])
		if gap>0:
			#---previous method used clumsy/slow cdist
			if False:
				#---! needs KDTree optimization
				dists = scipy.spatial.distance.cdist(points[water_inds],points[not_water_inds])
				#---list of residue indices in is_water that have at least one atom with an overlap
				excludes = np.array(incoming['residue_indices'])[is_water][
					np.where(np.any(dists<=gap/10.0,axis=1))[0]]
				#---collect waters not found in the excludes list of residues that overlap with not-water
				#---note that this command fails on redundant residues
				#---this was deprecated because it wasn't working correctly with the new KDTree method below
				surviving_water = np.all((np.all((
					np.tile(excludes,(len(residue_indices),1))!=np.tile(
						residue_indices,(len(excludes),1)).T),axis=1),is_water),axis=0)
			#---use scipy KDTree to find atom names inside the gap
			#---note that order matters: we wish to find waters too close to not_waters
			close_dists,neighbors = scipy.spatial.KDTree(points[water_inds]).query(
				points[not_water_inds],distance_upper_bound=gap/10.0)
			#---use the distances to find the residue indices for waters that are too close 
			excludes = np.array(incoming['residue_indices'])[is_water][np.where(close_dists<=gap/10.0)[0]]
			#---get residues that are water and in the exclude list
			#---note that the following step might be slow
			exclude_res = [ii for ii,i in enumerate(incoming['residue_indices']) 
				if i in excludes and is_water[ii]]
			#---copy the array that marks the waters
			surviving_water = np.array(is_water)
			#---remove waters that are on the exclude list
			surviving_water[exclude_res] = False
		else: 
			excludes = np.array([])
			surviving_water = np.ones(len(residue_indices)).astype(bool)
		#---we must remove waters that lie outside the box if there is a boxcut
		insiders = np.ones(len(points)).astype(bool)
		if boxcut:
			#---remove waters that lie outside the box
			#---get points that are outside of the box
			outsiders = np.any([np.any((points[:,ii]<0,points[:,ii]>i),axis=0) 
				for ii,i in enumerate(boxvecs)],axis=0)
			#---get residue numbers for the outsiders
			outsiders_res = np.array(incoming['residue_indices'])[np.where(outsiders)[0]]
			#---note that this is consonant with the close-water exclude step above (and also may be slow)
			exclude_outsider_res = [ii for ii,i in 
				enumerate(incoming['residue_indices']) if i in outsiders_res]
			insiders[exclude_outsider_res] = False
		surviving_indices = np.any((is_not_water,np.all((surviving_water,insiders),axis=0)),axis=0)
		lines = incoming['lines']
		lines = lines[:2]+list(np.array(incoming['lines'][2:-1])[surviving_indices])+lines[-1:]
		xyzs = list(points[surviving_indices])
		write_gro(lines=lines,xyzs=xyzs,output_file=state.here+'%s.gro'%gro)
	else: filecopy(wordspace['step']+'%s-dense.gro'%gro,wordspace['step']+'%s.gro'%gro)

###---SIMULATION POST-PROCESSING

def get_last_frame(gro='system-previous',dest=None,source=None,tpr=False):
	"""
	Prepare or locate a snapshot of the last state of the system.

	This function makes "chaining" possible by connecting one step to the next (along with a 
	portion of `init` which checks for previous states). It defaults to the current step, but you can 
	also set the source and destination. 
	The default output filename is "system-previous" because this is designed for chaining. 
	The default source is obtained by first checking for a previous state, in which case we get the 
	state from there. The primary alternate behavior is to get the last frame of the current directory, but
	this is typically suited to quick analysis, video-making, etc, in which case the user would have to 
	explicitly set the `source` keyword to `state.here`. If no previous state is available, we fall back to
	using `state.here`.
	"""

	#___! changed BASENAME TO GRO IN ARGUMENTS./ probably need to fix "out" below

	#---default source is state.here
	if not source: 
		#---DEFAULT behavior: if previous states are available we use them as the source
		if state.before: source = state.before[-1]['here']
		#---without previous states, we fall back to the current directory
		#---note: users must ask for the last frame in the current state
		else: source = state.here
	source = os.path.join(os.path.abspath(source),'')
	if not os.path.isdir(source): 
		raise Exception('requested last frame from %s but it does not exist'%source)
	#---default destination is state.here
	if dest: dest = os.path.join(os.path.abspath(dest),'')
	else: dest = state.here
	if not os.path.isdir(dest): raise Exception('cannot find folder %s'%dest)
	#---see if the source and destination are the same
	transmit = os.path.abspath(dest)!=os.path.abspath(source)
	#---current functionality requires that mdrun calls record the last supposed output
	#---check if the last frame was correctly written
	last_written_gro = source + get_last_gmx_call('mdrun')['flags']['-c']
	if os.path.isfile(last_written_gro):
		if transmit:
			#---if the source differs from the destination copy the file and save the path
			state.last_frame = os.path.join(dest,gro+'.gro')
			shutil.copyfile(last_written_gro,state.last_frame)
		#---if we are not copying the last frame, it is enough just to store its path
		else: state.last_frame = last_written_gro
	#---make the last frame from the cpt file
	else:
		#raise Exception('the following needs tested')
		cpt = source + get_last_gmx_call('mdrun')['flags']['-cpo']
		if not os.path.isfile(cpt): 
			msg = 'failed to find final gro *and* a cpt (%s).'%cpt
			msg += 'this might have occured if your simulation ran for less than 15 minutes'
			'and hence failed to write a cpt file for us to record the final frame'
			raise Exception(msg)
		#---use a custom command template here in case gmxcalls lacks it
		custom_gmxcall = commands_interpret('trjconv -f CPT -o OUT -s TPR')['trjconv']
		if dest:
			dest_dn = os.path.join(os.path.abspath(dest),'')
			if not os.path.isdir(dest_dn): raise Exception('cannot find folder %s'%dest)
			out = os.path.join(dest_dn,'trajectory_on_the_fly')
			log = os.path.join(os.path.abspath(dest),'log-trjconv-last-frame')
		else: 
			log = 'trjconv-last-frame'
		gmx('trjconv',cpt=get_last_gmx_call('mdrun')['flags']['-cpo'],
			tpr=get_last_gmx_call('mdrun')['flags']['-s'],
			out=out,custom=custom_gmxcall,log=log,inpipe='0\n')
		state.last_frame = state.here+out
	#---get tpr, top, etc, if requested
	#---! point to other functions
	return state.last_frame

def get_trajectory(dest=None):
	"""
	Convert the trajectory to reassemble broken molecules.
	Requires items from the history_gmx.
	Note that this is customized for vmdmake but it could be generalized and added to automacs.py.
	"""
	last_call = get_last_gmx_call('mdrun')
	last_tpr = last_call['flags']['-s']
	last_xtc = last_call['flags']['-x']
	last_cpt = last_call['flags']['-cpo']
	last_partno = int(re.match('^md\.part([0-9]{4})',os.path.basename(last_xtc)).group(1))
	if dest:
		dest_dn = os.path.join(os.path.abspath(dest),'')
		if not os.path.isdir(dest_dn): raise Exception('cannot find folder %s'%dest)
		log = os.path.join(os.path.abspath(dest),'log-trjconv-last-frame')
	else: log = 'trjconv-last-frame'
	out = 'md.part%04d.pbcmol'%last_partno
	if dest: out = os.path.join(dest_dn,out)
	custom_gmxcall = commands_interpret('trjconv -f XTC -o OUT.xtc -s TPR -pbc mol')['trjconv']
	gmx('trjconv',tpr=last_tpr,out=out,custom=custom_gmxcall,xtc=last_xtc,log=log,inpipe='0\n')
	custom_gmxcall = commands_interpret('trjconv -f CPT -o OUT.gro -s TPR -pbc mol')['trjconv']
	gmx('trjconv',cpt=last_cpt,tpr=last_tpr,out=out,
		custom=custom_gmxcall,log=log+'-gro',inpipe='0\n')
	#---if the destination is remote we attach the full path to the tpr, which can remain in place
	if dest: last_tpr = os.path.join(os.getcwd(),state.here,last_tpr)
	return {'xtc':out+'.xtc','gro':out+'.gro','tpr':last_tpr}
