#!/usr/bin/env python

from __future__ import print_function
from ortho import str_types
import os,shutil,re
from amx.utils import status
from .gmx_tools import component,include

def minimize(name,structure=None,method='steep',top=None,restraints=False):
	"""
	Standard minimization procedure.
	"""
	log_base = 'grompp-%s-%s'%(name,method)
	grompp_kwargs = {}
	if restraints==True: grompp_kwargs['r'] = '%s.gro'%name
	elif restraints: grompp_kwargs['r'] = restraints
	base = 'em-%s-%s'%(name,method)
	gmx('grompp',
		out=base+'.tpr',
		topology=name+'.top' if not top else top,
		structure=name+'.gro' if not structure else structure,
		log=log_base,
		parameters='input-em-%s-in'%method,
		parameters_out=base+'.mdp',
		**grompp_kwargs)
	tpr = state.here+'em-%s-%s.tpr'%(name,method)
	if not os.path.isfile(tpr): 
		try:
			#! note that this error reporting resembles that in gmx_run
			#! needs systematic error checker
			from calls import gmx_error_strings
			log_fn = state.here+'log-%s'%log_base
			with open(log_fn) as fp: log_text = fp.read()
			errors = re.findall('\n-{2,}(.*?(?:%s).*?)-{2,}'%(
				'|'.join(gmx_error_strings)),log_text,re.M+re.DOTALL)
			for error in errors:
				#! error reporting may be duplicated in gmx_run and worth consolidating
				status('caught error in %s:\n[ERROR] | '%log_fn,tag='error')
				print('\n[ERROR] | '.join(error.split('\n')))
				print('note',
					'the extracted output above may not capture the full error, so check the file')
			raise Exception('cannot find %s. see errors above and check the grompp step.'%tpr)
		except: raise Exception('cannot find %s. check the grompp step.'%tpr)
	base = 'em-'+'%s-%s'%(name,method)
	structure = base+'.gro'
	gmx('mdrun',
		energy=base+'.edr',
		logfile=base+'.log',
		compressed=base+'.xtc',
		trajectory=base+'.trr',
		checkpoint=base+'.cpt',
		structure=structure,
		input=base+'.tpr',
		log='mdrun-%s-%s'%(name,method))
	shutil.copyfile(state.here+structure,state.here+'%s-minimized.gro'%name)

def solvate_protein(structure,top):
	"""
	Standard solvate procedure for atomistic protein in water.
	! STILL USING THIS BECAUSE NO scipy and because we cannot find spc216 in the other one
	"""
	# purge the wordspace of solvent and anions in case we are resuming
	for key in [state.q('anion'),state.q('cation'),'SOL']:
		if key in list(zip(*state.composition))[0]:
			del state.composition[list(zip(*state.composition))[0].index(key)]
	gmx('editconf',
		structure=structure,
		out='solvate-box-alone.gro',
		log='editconf-checksize',d=0)
	with open(state.here+'log-editconf-checksize','r') as fp: lines = fp.readlines()
	boxdims = map(lambda y:float(y),re.findall(r'\s*box vectors \:\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)',
		list(filter(lambda x:re.match(r'\s*box vectors',x),lines)).pop()).pop())
	boxvecs = tuple([i+2*state.q('water_buffer') for i in boxdims])
	center = tuple([i/2. for i in boxvecs])
	# cube is not implemented yet
	gmx('editconf',structure=structure,out='solvate-protein.gro',
		#flags='-center %f %f %f'%center+' '+'-box %f %f %f'%boxvecs,
		log='editconf-center-protein')
	gmx('solvate',
		structure='solvate-protein.gro',
		solvent=state.q('solvent'),
		out='solvate-dense.gro',
		log='genbox-solvate')
	# trim waters if the protein_water_gap setting is not False
	water_gap = state.q('protein_water_gap')
	if water_gap: 
		try:
			import scipy
			trim_waters(structure='solvate-dense.gro',out='solvate.gro',
				gap=water_gap,boxvecs=boxvecs)
		except:
			print('warning','failed to load scipy so continuing without a water_gap')
			copy_file('solvate-dense.gro','solvate.gro')
	else: copy_file('solvate-dense.gro','solvate.gro')
	gmx('make_ndx',inpipe='q\n',
		structure='solvate.gro',
		out='solvate-water-check.ndx',
		log='make-ndx-solvate-check')
	with open(state.here+'log-make-ndx-solvate-check','r') as fp: lines = fp.readlines()
	nwaters = int(re.findall(r'\s*[0-9]+\s+Water\s+:\s+([0-9]+)\s+atoms',
		list(filter(lambda x:re.match(r'\s*[0-9]+\s+Water',x),lines)).pop()).pop())/3
	state.water_without_ions = nwaters
	component('SOL',count=nwaters)
	# add the suffix so that water is referred to by its name in the settings
	include(state.q('water'),ff=True)
	write_top('solvate.top')

def counterions(structure=None,top=None,includes=None,ff_includes=None,gro='counterions.gro',
	restraints=False,counts=None):
	"""
	Standard procedure for adding counterions.
	The resname must be understandable by "r RESNAME" in make_ndx and writes to the top file.
	Note that the ``top`` argument is not used and should be removed after checking downstream.
	"""
	# we store the water resname in the wordspace as "sol"
	resname =  state.q('sol','SOL')
	#! the following section fails on the helix-0 test set which tracks water accurately
	if state.get('counterions_header',True):
		# clean up the composition in case this is a restart
		for key in ['cation','anion',resname]:
			try: state.composition.pop(list(zip(*state.composition))[0].index(state.q(key)))
			except: pass
		component(resname,count=state.water_without_ions)
	# write the topology file as of the solvate step instead of copying them (genion overwrites top)
	write_top('counterions.top')
	# bilayers have restraints during genion step so we pass that along here
	grompp_kwargs = {}
	if restraints==True: grompp_kwargs['r'] = '%s.gro'%structure
	elif restraints: grompp_kwargs['r'] = restraints
	gmx('grompp',
		out='genion.tpr',
		topology='counterions.top',
		structure=structure,
		log='grompp-genion',
		parameters='input-em-%s-in'%'steep',
		parameters_out='genion.mdp',
		**grompp_kwargs)
	gmx('make_ndx',
		structure=structure,
		out='solvate-waters.ndx',
		inpipe='keep 0\nr %s\nkeep 1\nq\n'%resname,
		log='make-ndx-counterions-check')
	if not state.ionic_strength: raise Exception('specify ionic strength in the settings (in mol/L)')
	for key in ['cation','anion']:
		if not state.q(key,None): raise Exception('you must specify %s in settings'%key)
	counts = dict(conc='%f'%state.q('ionic_strength'),neutral=True) if not counts else counts
	gmx('genion',
		input='genion.tpr',
		out=gro,
		index='solvate-waters.ndx',
		cation=state.cation,
		anion=state.anion,
		log='genion',**counts)
	with open(state.here+'log-genion','r') as fp: lines = fp.readlines()
	declare_ions = list(filter(lambda x:re.search('Will try',x)!=None,lines)).pop()
	ion_counts = re.findall(
		r'^Will try to add ([0-9]+)\+?\-? ([\w\+\-]+) ions and ([0-9]+) ([\w\+\-]+) ions',
		declare_ions).pop()
	for ii in range(2): component(ion_counts[2*ii+1],count=ion_counts[2*ii])
	component(resname,count=component(resname)-component(ion_counts[1])-component(ion_counts[3]))
	if includes:
		if type(includes)==str: includes = [includes]
		for i in includes: include(i)
	if ff_includes:
		if type(ff_includes)==str: ff_includes = [ff_includes]
		for i in ff_includes: include(i,ff=True)
	write_top('counterions.top')

def equilibrate_check(name):
	"""
	Check if the gro file for this step has been written.
	"""
	found = False
	fn = state.here+'md-%s.gro'%name
	if os.path.isfile(fn): 
		print('note','found %s'%fn)
		found = True
	return found

def equilibrate(groups=None,structure='system',top='system.top',
	stages_only=False,seq=None,restraints=False):
	"""
	Standard equilibration procedure.
	"""
	# custom settings via kwarg otherwise we call out to the state
	if not seq:
		# settings can be a python list or a comma-separated string
		eq_setting = state.get('equilibration')
		if eq_setting:
			if isinstance(eq_setting,str_types):
				try: seq = eq_setting.split(',')
				except: 
					raise Exception(
						'failed to parse equilibration setting: "%s"'%
						str(eq_setting))
			else: seq = eq_setting
		else: seq = []
	# sequential equilibration stages
	for eqnum,name in enumerate(seq):
		if not equilibrate_check(name):
			structure_this = structure if eqnum == 0 else 'md-%s'%seq[eqnum-1]
			grompp_kwargs = {}
			if restraints==True: grompp_kwargs['r'] = '%s.gro'%structure_this
			elif restraints: grompp_kwargs['r'] = restraints
			if groups: grompp_kwargs['n'] = groups
			base='md-%s'%name
			gmx('grompp',
				out=base+'.tpr',
				topology=top,
				structure=structure_this,
				log='grompp-%s'%name,
				parameters='input-md-%s-eq-in'%name,
				parameters_out=base+'.mdp',
				maxwarn=state.get('maxwarn',0),
				**grompp_kwargs)
			gmx('mdrun',
				base='md-%s'%name,
				log='mdrun-%s'%name)
			if not os.path.isfile(state.here+'md-%s.gro'%name): 
				raise Exception('mdrun failure at %s'%name)
	# stages only protects you from beginning with part numbers
	if not stages_only:
		# first part of the equilibration/production run
		name = 'md.part0001'
		if not equilibrate_check(name) or seq == []:
			structure_this = 'md-%s'%seq[-1] if seq else structure
			grompp_kwargs = {}
			if restraints==True: grompp_kwargs['r'] = '%s.gro'%structure_this
			elif restraints: grompp_kwargs['r'] = restraints
			if groups: grompp_kwargs['n'] = groups
			gmx('grompp',
				base=name,
				topology=top,
				structure=structure_this,
				parameters='input-md-in',
				maxwarn=state.get('maxwarn',0),
				log='grompp-0001',
				**grompp_kwargs)
			gmx('mdrun',
				base=name,
				log='mdrun-0001')
