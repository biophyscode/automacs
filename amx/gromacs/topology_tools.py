#!/usr/bin/env python

import sys,re,os,glob,json,shutil
import numpy as np
#---amx is already in the path when importing amx/gromacs
from utils import str_types

class GMXForceField:
	"""
	A collection of GMXTopology files
	"""
	def __init__(self,dirname):
		if not os.path.isdir(dirname): raise Exception('cannot find force field directory %s'%dirname)
		self.dirname = dirname
		self.itps = {}
		for fn in glob.glob(os.path.join(self.dirname,'*.itp')):
			self.itps[os.path.basename(fn)] = GMXTopology(fn)
	def molecules_list(self):
		#---we don not protect against repeated molecules, but gromacs does
		return [i for j in [v.molecules for v in self.itps.values()] for i in j]
	def molecule(self,name):
		which_itp = [fn for fn,itp in self.itps.items() if name in itp.molecules]
		if len(which_itp)==0: raise Exception('cannot find molecule %s in force field %s'%(name,self.dirname))
		elif len(which_itp)>1:
			print('[WARNING] molecule %s is repeated in %s: %s. '
				'using the first.'%(name,self.dirname,which_itp))
		return self.itps[which_itp[0]].molecules[name]

class GMXTopology:
	"""
	Represent a molecule topology.
	"""
	#---regex the ITP format
	_regex_molecule = r'^(\s*\[\s*moleculetype\s*\]\s*.*?)(?=\s*\[\s*moleculetype|\Z)'
	_regex_bracket_entry = r'^\s*\[\s*(.*?)\s*\]\s*(.*?)(?=(?:^\s*\[|\Z))'
	_regex_commented_line = r'^(\s*[\;\#].+|\s*)$'
	#_regex_ifdef_block = r"(?:\n#(if%sdef)\s*(.*?)\s*\n)(.*?)(\n#endif\s*\n)"
	#---it is important not to having any trailing parts
	_regex_ifdef_block = r'(?:\n#if%sdef\s*(.*?)\s*\n(.*?)\n#endif)'
	_regex_ifdef_block_sub = r'(?:\n#if%sdef\s*(%s)\s*\n(.*?)\n#endif)'
	_regex_define = r"^\s*(\#define.+)$"
	#---abstract definition of different ITP entries
	_entry_abstracted = {
		'moleculetype':{'records':'molname nrexcl','lines':1},
		'atoms':{'records':'id type resnr resname atom cgnr charge mass typeB chargeB massB'},
		'bonds':{'records':'i j funct length force'},
		'constraints':{'records':'i j funct length'},
		'angles':{'records':'i j k funct angle force'},
		'dihedrals':{'records':'i j k l funct angle force multiplicity'},
		'position_restraints':{'records':'ai  funct  fcx    fcy    fcz'},
		'exclusions':{'records':'i j'},
		'virtual_sites3':{'records':'site n0 n1 n2 funct a b'},
		'pairs':{'records':'ai aj funct c0 c1 c2 c3'},
		'cmap':{'records':'ai aj ak al am funct'},
		'settles':{'records':'OW funct doh dhh'},}
	#---! NOTE THAT THIS IS A CRITICAL LYNCHPIN. IF IT IS NOT ON HERE IT IS NOT WRITTEN
	_entry_order = ("moleculetype atoms bonds angles dihedrals constraints virtual_sites3 exclusions "+
		"position_restraints").split()
	#---specify the ITP format for a molecule type
	_entry_defns_original = dict([(name,{'lines':details.get('lines','many'),'regex':
		'^\s*%s$'%(''.join(["(?P<"+kw+">.*?)\s"+('+' if dd<len(details['records'].split())-1 else '*') 
			for dd,kw in enumerate(details['records'].split())])),
		}) for name,details in _entry_abstracted.items()])
	#---! note that some topology definitions include varying numbers of arguments, sometimes including the 
	#---! ...mass, sometimes excluding it, etc. which means that if we want to pick off the items with the 
	#---! ...original automatic-regex for records, we have to detect the number of items and only then create
	#---! ...the appropriate regex. for that reason we now save the regex as a list, detect the number of 
	#---! ...space-separated arguments, and then construct the regex on the fly, for each argument
	_entry_defns = dict([(name,{'lines':details.get('lines','many'),'regex':
		["(?P<"+kw+">.*?)\s" for dd,kw in enumerate(details['records'].split())],
		}) for name,details in _entry_abstracted.items()])
		#---drop any lines that only have comments
	_lam_strip_commented_lines = lambda self,x:[i.strip() for i in x.split('\n') 
		if not re.match(self._regex_commented_line,i)]
	#---amino acid codes
	_aa_codes3 = ['TRP','TYR','PHE','HIS','ARG','LYS','CYS','ASP','GLU',
		'ILE','LEU','MET','ASN','PRO','HYP','GLN','SER','THR','VAL','ALA','GLY']
	_aa_codes1 = 'WYFHRKCDEILMNPOQSTVAG'

	def __init__(self,itp=None,**kwargs):

		"""
		Unpack an ITP file.
		"""

		self.molecules = {}
		self.itp_source = itp
		self.defs = kwargs.pop('defs',{})
		self.constraints_to_bonds = kwargs.pop('constraints_to_bonds',False)
		if kwargs: raise Exception('unprocessed kwargs: %s'%kwargs)

		if self.itp_source:
			with open(self.itp_source) as fp: self.itp_raw = fp.read()
			#---extract definition lines
			defines = re.findall(r"^\s*(\#define.+)$",self.itp_raw,re.M)
			#---! dropping the ifdefs above and the deprecated entry_pre_proc flag
			self.preproc()
			self.defines = list(set(defines))
			#---extract includes lines
			self.includes = re.findall(r"^\s*\#include\s*\"(.+)\"\s*$",self.itp_raw,re.M)
			#---! need to add a check in case the defines are sequential and they override each other
			#---extract raw molecule types and process them
			for match in re.findall(self._regex_molecule,self.itp_raw,re.M+re.DOTALL):
				#---note that comment-only lines are stripped elsewhere, but here we remove comment tails
				match_no_comment_tails = re.sub('[^\n;];.*?(\n|\Z)','\n',match,flags=re.M)
				match_proc = self.entry_pre_proc(match_no_comment_tails)	
				moldef = self.process_moleculetype(match_proc)
				self.molecules[moldef['moleculetype']['molname']] = moldef
			if self.constraints_to_bonds:
				for molname in self.molecules:
					if 'constraints' in self.molecules[molname]:
						self.molecules[molname]['bonds'] = (self.molecules[molname]['bonds'] +
							[dict(force=30000,**i) for i in self.molecules[molname].pop('constraints')])
		#---if no source we create a blank topology
		else: self.defines = []

	def preproc(self):
		"""
		"""
		#---first we detect any ifdef/ifndef statements
		ifdefs = re.findall(self._regex_ifdef_block%'',self.itp_raw,flags=re.DOTALL+re.M)
		ifndefs = re.findall(self._regex_ifdef_block%'n',self.itp_raw,flags=re.DOTALL+re.M)
		defnames_ja = list(set(list(zip(*ifdefs)[0]))) if ifdefs else []
		defnames_no = list(set(list(zip(*ifndefs)[0]))) if ifndefs else []
		defs = {}
		for key in defnames_ja: defs[key] = True
		#---default is NOT to include a block (we run this second)
		for key in defnames_no: defs[key] = False
		#---overrides from the user
		for key,val in self.defs.items(): defs[key] = val
		#---make replacements
		for key,val in defs.items():
			#---keeper
			#---! temporarily added \n before group 2 below for martini cholesterol
			self.itp_raw = re.sub(self._regex_ifdef_block_sub%('' if val else 'n',key),r"\n\2",
				self.itp_raw,flags=re.M+re.DOTALL)
			#---discard
			self.itp_raw = re.sub(self._regex_ifdef_block_sub%('n' if val else '',key),'',
				self.itp_raw,flags=re.M+re.DOTALL)

	def entry_pre_proc(self,match):

		"""
		Catalogue and apply preprocessor flags, namely ifdef.
		"""

		match_proc = str(match)
		
		#---! THIS WAS (false) A TERRIBLE MISTAKE !!!!!!!! DOCUMENT IT!
		if False:
			#---take or leave ifn?def...endif blocks based on the pre_proc_flags
			#---! previously named "pre_proc_flags" but it looks like we want this to be ifdefs
			for key,val in self.pre_proc_flags.items():
				keeper = self._regex_ifdef_block%{True:'',False:'n'}[val]
				match_proc = re.sub(keeper,r"\2",match_proc,flags=re.M+re.DOTALL)
				dropper = self._regex_ifdef_block%{True:'',False:'n'}[not val]
				match_proc = re.sub(dropper,"",match_proc,flags=re.M+re.DOTALL)
				import ipdb;ipdb.set_trace()
				xxx
			if re.search('ifdef',match_proc):
				xxx
		return match_proc

	def entry_proc(self,name,text):

		"""
		Process a single entry type in ???
		"""

		if name not in self._entry_defns:
			raise Exception('developing GMXTopology. missing entry for "%s"'%name)
		spec = self._entry_defns[name]
		valids = self._lam_strip_commented_lines(text)
		lines = spec.get('lines',None)
		if lines and lines!='many':
			if len(valids)!=lines: raise Exception('too many lines in %s'%name)

		#---! removed after changing the entry defs for a flexible number of columns
		if False:
			if lines == 1: 
				return {name:re.search(spec['regex'],valids[0]).groupdict()}
			else: 
				out = {name:[re.search(spec['regex'],v).groupdict() 
					for v in valids if not re.match('^\s*;',v)]}
				return out

		#---the following handles both one-line and many-line entries
		atoms = []
		for v in [i for i in valids if not re.match('^\s*;',i)]:
			if re.search(';',v): 
				import ipdb;ipdb.set_trace()
				raise Exception('comment-strippper failed in %s'%name)
			n_cols = len(v.split())
			regex_all = spec['regex'][:n_cols]
			#---since the regex is dynamic depending on the number of columns, we have to assign 
			#---...regex plus/star wildcards dynamically too
			this_regex = '^\s*%s$'%(''.join([
				r+('+' if dd<len(regex_all)-1 else '*') for dd,r in enumerate(regex_all)]))
			if not re.search(this_regex,v):
				import ipdb;ipdb.set_trace()
			atoms.append(re.search(this_regex,v).groupdict())
		## if not atoms: raise Exception('no atoms (!) in molecule %s'%name)
		#---! cannot stop if no atoms because sometimes e.g. dihedrals are just blank
		if lines==1: atoms = atoms[0]
		return {name:atoms}

	def process_moleculetype(self,text):

		"""
		Interpret a single moleculetype entry from a GROMACS itp file.
		"""

		entries = {}
		text_entries = re.findall(self._regex_bracket_entry,text,re.M+re.DOTALL)
		for name,entry in text_entries:
			entries.update(**self.entry_proc(name,entry))
		return entries

	def write(self,fn,overwrite=False):
		"""
		Write an ITP file.
		"""
		if os.path.isfile(fn) and not overwrite: raise Exception('refusing to overwrite %s'%fn)
		mol_entries = []
		#---start with the defines
		mol_entries = list(self.defines)
		for mol,molspec in self.molecules.items():
			text = []
			for entry in [i for i in self._entry_order if i in molspec]:
				text.append('[%s]\n;%s'%(entry,self._entry_abstracted[entry]['records']))
				over = [molspec[entry]] if type(molspec[entry])!=list else molspec[entry]
				for o in over:
					line = ''
					#---changed _entry_abstracted to handle a flexible stopping point in that list
					#---...here we check that the items on the list are present
					header_keys = self._entry_abstracted[entry]['records'].split()
					if type(o)!=dict: 
						import ipdb;ipdb.set_trace()
					if not set(header_keys[:len(o.keys())])==set(o.keys()):
						raise Exception('the set of keys in this entry does not match a starting subsequence '+
							'from the header. the available keys are %s and the header is %s'%(o.keys(),header_keys))
					for key in header_keys[:len(o.keys())]:
						line += '%s '%str(o[key])
					text.append(line)
			mol_entries.append('\n'.join(text))
		with open(fn,'w') as fp: fp.write('\n'.join(mol_entries))

	def molecule_rename(self,old,rename):
		"""
		"""
		self.molecules[old]['moleculetype']['molname'] = rename
		self.molecules[rename] = self.molecules.pop(old)

	def add_molecule(self,**kwargs):
		"""
		Add a new molecule.
		"""
		for key,val in kwargs.items():
			if key in self.molecules: raise Exception('refusing to overwrite molecule: %s'%key)
		else: self.molecules[key] = val

	def restrain_atoms(self,*names,**kwargs):
		"""
		Apply a restraint to a molecule.
		"""
		mol = kwargs.pop('mol',0)
		forces = {}
		for k in 'xyz': forces['fc%s'%k] = kwargs.pop('fc%s'%k,0)
		if kwargs: raise Exception('unprocessed kwargs')
		if not mol or mol not in self.molecules: raise Exception('cannot find molecule %s'%mol)
		#---generate blank restraints if they do not exist otherwise we overwrite what is already there
		#---! note that this might be dangerous
		if 'position_restraints' not in self.molecules[mol]:
			posres_custom = {'funct':'1','fcy':'0','ai':'1','fcx':'0','fcz':'0'}
			posres_all = [dict(posres_custom,ai=str(ii+1)) 
				for ii,i in enumerate(self.molecules[mol]['atoms'])]
			self.molecules[mol]['position_restraints'] = posres_all	
		atoms = [i['atom'] for i in self.molecules[mol]['atoms']]
		#---loop over target atom names
		for atom_name in names:
			#---loop over directions to apply the forces
			for k,v in forces.items(): 
				self.molecules[mol]['position_restraints'][atoms.index(atom_name)][k] = v

	#---DEVELOPING MORE CAREFUL BOND PARSINGS
		
	def get_bonds_by_regex(self,molname,patterns,include_resname=False):
		"""
		Collect all possible hydrogen bonds by residue name and atom.
		"""

		mol = GMXTopologyMolecule(self.molecules[molname])
		bonds = mol.get_bonds()
		names = mol.get_atom_spec_by_bond(*bonds)
		if type(patterns) in str_types: patterns = []
		if not len(patterns) in [1,2]: raise Exception('patterns must be length 1 or 2: %s'%patterns) 
		matching_bonds = np.array([ii for ii,i in enumerate(names) 
			if sum([np.any([(1 if re.match(regex,n) else 0) 
				for regex in patterns]) for n in i])==len(patterns)])
		#---! this function returns only a list of name pairs for hydrogen bond donors
		if len(matching_bonds)==0: return []
		bond_pairs_by_name = [tuple(j) 
			for j in mol.get_atom_spec_by_bond(*np.array(bonds)[matching_bonds],key='atom')]
		if include_resname:
			bond_pairs_by_resname = [tuple(j) 
				for j in mol.get_atom_spec_by_bond(*np.array(bonds)[matching_bonds],key='resname')]
			return zip(bond_pairs_by_resname,bond_pairs_by_name)
		return bond_pairs_by_name

class GMXTopologyMolecule:

	"""
	PROTOYPING a molecule class. Wraps ITP molecules in some helpful functions.
	"""

	def __init__(self,molecule): self.mol = molecule

	def get_atom(self,atom):
		"""
		HACK. Get an atom from a molecule by index number.
		"""
		matches = [ii for ii,i in enumerate(self.mol['atoms']) if i['id']==str(atom)]
		if len(matches)>1: raise Exception('found too many atoms with id %s in this molecule'%atom)
		elif len(matches)==0: raise Exception('no atom with id %s in this molecule'%atom)
		else: return matches[0]

	def get_bonds(self):
		"""
		Return indices for the bond list.
		"""
		return [[self.get_atom(atom=bond[l]) for l in 'ij'] for bond in self.mol['bonds']]

	def get_atom_spec_by_bond(self,*args,**kwargs):
		"""Return atom names."""
		key = kwargs.pop('key','atom')
		if kwargs: raise Exception('unprocessed kwargs %s'%kwargs)
		#---filter all bonds for those involving an atom with a name starting with the letter "H"
		names = np.array([[self.mol['atoms'][i][key],self.mol['atoms'][j][key]] for i,j in args])
		return names
