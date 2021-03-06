#!/usr/bin/env python

"""
COMMON
------

Extra functions common to many simulations.
Generic extensions used by: proteins, bilayers
"""

import os,sys,re,glob,shutil,subprocess,json
import numpy as np

from calls import gmx,gmx_get_share
from generic import component,include
from force_field_tools import Landscape
from utils import str_types
from gromacs_commands import gmx_get_last_call

#---hide some functions from logging because they are verbose
_not_reported = ['write_gro','dotplace','unique']
#---extensions shared throughout the codes
_shared_extensions = ['dotplace','unique']

#---write a float in a format favorable to GRO to ensure the dot is always in the right place
dotplace = lambda n: re.compile(r'(\d)0+$').sub(r'\1',"%8.3f"%float(n)).ljust(8)

def unique(items):
	"""
	Enforce uniqueness on a list.
	!! used only once in this file otherwise np.unique (try: find . -name "*.py" | xargs grep "[^\.]unique(")
	!! hence this is soon to move to the trash bin
	"""
	try: (element,) = items
	except ValueError: 
		raise Exception('expecting only one item in this list: %s'%str(items))
	return element

def contiguous_encode(items):
	"""
	Handy method for encoding tuples into single objects in numpy for uniqueness checking.
	Note that this may eventually be superceded by an axis keyword in the numpy unique.
	!! currently only used in amx/structure_tools. soon to move there
	"""
	return np.ascontiguousarray(items).view(np.dtype((np.void,items.dtype.itemsize*items.shape[1])))

###---PDB-SPECIFIC FUNCTIONS

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

def get_pdb(code,path=None):
	"""
	Download a PDB from the database or copy from file.
	"""
	#---! previous version of this function checked some path for an already-downloaded copy
	#---! ...this might be worth adding back in. it also extracted the sequence 
	if sys.version_info<(3,0): from urllib2 import urlopen
	else: from urllib.request import urlopen
	response = urlopen('http://www.rcsb.org/pdb/files/'+code+'.pdb')
	pdbfile = response.read()
	if path==None: dest = state.here+'start-structure.pdb'
	else: 
		if os.path.isdir(path): dest = os.path.join(path,code+'.pdb')
		else: dest = path
	with open(dest,'w') as fp: fp.write(pdbfile.decode())
	#---! we should log that the PDB was successfully got

def get_last(name,cwd=None):
	"""
	Get the last of a particular file by extension.
	"""
	if not re.match('^[a-z]+$',name): 
		raise Exception('extension %s can only have lowercase letters'%name)
	if not cwd: cwd = state.here
	fns = glob.glob(os.path.join(cwd,'*.tpr'))
	fns_recent = sorted(fns,key=lambda x:os.path.getmtime(x))
	if len(fns_recent)==0: raise Exception('could not find a %s file in %s'%(name,cwd))
	#---by convention we strip extensions because everything runs through gmxcalls
	fn = os.path.basename(fns_recent[-1])
	return os.path.splitext(fn)[0]

def get_last_file(name,cwd=None):
	"""
	Get the last of a particular file by extension.
	"""
	if not state.before: raise Exception('cannot find a previous step in state.before')
	target = os.path.join(state.before[-1]['here'],name)
	if not os.path.isfile(target): raise Exception('cannot find %s'%target)
	shutil.copy(fn,state.here)

def get_last_mdps():
	"""
	Get all of the mdp files from a previous step.
	"""
	if not state.before: raise Exception('cannot find a previous step in state.before')
	prev_here = state.before[-1]['here']
	for fn in glob.glob(os.path.join(prev_here,'input-*.mdp')): shutil.copy(fn,state.here)

def get_last_sources():
	"""
	Get the sources retrieved from the previous step (this gets the originals).
	"""
	if not state.before: raise Exception('cannot find a previous step in state.before')
	sources = state.before[-1]['settings']['sources']
	for dn in sources:
		if not os.path.isdir(dn): raise Exception('source %s is not a directory'%dn)
		shutil.copytree(dn,os.path.join(state.here,os.path.basename(dn)))

def remove_hetero_atoms(structure,out):
	"""
	Remove heteroatoms from a PDB.
	"""
	if not os.path.isfile(state.here+structure): 
		raise Exception('cannot find input %s'%(state.here+structure))
	with open(state.here+structure) as fp: original = fp.read()
	if os.path.isfile(state.here+out): raise Exception('refusing to overwrite %s'%(state.here+out))
	with open(state.here+out,'w') as fp: 
		fp.write('\n'.join(i for i in original.splitlines() if re.match('^ATOM',i)))

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
		if re.match('^(\s+)?\[(\s+)?molecules(\s+)?\]',i)][0]
	count_regex = '^(\w+)\s+([0-9]+)'
	components = [re.findall(count_regex,line).pop()
		for line in topfile.split('\n')[startline:] if re.match(count_regex,line)]		
	for name,count in components: component(name,count=int(count))
	with open(state.here+itp,'w') as fp: 
		for line in topfile.split('\n'):
			#---skip any part of the top that follows the water topology and/or system composition
			if re.match('; Include water topology',line): break
			if re.match('; Include topology for ions',line): break
			if re.match('\[ system \]',line): break
			#---you must extract forcefield.itp from the file to prevent redundant includes
			if not re.match(".+forcefield\.itp",line) and not \
				re.match("; Include forcefield parameters",line): 
				fp.write(line+'\n')
	if 'itp' not in state: state.itp = [itp]
	else: state.itp.append(itp)
	#---always report the itp file
	return itp

def write_top_original(topfile):
	"""
	Write the topology file.
	"""
	#---forcefield.itp is a default
	state.ff_includes = state.q('ff_includes',['forcefield'])
	with open(state.here+topfile,'w') as fp:
		#---write include files for the force field
		for incl in state.ff_includes:
			if not state.force_field: 
				raise Exception('state.force_field is undefined. refusing to write a topology.')
			fp.write('#include "%s.ff/%s.itp"\n'%(state.q('force_field'),incl))
		#---write include files
		if 'itp' not in state: state.itp = []
		for itp in state.itp: fp.write('#include "'+itp+'"\n')
		#---write system name
		fp.write('[ system ]\n%s\n\n[ molecules ]\n'%state.q('system_name'))
		for key,val in state.composition: 
			if val>0: fp.write('%s %d\n'%(key,val))

def write_top(topfile):
	"""
	Write a topology.
	"""
	#---remove redundancies 
	if 'itp' in state: state.itp = list(set(state.itp))
	#---if the force field is local we automatically detect its files and add itps to it
	if state.force_field and os.path.isdir(state.here+state.force_field+'.ff'):
		meta_fn = os.path.join(state.here+state.force_field+'.ff','meta.json')
		#---we require a meta.json file to specify the definitions
		if not os.path.isfile(meta_fn): raise Exception('need meta.json in %s'%(state.force_field+'.ff'))
		with open(meta_fn) as fp: meta = json.loads(fp.read())
		#---includes is typically only the itp files in the top level unless the meta file is explicit
		includes = glob.glob(os.path.join(state.here+state.force_field+'.ff','*.itp'))
		#---an explicit include_itps list is added after the defs and overrides the itps in the top level of 
		#---...the e.g. charmm.ff folder
		#---! note that this is clumsy. the include_itps is necessary to have itp files in a subfolder
		#---! ...but we also need to have everything in the meta['definitions'] for the new-style charmm
		#---! ...way of handling the itps triggered by "if 'definitions'" below
		if meta.get('include_itps',False):
			includes = [os.path.join(state.step,state.force_field+'.ff',i) for i in meta['include_itps']]
			missing_itps = [i for i in includes if not os.path.isfile(i)]
			if any(missing_itps):
				raise Exception('some files specified by include_itps in meta are missing: %s'%missing_itps)
		#---use new style definitions for an explicit ordering of the top list of includes
		#---...which is suitable for charmm and other standard force fields 
		#---...(martini is the else, needs replaced)
		if 'definitions' in meta:
			#---get the paths
			itp_namer = dict([(os.path.basename(j),j) for j in includes])
			includes_reorder = [itp_namer[os.path.basename(j)] for j in meta['definitions']]
		#---other force fields might have molecules spread across multiple ITPs with one that has the defs
		else: 
			ff_defs = unique([i for i in meta if meta[i] if 'defs' in meta[i]])
			#---reorder with the definitions first
			includes_reorder = [i for i in includes if os.path.basename(i)==ff_defs]
			includes_reorder += [i for i in includes if i not in includes_reorder]
		with open(state.here+topfile,'w') as fp:
			for fn in [os.path.relpath(i,state.here) for i in includes_reorder]:
				fp.write('#include "%s"\n'%fn)
			#---additional itp files
			for itp in list(set(state.q('itp',[]))): fp.write('#include "'+itp+'"\n')
			#---write system name
			fp.write('[ system ]\n%s\n\n[ molecules ]\n'%state.q('system_name'))
			for key,val in state.composition: fp.write('%s %d\n'%(key,val))
	#---revert to the old-school method if we are not using local force fields in e.g. protein atomistic
	else: write_top_original(topfile)

#---aliases for common/intuitive names
write_topology = write_top

def read_molecule(gro):
	"""
	Read a molecule in GRO form and return its XYZ coordinates and atomnames.
	!REPLACE WITH common.read_gro
	"""
	with open(wordspace['lipid_structures']+'/'+gro+'.gro','r') as fp: rawgro = fp.readlines()
	pts = np.array([[float(j) for j in i.strip('\n')[20:].split()] for i in rawgro[2:-1]])
	pts -= mean(pts,axis=0)
	atomnames = np.array([i.strip('\n')[10:15].strip(' ') for i in rawgro[2:-1]])
	return pts,atomnames

def read_gro(gro,**kwargs):
	"""
	Read a GRO file and return its XYZ coordinates and atomnames. 
	!Note that this is highly redundant with a cgmd_bilayer.read_molecule so you might replace that one.
	!RE-ADD NUMPY AND CENTER FOR reionize/cgmd_bilayer
	!Note that we drop velocities which should be read separately or with a flag.
	"""
	cwd = kwargs.get('cwd',state.here)
	center = kwargs.get('center',False)
	with open(os.path.join(cwd,gro),'r') as fp: lines = fp.readlines()
	if center:
		import numpy as np
		pts = np.array([[float(j) for j in i.strip('\n')[20:].split()] for i in lines[2:-1]])
		pts -= np.mean(pts,axis=0)
		atom_names = np.array([i.strip('\n')[10:15].strip(' ') for i in lines[2:-1]])
	else:
		try: pts = [[float(j) for j in i.strip('\n')[20:].split()] for i in lines[2:-1]]
		#---backup regex in case values run together
		except: 
			runon_regex = \
				'^\s*([-]?[0-9]+\.?[0-9]{0,3})\s*([-]?[0-9]+\.?[0-9]{0,3})\s*([-]?[0-9]+\.?[0-9]{0,3})'
			pts = [[float(j) for j in re.findall(runon_regex,i[20:])[0]] for i in lines[2:-1]]
		atom_names = [i.strip('\n')[10:15].strip(' ') for i in lines[2:-1]]
	residue_names = [i[5:10].strip() for i in lines[2:-1]]
	residue_indices = [int(i[0:5].strip()) for i in lines[2:-1]]
	pts_out = [i[:3] for i in pts]
	if center:
		atom_names = np.array(atom_names)
		residue_names = np.array(residue_names)
		residue_indices = np.array(residue_indices)
		pts_out = np.array(pts_out)
	outgoing = {'points':pts_out,'atom_names':atom_names,'lines':lines,
		'residue_names':residue_names,'residue_indices':residue_indices}
	return outgoing

def write_gro(**kwargs):
	"""
	Write a GRO file with new coordinates.
	"""
	input_file = kwargs.get('input_file',None)
	output_file = kwargs.get('output_file',None)
	if input_file:
		with open(incoming,'r') as fp: lines = fp.readlines()
	else: lines = kwargs.get('lines')
	xyzs = kwargs.get('xyzs')
	lines[1] = re.sub('^\s*([0-9]+)','%d'%(len(lines)-3),lines[1])
	for lnum,line in enumerate(lines[2:-1]):
		lines[2+lnum] = line[:20] + ''.join([dotplace(x) for x in xyzs[lnum]])+'\n'
	with open(output_file,'w') as fp: 
		for line in lines: fp.write(line)

def gro_combinator(*args,**kwargs):
	"""
	Concatenate an arbitrary number of GRO files.
	"""
	cwd = kwargs.pop('cwd','./')
	out = kwargs.pop('gro','combined')
	box = kwargs.pop('box',False)
	name = kwargs.pop('name','SYSTEM')
	collection = []
	for arg in args: 
		with open(cwd+arg+'.gro' if not re.match('^.+\.gro',arg) else cwd+arg) as fp: 
			collection.append(fp.readlines())
	with open(cwd+out+'.gro','w') as fp:
		fp.write('%s\n%d\n'%(name,sum(len(i) for i in collection)-len(collection)*3))
		for c in collection: 
			for line in c[2:-1]: fp.write(line)
		#---use the box vectors from the first structure
		if not box: fp.write(collection[0][-1])		
		else: fp.write(' %.3f %.3f %.3f\n'%tuple(box))
	#---! added this because resnrs were scrambled
	gmx('editconf',structure=out,gro=out+'-renumber',log='editconf-combo-%s'%out,resnr=1)
	move_file(out+'-renumber.gro',out+'.gro')
	os.remove(state.here+'log-editconf-combo-%s'%out)

def get_box_vectors(structure,gro=None,d=0,log='checksize'):
	"""
	Return the box vectors.
	"""
	if not gro: gro = structure+'-check-box'
	#---note that we consult the command_library here
	gmx('editconf',structure=structure,gro=gro,
		log='editconf-%s'%log,d=d)
	with open(state.here+'log-editconf-%s'%log,'r') as fp: lines = fp.readlines()
	box_vector_regex = '\s*box vectors\s*\:\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)'
	box_vector_new_regex = '\s*new box vectors\s*\:\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)'
	runon_regex = '^\s*([-]?[0-9]+\.?[0-9]{0,3})\s*([-]?[0-9]+\.?[0-9]{0,3})\s*([-]?[0-9]+\.?[0-9]{0,3})'
	old_line = [l for l in lines if re.match(box_vector_regex,l)][0]
	vecs_old = re.findall('\s*box vectors\s*:([^\(]+)',old_line)[0]
	try:
		#---sometimes the numbers run together
		try: vecs_old = [float(i) for i in vecs_old.strip(' ').split()]
		except: vecs_old = [float(i) for i in re.findall(runon_regex,vecs_old)[0]]
		#---repeat for new box vectors
		new_line = [l for l in lines if re.match(box_vector_new_regex,l)][0]
		vecs_new = re.findall('\s*box vectors\s*:([^\(]+)',new_line)[0]
		try: vecs_new = [float(i) for i in vecs_new.strip(' ').split()]
		except: vecs_new = [float(i) for i in re.findall(runon_regex,vecs_new)[0]]
	except:
		import pdb;pdb.set_trace()
	#---no need to keep the output since it is a verbatim copy for diagnostic only
	os.remove(os.path.join(state.here,gro+'.gro'))
	#import pdb;pdb.set_trace()
	return vecs_old,vecs_new

def count_molecules(structure,resname):
	"""
	Count the number of molecules in a system using make_ndx.
	"""
	gmx('make_ndx',structure=structure,ndx=structure+'-count',
		log='make-ndx-%s-check'%structure,inpipe='q\n')
	with open(state.here+'log-make-ndx-%s-check'%structure) as fp: lines = fp.readlines()
	if not resname: raise Exception('cannot count a null resname: %s'%resname)
	try:
		residue_regex = '^\s*[0-9]+\s+%s\s+\:\s+([0-9]+)\s'%resname
		count, = [int(re.findall(residue_regex,l)[0]) for l in lines if re.match(residue_regex,l)]
	except: raise Exception('cannot find resname "%s" in %s'%(resname,'make-ndx-%s-check'%structure))
	return count

def trim_waters(structure='solvate-dense',gro='solvate',gap=3,boxvecs=None,method='aamd',boxcut=True):
	"""
	ABSOLUTE FINAL VERSION OF THIS FUNCTION HOPEFULLY GOD WILLING
	trim_waters(structure='solvate-dense',gro='solvate',gap=3,boxvecs=None)
	Remove waters within a certain number of Angstroms of the protein.
	#### water and all (water and (same residue as water within 10 of not water))
	note that we vided the solvate.gro as a default so this can be used with any output gro file
	IS IT A PROBLEM THAT THIS DOESN'T TOUCH THE IONS??
	"""
	use_vmd = state.q('use_vmd',False)
	if (gap != 0.0 or boxcut) and use_vmd:
		if method == 'aamd': watersel = "water"
		elif method == 'cgmd': watersel = "resname %s"%state.q('sol')
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
		with open(state.here+'script-vmd-trim.tcl','w') as fp:
			for line in vmdtrim: fp.write(line+'\n')
		vmdlog = open(state.here+'log-script-vmd-trim','w')
		#vmd_path = state.gmxpaths['vmd']
		vmd_path = 'vmd'

		#---previously used os.environ['VMDNOCUDA'] = "1" but this was causing segfaults on green
		p = subprocess.Popen('VMDNOCUDA=1 '+vmd_path+' -dispdev text -e script-vmd-trim.tcl',
			stdout=vmdlog,stderr=vmdlog,cwd=state.here,shell=True,executable='/bin/bash')
		p.communicate()
		#---!
		#with open(wordspace['bash_log'],'a') as fp:
		#	fp.write(gmxpaths['vmd']+' -dispdev text -e script-vmd-trim.tcl &> log-script-vmd-trim\n')
		gmx_run(state.gmxpaths['editconf']+' -f %s-vmd.pdb -o %s.gro -resnr 1'%(gro,gro),
			log='editconf-convert-vmd')
	#---scipy is more reliable than VMD
	elif gap != 0.0 or boxcut:
		import scipy
		import scipy.spatial
		import numpy as np
		#---if "sol" is not in the state we assume this is atomistic and use the standard "SOL"
		watersel = state.q('sol','SOL')
		incoming = read_gro(structure+'.gro')
		is_water = np.array(incoming['residue_names'])==watersel
		is_not_water = np.array(incoming['residue_names'])!=watersel
		water_inds = np.where(is_water)[0]
		not_water_inds = np.where(np.array(incoming['residue_names'])!=watersel)[0]
		points = np.array(incoming['points'])
		residue_indices = np.array(incoming['residue_indices'])
		if gap>0:
			#---previous method used clumsy/slow cdist (removed)
			#---use scipy KDTree to find atom names inside the gap
			#---note that order matters: we wish to find waters too close to not_waters
			close_dists,neighbors = scipy.spatial.KDTree(points[not_water_inds]).query(points[water_inds],
				distance_upper_bound=gap/10.0)
			#---use the distances to find the residue indices for waters that are too close 
			excludes = np.array(incoming['residue_indices'])[is_water][np.where(close_dists<=gap/10.0)[0]]
			#---get residues that are water and in the exclude list
			#---note that the following step might be slow
			exclude_res = [ii for ii,i in enumerate(incoming['residue_indices']) if i in excludes and is_water[ii]]
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
	else: raise Exception('you need to either trim the box or remove waters in a gap')

def solvate_protein(structure,top):
	"""
	Standard solvate procedure for atomistic protein in water.
	! STILL USING THIS BECAUSE NO scipy and because we cannot find spc216 in the other one
	"""
	#---purge the wordspace of solvent and anions in case we are resuming
	for key in [state.q('anion'),state.q('cation'),'SOL']:
		if key in list(zip(*state.composition))[0]:
			del state.composition[list(zip(*state.composition))[0].index(key)]
	gmx('editconf',structure=structure,gro='solvate-box-alone',
		log='editconf-checksize',d=0)
	with open(state.here+'log-editconf-checksize','r') as fp: lines = fp.readlines()
	boxdims = map(lambda y:float(y),re.findall('\s*box vectors \:\s*([^\s]+)\s+([^\s]+)\s+([^\s]+)',
		list(filter(lambda x:re.match('\s*box vectors',x),lines)).pop()).pop())
	boxvecs = tuple([i+2*state.q('water_buffer') for i in boxdims])
	center = tuple([i/2. for i in boxvecs])
	#---cube is not implemented yet
	gmx('editconf',structure=structure,gro='solvate-protein',
		#flags='-center %f %f %f'%center+' '+'-box %f %f %f'%boxvecs,
		log='editconf-center-protein')
	gmx('genbox',structure='solvate-protein',solvent=state.q('solvent'),
		gro='solvate-dense',log='genbox-solvate')
		#top='solvate-standard',
	#---trim waters if the protein_water_gap setting is not False
	water_gap = state.q('protein_water_gap')
	if water_gap: 
		try:
			import scipy
			trim_waters(structure='solvate-dense',gro='solvate',gap=water_gap,boxvecs=boxvecs)
		except:
			status('failed to load scipy so continuing without a water_gap',tag='warning')
			copy_file('solvate-dense.gro','solvate.gro')
	else: copy_file('solvate-dense.gro','solvate.gro')
	gmx('make_ndx',structure='solvate',ndx='solvate-water-check',inpipe='q\n',
		log='make-ndx-solvate-check')
	with open(state.here+'log-make-ndx-solvate-check','r') as fp: lines = fp.readlines()
	nwaters = int(re.findall('\s*[0-9]+\s+Water\s+:\s+([0-9]+)\s+atoms',
		list(filter(lambda x:re.match('\s*[0-9]+\s+Water',x),lines)).pop()).pop())/\
		state.q('n_water_pts',3)
	state.water_without_ions = nwaters
	component('SOL',count=nwaters)
	#---add the suffix so that water is referred to by its name in the settings
	include(state.q('water'),ff=True)
	write_top('solvate.top')

def restuff(structure,gro,tpr,ndx):
	"""
	Restuff everything in the box.
	Used as a prelude for the generic solvate function.
	! Desperately needs a better name.
	"""
	#---added to the beginning of solvate for the bilayers. removed for proteins
	#---! is above necessary ???
	#---re-stuff everything in the box
	#---! might want to use the center flag on trjconv
	gmx('trjconv',structure=structure,inpipe='0\n',pbc='mol',
		tpr=tpr,ndx=ndx,gro=gro,log='trjconv-restuff')

def center_by_group(structure,gro,selection):
	"""
	Center a particular selection in the box.
	Similar to "restuff" above.
	"""
	ndx = 'system-group-center'
	gmx('make_ndx',structure=structure,ndx=ndx,
		inpipe='keep 0\n%s\nq\n'%selection,
		log='make-ndx-counterions-check')
	tpr = os.path.splitext(gmx_get_last_call('mdrun')['flags']['-s'])[0]
	#---we send "1" then "0" to center on the second group while "system" is the first
	gmx('trjconv',structure=structure,inpipe='1\n0\n',pbc='mol',
		center=True,tpr=tpr,ndx=ndx,gro=gro,log='trjconv-center')

def solvate(structure,gro,edges=None,center=False):
	"""
	Standard solvate procedure for atomistic protein in water.
	Often requires restuff above.
	"""
	#---purge the wordspace of solvent and anions in case we are resuming
	for key in [state.q('anion'),state.q('cation'),'SOL']:
		if key in list(zip(*state.composition))[0]:
			del state.composition[list(zip(*state.composition))[0].index(key)]
	#---make an oversized water box
	boxdims_old,boxdims = get_box_vectors(structure)
	newdims = boxdims_old
	#---impose the total box thickness here!
	if state.thickness and edges: raise Exception('cannot set both thickness and edges')
	if state.q('thickness'): 
		boxdims[2] = state.q('thickness')
		boxdims_old[2] = state.q('thickness')
	if edges:
		#---custom water buffers in each direction require that we make a new box
		water_edges = [float(j) for j in state.water_edges]
		if not len(water_edges)==3: raise Exception('water_edges must be a triplet')
		boxdims_old = [boxdims_old[jj]+2*water_edges[jj] for jj in range(3)]
		structure_new = structure+'-centered'
		gmx('editconf',structure=structure,gro=structure_new,
			box=' '.join([str(j) for j in boxdims_old]),c=True,log='editconf-recenter')
		structure = structure_new
	#---if no solvent argument we go and fetch it
	solvent = state.q('solvent','spc216')
	if solvent=='spc216' and not os.path.isfile(state.here+'spc216.gro'):
		share_dn = gmx_get_share()
		shutil.copyfile(os.path.join(share_dn,'spc216.gro'),state.here+'spc216.gro')
	#---! solvent must be centered. for some reason spc216 is not in the box entirely.
	if solvent=='spc216':
		_,boxdims_spc216 = get_box_vectors('spc216')
		gmx('editconf',structure='spc216',gro='spc216-center',
			center=' '.join([str(i/2.) for i in boxdims_spc216]),log='spc216-recenter')
		solvent = 'spc216-center'
	#---get the basedim for the incoming water box
	basedim,_ = get_box_vectors(solvent)
	#---use the preexisting box vectors
	#---! fixed this from newdims to boxdims_old since the solvate function works in-place
	nbox = ' '.join([str(int(i/basedim[ii]+1)) for ii,i in enumerate(boxdims_old)])
	gmx('genconf',structure=solvent,gro='solvate-empty-uncentered-untrimmed',nbox=nbox,log='genconf')
	gro_combinator(structure+'.gro','solvate-empty-uncentered-untrimmed.gro',
		box=boxdims_old,cwd=state.here,gro='solvate-dense')
	atom_resolution = atomistic_or_coarse()
	trim_waters(structure='solvate-dense',gro=gro,gap=state.q('water_buffer',3),
		boxvecs=boxdims_old,method=atom_resolution,boxcut=True)
	#---! ugly
	sol = state.q('sol','SOL')
	nwaters = count_molecules(gro,sol)/({'aamd':3.0,'cgmd':1.0}[atom_resolution])
	if round(nwaters)!=nwaters: raise Exception('[ERROR] fractional water molecules')
	else: nwaters = int(nwaters)
	component(sol,count=nwaters)
	state.bilayer_dimensions_solvate = boxdims_old
	state.water_without_ions = nwaters

def counterions(structure,top=None,includes=None,ff_includes=None,gro='counterions'):
	"""
	Standard procedure for adding counterions.
	The resname must be understandable by "r RESNAME" in make_ndx and writes to the top file.
	Note that the ``top`` argument is not used and should be removed after checking downstream.
	"""
	#---we store the water resname in the wordspace as "sol"
	resname =  state.q('sol','SOL')
	#---! the following section fails on the helix-0 test set which tracks water accurately
	if True:
		#---clean up the composition in case this is a restart
		for key in ['cation','anion',resname]:
			try: state.composition.pop(list(zip(*state.composition))[0].index(state.q(key)))
			except: pass
		component(resname,count=state.water_without_ions)
	#---write the topology file as of the solvate step instead of copying them (genion overwrites top)
	write_top('counterions.top')
	gmx('grompp',base='genion',structure=structure,
		top='counterions',mdp='input-em-steep-in',
		log='grompp-genion',maxwarn=state.q('maxwarn',0))
	gmx('make_ndx',structure=structure,ndx='solvate-waters',
		inpipe='keep 0\nr %s\nkeep 1\nq\n'%resname,
		log='make-ndx-counterions-check')
	if not state.ionic_strength: raise Exception('specify ionic strength in the settings (in mol/L)')
	for key in ['cation','anion']:
		if not state.q(key,None): raise Exception('you must specify %s in settings'%key)
	gmx('genion',base='genion',gro=gro,ndx='solvate-waters',
		cation=state.cation,anion=state.anion,
		conc='%f'%state.q('ionic_strength'),neutral=True,
		log='genion')
	with open(state.here+'log-genion','r') as fp: lines = fp.readlines()
	declare_ions = list(filter(lambda x:re.search('Will try',x)!=None,lines)).pop()
	ion_counts = re.findall(
		'^Will try to add ([0-9]+)\+?\-? ([\w\+\-]+) ions and ([0-9]+) ([\w\+\-]+) ions',
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

def write_structure_pdb(structure,pdb):
	"""
	Infer the starting residue from the original PDB and write structure.pdb with the correct indices
	according to the latest GRO structure (typically counterions.gro).
	"""
	#---automatically center the protein in the box here and write the final structure
	gmx('make_ndx',structure=structure,ndx='counterions-groups',
		log='make-ndx-counterions',inpipe='q\n',)
	with open(state.here+'log-make-ndx-counterions','r') as fp: lines = fp.readlines()
	relevant = [list(filter(lambda x:re.match('\s*[0-9]+\s+%s'%name,x),lines))
		for name in ['System','Protein']]
	groupdict = dict([(j[1],int(j[0])) for j in 
		[re.findall('^\s*([0-9]+)\s(\w+)',x[0])[0] for x in relevant]])
	gmx('trjconv',ndx='counterions-groups',structure='counterions-minimized',
		inpipe='%d\n%d\n'%(groupdict['Protein'],groupdict['System']),
		log='trjconv-counterions-center',tpr='em-counterions-steep',gro='system')
	with open(state.here+pdb,'r') as fp: lines = fp.readlines()
	startres = int([line for line in lines if re.match('^ATOM',line)][0][23:26+1])
	gmx('editconf',structure=structure,o='structure.pdb',resnr=startres,
		log='editconf-structure-pdb')

###---EQUILIBRATE + MINIMIZE

def minimize(name,method='steep',top=None,restraints=False):
	"""
	Standard minimization procedure.
	"""
	log_base = 'grompp-%s-%s'%(name,method)
	grompp_kwargs = {}
	if restraints==True: grompp_kwargs['r'] = '%s.gro'%name
	elif restraints: grompp_kwargs['r'] = restraints
	gmx('grompp',base='em-%s-%s'%(name,method),top=name if not top else re.sub(r'^(.+)\.top$',r'\1',top),
		structure=name,log=log_base,mdp='input-em-%s-in'%method,nonessential=True,
		maxwarn=state.q('maxwarn',0),**grompp_kwargs)
	tpr = state.here+'em-%s-%s.tpr'%(name,method)
	if not os.path.isfile(tpr): 
		try:
			#! note that this error reporting resembles that in gmx_run
			from calls import gmx_error_strings
			log_fn = state.here+'log-%s'%log_base
			with open(log_fn) as fp: log_text = fp.read()
			errors = re.findall('\n-{2,}(.*?(?:%s).*?)-{2,}'%('|'.join(gmx_error_strings)),log_text,re.M+re.DOTALL)
			for error in errors:
				status('caught error in %s:'%log_fn,tag='error')
				print('\n[ERROR] | '.join(error.split('\n')))
			raise Exception('cannot find %s. see errors above and check the grompp step.'%tpr)
		except: raise Exception('cannot find %s. check the grompp step.'%tpr)
	gmx('mdrun',base='em-%s-%s'%(name,method),log='mdrun-%s-%s'%(name,method))
	shutil.copyfile(state.here+'em-'+'%s-%s.gro'%(name,method),state.here+'%s-minimized.gro'%name)

def equilibrate_check(name):
	"""
	Check if the gro file for this step has been written.
	"""
	found = False
	fn = state.here+'md-%s.gro'%name
	if os.path.isfile(fn): 
		print('[NOTE] found %s'%fn)
		found = True
	return found

def equilibrate(groups=None,structure='system',top='system',stages_only=False,seq=None):
	"""
	Standard equilibration procedure.
	"""
	#---custom settings via kwarg otherwise we call out to the state
	if not seq:
		#---settings can be a python list or a comman-separated string
		eq_setting = state.q('equilibration')
		if eq_setting:
			if type(eq_setting) in str_types:
				try: seq = eq_setting.split(',')
				except: raise Exception('failed to parse equilibration setting: "%s"'%str(eq_setting))
			else: seq = eq_setting
		else: seq = []
	#---sequential equilibration stages
	for eqnum,name in enumerate(seq):
		if not equilibrate_check(name):
			gmx('grompp',base='md-%s'%name,top=top,
				structure=structure if eqnum == 0 else 'md-%s'%seq[eqnum-1],
				log='grompp-%s'%name,mdp='input-md-%s-eq-in'%name,
				maxwarn=state.q('maxwarn',0),**({'n':groups} if groups else {}))
			gmx('mdrun',base='md-%s'%name,log='mdrun-%s'%name,nonessential=True)
			if not os.path.isfile(state.here+'md-%s.gro'%name): 
				raise Exception('mdrun failure at %s'%name)
	#---stages only protects you from beginning with part numbers
	if not stages_only:
		#---first part of the equilibration/production run
		name = 'md.part0001'
		if not equilibrate_check(name) or seq == []:
			gmx('grompp',base=name,top=top,
				structure='md-%s'%seq[-1] if seq else structure,
				log='grompp-0001',mdp='input-md-in',
				maxwarn=state.q('maxwarn',0),**({'n':groups} if groups else {}))
			gmx('mdrun',base=name,log='mdrun-0001')

def restart_clean(part,structure,groups,posres_coords=None,mdp='input-md-in'):
	"""
	Perform a hard-restart that mimics the md.part0001 naming scheme.
	"""
	if type(part)!=int: raise Exception('part must be an integer')
	#---! other validations here? check for overwrites
	name = 'md.part%04d'%part
	flags = {'n':groups} if groups else {}
	#---! needs systematic restraint additions for all grompp !!!!!!!!!!!!
	if posres_coords: flags['r'] = posres_coords
	gmx('grompp',base=name,top='system',
		structure=structure,log='grompp-%04d'%part,mdp=mdp,
		maxwarn=state.q('maxwarn',0),**flags)
	gmx('mdrun',base=name,log='mdrun-%04d'%part)

def atomistic_or_coarse():
	"""
	We rely on tags to identify atomistic and coarse-grained simulations rather than settings.
	"""
	if not 'cgmd' in state.expt['tags'] and not 'aamd' in state.expt['tags']:
		raise Exception('neither `aamd` nor `cgmd` can be found in your `tags` key in your experiment')
	return 'cgmd' if 'cgmd' in state.expt['tags'] else 'aamd'

def grouper(ndx='system-groups',protein=True,lipids=True):
	"""
	Generic replacement for generating system-groups.ndx for various configurations.
	"""
	groups = ['SOLVENT']
	if not lipids: groups += ['LIPIDS']
	if not protein: groups += ['PROTEIN']
	atom_resolution = atomistic_or_coarse()
	if atom_resolution=='aamd': raise Exception('dev')
	#---track the list of selection commands
	class MakeNDXSelector:
		def __init__(self): self.sel,self.selno = ['keep 0','del 0'],0
		def ask(self,cmd,name=None):
			self.sel.append(cmd)
			#---send a name along only if we just made a new selection and we wish to name it
			if name: 
				self.sel.append("name %d %s"%(self.selno,name))
				self.selno += 1
		def final(self): return '\n'.join(self.sel)+'\nq\n'
	selector = MakeNDXSelector()
	#---we always include solvent
	#---! should we always use ION even if it is relevant only for MARTINI?
	sol_list = [state.sol,'ION',state.cation,state.anion]
	if any([not i for i in sol_list]): 
		#---! temporary intervension
		land = Landscape()
		#---! have to have ION for MARTINI still, ca testing of bilayer release on v823
		sol_list = [land.SOL,state.cation,state.anion,'ION']
		# raise Exception('solvent list has a null value: %s'%sol_list)
	selector.ask(" || ".join(['r '+r for r in sol_list]),name='SOLVENT')
	#---use landscapes to make the protein selection
	if protein:
		land = Landscape('martini')
		protein_selection = land.protein_selection()
		selector.ask(protein_selection,name='PROTEIN')
	if lipids: 
		if not state.lipids: raise Exception('the state must know the lipids to add them to a groups file')
		selector.ask('|'.join([' r %s '%i for i in state.lipids]),name='LIPIDS')
	#---create the final copy of groups
	#---make_ndx will throw a syntax error if a group has zero atoms so we have to be precise
	gmx('make_ndx',structure='system',ndx=ndx,log='make-ndx-groups',inpipe=selector.final())

def protein_laden(structure='system'):
	"""
	Infer if there are proteins in the simulation.
	"""
	from structure_tools import GMXStructure
	struct = GMXStructure(state.here+'%s.gro'%structure)
	land = Landscape()
	return np.any(np.in1d(struct.residue_names,land.protein_residues))
