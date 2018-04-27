#!/usr/bin/env python

import re
#from command_templates import gmx_call_templates

def gmx_commands_interpret(templates):
	"""
	Interpret a block of command templates for GROMACS.
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

def gmx_convert_template_to_call(spec,kwargs,strict=False):
	"""
	Use GROMACS call instructions along with kwargs to make a new command.
	"""
	kwargs_copy = dict(kwargs)
	#---check that we have the right incoming arguments
	missing_kwargs = [key for key in spec['required'] if key not in kwargs]
	#---remove required kwargs from the kwargs list
	subs_required = {}
	for key in spec['required']: 
		if key in kwargs: subs_required[key] = kwargs.pop(key)
	#---flags comes in as a list of tuples, but we require a dictionary
	flags = dict(spec['flags'])
	#---remaining kwargs are overrides
	if kwargs and not strict: 
		#---loop over overrides and apply them
		for key,val in kwargs.items(): 
			flags[key if key in flags else '-'+key] = val
	elif kwargs and strict: raise Exception('unprocessed kwargs with strictly no overrides: %s'%str(kwargs))
	#---replace booleans with gromacs -flag vs -noflag syntax
	#---! note that sending e.g. noflag=True is not allowed!
	for key in list(flags.keys()):
		if type(flags[key])==bool: 
			if re.match('^no',key): 
				raise Exception('refusing to accept a kwarg to a gmx flag that starts with "no": '%key)
			if flags[key]: flags[key] = ''
			else: 
				flags[re.sub('^-(.+)$',r'-no\1',key)] = '' 
				del flags[key]
	#---use the flags to construct the call
	call = state.gmxpaths[spec['command']]+' '
	try: call += (' '.join(['%s %s'%(key,val) for key,val in flags.items()]))%subs_required
	except: raise Exception('[ERROR] failed to construct the gromacs call. '+
		'NOTE missing keywords: %s'%missing_kwargs+' NOTE spec: %s'%spec+' NOTE incoming kwargs: %s'%kwargs_copy)
	#---use the explicit specs to make a record of this call
	recorded = {'call':spec['command'],'flags':dict([(flag,
		value%subs_required if type(value)==str else value) for flag,value in flags.items()])}
	return {'call':call,'recorded':recorded}

def gmx_get_last_call(name,this_state=None):
	"""
	The gmx call history is loaded by convert_gmx_template_to_call. We can retrieve the last call to a 
	particular gromacs utility using this function.
	"""
	# sometimes we run this after "import amx" so the state is found there
	if not this_state: this_state = state
	if 'history_gmx' not in this_state: raise Exception('no gromacs history to get last call')
	recents = [ii for ii,i in enumerate(this_state.history_gmx) if i['call']==name]
	if not recents: raise Exception('no record of a gmx call to %s recently'%name)
	return this_state.history_gmx[recents[-1]]

def gmx_register_call(command,flag,value):
	"""
	Register an automatic rule for adding flags to gromacs calls.
	"""
	if 'gmx_call_rules' not in state: state.gmx_call_rules = []
	conflicting_rules = [ii for ii,i in enumerate(state.gmx_call_rules) 
		if i['command']==command and i['flag']==flag]
	if any(conflicting_rules):
		print('[NOTE] the rules list is: %s'%conflicting_rules)
		raise Exception('incoming item in gmx_call_rules conflicts with the list (see rules list above): '+
			'command="%s",flag="%s",value="%s"'%(command,flag,value))
	state.gmx_call_rules.append(dict(command=command,flag=flag,value=value))
	#---! somehow this gets propagated to the next step, which is pretty cool. explain how this happens
