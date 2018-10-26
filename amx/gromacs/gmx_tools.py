#!/usr/bin/env python

import os,re

def extract_itp(topfile,cwd=None,itp='protein.itp'):
	"""
	Extract a ``protein.itp`` file from a `top` file which is automatically generated by `pdb2gmx`.
	Note that parts of this function was poached to read_top in common.
	This always generates a single ITP file.
	"""
	topfile_fn = state.here+topfile
	if os.path.isfile(topfile_fn): pass
	elif not os.path.isfile(topfile_fn) and os.path.isfile(topfile): topfile_fn = topfile
	else: raise Exception('cannot find %s or %s'%(topfile_fn,topfile))
	with open(topfile_fn,'r') as f: topfile = f.read()
	chains = {}
	startline = [ii for ii,i in enumerate(topfile.split('\n')) 
		if re.match(r'^(\s+)?\[(\s+)?molecules(\s+)?\]',i)][0]
	count_regex = r'^(\w+)\s+([0-9]+)'
	components = [re.findall(count_regex,line).pop()
		for line in topfile.split('\n')[startline:] if re.match(count_regex,line)]		
	for name,count in components: component(name,count=int(count))
	with open(state.here+itp,'w') as fp: 
		for line in topfile.split('\n'):
			# skip any part of the top that follows the water topology and/or system composition
			if re.match('; Include water topology',line): break
			if re.match('; Include topology for ions',line): break
			if re.match(r'\[ system \]',line): break
			# you must extract forcefield.itp from the file to prevent redundant includes
			if not re.match(r".+forcefield\.itp",line) and not \
				re.match("; Include forcefield parameters",line): 
				fp.write(line+'\n')
	if 'itp' not in state: state.itp = [itp]
	else: state.itp.append(itp)
	# always report the itp file
	return itp

def component(name,count=None,top=False):
	"""
	Add or modify the composition of the system and return the count if none is provided.
	"""
	# start a composition list if absent
	if 'composition' not in state: 
		state.composition = []
		try: state.composition.append([name,int(count)])
		except: raise Exception('the first time you add a component you must supply a count')
	# if count is supplied then we change the composition
	names = list(zip(*state.composition))[0]
	if count != None:
		if name in names: state.composition[names.index(name)][1] = int(count)
		else: 
			if top: state.composition.insert(0,[name,int(count)])
			else: state.composition.append([name,int(count)])
	# return the requested composition
	names = list(zip(*state.composition))[0]
	return state.composition[names.index(name)][1]

def include(name,ff=False):
	"""
	Add an ITP file to the itp (non-ff includes) list but avoid redundancies 
	which cause errors in GROMACS.
	"""
	#! standardize this interface
	which = 'ff_includes' if ff else 'itp'
	if which not in state: state[which] = []
	if name not in state[which]: state[which].append(name)

def write_top_original(topfile):
	"""
	Write the topology file.
	"""
	#! retire this
	# forcefield.itp is a default
	state.ff_includes = state.get('ff_includes',['forcefield'])
	with open(state.here+topfile,'w') as fp:
		# write include files for the force field
		for incl in state.ff_includes:
			if not state.force_field: 
				raise Exception('state.force_field is undefined. refusing to write a topology.')
			fp.write('#include "%s.ff/%s.itp"\n'%(state['force_field'],incl))
		# write include files
		if 'itp' not in state: state.itp = []
		for itp in state.itp: fp.write('#include "'+itp+'"\n')
		# write system name
		fp.write('[ system ]\n%s\n\n[ molecules ]\n'%state.get('system_name'))
		for key,val in state.composition: 
			if val>0: fp.write('%s %d\n'%(key,val))

def write_top(topfile):
	"""
	Write a topology.
	"""
	# remove redundancies 
	if 'itp' in state: state.itp = list(set(state.itp))
	# if the force field is local we automatically detect its files and add itps to it
	if state.force_field and os.path.isdir(state.here+state.force_field+'.ff'):
		meta_fn = os.path.join(state.here+state.force_field+'.ff','meta.json')
		# we require a meta.json file to specify the definitions
		if not os.path.isfile(meta_fn): raise Exception('need meta.json in %s'%(state.force_field+'.ff'))
		with open(meta_fn) as fp: meta = json.loads(fp.read())
		# includes is typically only the itp files in the top level unless the meta file is explicit
		includes = glob.glob(os.path.join(state.here+state.force_field+'.ff','*.itp'))
		# an explicit include_itps list is added after the defs and overrides the itps in the top level of 
		#   the e.g. charmm.ff folder
		#! note that this is clumsy. the include_itps is necessary to have itp files in a subfolder
		#!   but we also need to have everything in the meta['definitions'] for the new-style charmm
		#!   way of handling the itps triggered by "if 'definitions'" below
		if meta.get('include_itps',False):
			includes = [os.path.join(state.step,state.force_field+'.ff',i) for i in meta['include_itps']]
			missing_itps = [i for i in includes if not os.path.isfile(i)]
			if any(missing_itps):
				raise Exception('some files specified by include_itps in meta are missing: %s'%missing_itps)
		# use new style definitions for an explicit ordering of the top list of includes
		#   which is suitable for charmm and other standard force fields 
		#   (martini is the else, needs replaced)
		if 'definitions' in meta:
			# get the paths
			itp_namer = dict([(os.path.basename(j),j) for j in includes])
			includes_reorder = [itp_namer[os.path.basename(j)] for j in meta['definitions']]
		# other force fields might have molecules spread across multiple ITPs with one that has the defs
		else: 
			ff_defs = unique([i for i in meta if meta[i] if 'defs' in meta[i]])
			# reorder with the definitions first
			includes_reorder = [i for i in includes if os.path.basename(i)==ff_defs]
			includes_reorder += [i for i in includes if i not in includes_reorder]
		with open(state.here+topfile,'w') as fp:
			for fn in [os.path.relpath(i,state.here) for i in includes_reorder]:
				fp.write('#include "%s"\n'%fn)
			# additional itp files
			for itp in list(set(state.q('itp',[]))): fp.write('#include "'+itp+'"\n')
			# write system name
			fp.write('[ system ]\n%s\n\n[ molecules ]\n'%state.q('system_name'))
			for key,val in state.composition: fp.write('%s %d\n'%(key,val))
	# revert to the old-school method if we are not using local force fields in e.g. protein atomistic
	else: write_top_original(topfile)

def write_structure_pdb(structure,pdb):
	"""
	Infer the starting residue from the original PDB and write structure.pdb with the correct indices
	according to the latest GRO structure (typically counterions.gro).
	"""
	# automatically center the protein in the box here and write the final structure
	gmx('make_ndx',inpipe='q\n',
		structure=structure,
		out='counterions-groups.ndx',
		log='make-ndx-counterions',)
	with open(state.here+'log-make-ndx-counterions','r') as fp: lines = fp.readlines()
	relevant = [list(filter(lambda x:re.match(r'\s*[0-9]+\s+%s'%name,x),lines))
		for name in ['System','Protein']]
	groupdict = dict([(j[1],int(j[0])) for j in 
		[re.findall(r'^\s*([0-9]+)\s(\w+)',x[0])[0] for x in relevant]])
	import ipdb;ipdb.set_trace()
	gmx('trjconv',
		inpipe='%d\n%d\n'%(groupdict['Protein'],groupdict['System']),
		center=True,
		index='counterions-groups.ndx',
		structure='counterions-minimized.gro',
		log='trjconv-counterions-center',
		input='em-counterions-steep.tpr',
		out='system.gro')
	with open(state.here+pdb,'r') as fp: lines = fp.readlines()
	startres = int([line for line in lines if re.match('^ATOM',line)][0][23:26+1])
	gmx('editconf',
		structure=structure,
		out='structure.pdb',
		resnr=startres,
		log='editconf-structure-pdb')
