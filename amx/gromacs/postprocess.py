#!/usr/bin/env python

def gmx_get_last_frame(gro='system-previous',dest=None,source=None,tpr=False):
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
	last_written_gro = source + gmx_get_last_call('mdrun')['flags']['-c']
	if os.path.isfile(last_written_gro):
		if transmit:
			#---if the source differs from the destination copy the file and save the path
			state.last_frame = os.path.join(dest,gro+'.gro')
			shutil.copyfile(last_written_gro,state.last_frame)
		#---if we are not copying the last frame, it is enough just to store its path
		else: state.last_frame = last_written_gro
	#---make the last frame from the cpt file
	else:
		cpt = source + gmx_get_last_call('mdrun')['flags']['-cpo']
		if not os.path.isfile(cpt):
			msg = 'failed to find final gro *and* a cpt (%s).'%cpt
			msg += 'this might have occured if your simulation ran for less than 15 minutes'
			'and hence failed to write a cpt file for us to record the final frame'
			raise Exception(msg)
		#---use a custom command template here in case gmxcalls lacks it
		custom_gmxcall = gmx_commands_interpret('trjconv -f CPT -o OUT -s TPR')['trjconv']
		if dest:
			dest_dn = os.path.join(os.path.abspath(dest),'')
			if not os.path.isdir(dest_dn): raise Exception('cannot find folder %s'%dest)
			out = os.path.join(dest_dn,'trajectory_on_the_fly')
			log = os.path.join(os.path.abspath(dest),'log-trjconv-last-frame')
		else: 
			log = 'trjconv-last-frame'
		gmx('trjconv',cpt=gmx_get_last_call('mdrun')['flags']['-cpo'],
			tpr=gmx_get_last_call('mdrun')['flags']['-s'],
			out=out,custom=custom_gmxcall,log=log,inpipe='0\n')
		state.last_frame = state.here+out
	#---get tpr, top, etc, if requested
	#---! point to other functions
	return state.last_frame

def gmx_get_trajectory(dest=None):
	"""
	Convert the trajectory to reassemble broken molecules.
	Requires items from the history_gmx.
	Note that this is customized for vmdmake but it could be generalized and added to automacs.py.
	"""
	last_call = gmx_get_last_call('mdrun')
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
	custom_gmxcall = gmx_commands_interpret('trjconv -f XTC -o OUT.xtc -s TPR -pbc mol')['trjconv']
	gmx('trjconv',tpr=last_tpr,out=out,custom=custom_gmxcall,xtc=last_xtc,log=log,inpipe='0\n')
	custom_gmxcall = gmx_commands_interpret('trjconv -f CPT -o OUT.gro -s TPR -pbc mol')['trjconv']
	gmx('trjconv',cpt=last_cpt,tpr=last_tpr,out=out,
		custom=custom_gmxcall,log=log+'-gro',inpipe='0\n')
	#---if the destination is remote we attach the full path to the tpr, which can remain in place
	if dest: last_tpr = os.path.join(os.getcwd(),state.here,last_tpr)
	return {'xtc':out+'.xtc','gro':out+'.gro','tpr':last_tpr}
