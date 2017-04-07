#!/usr/bin/env python

import re,os,glob,json,shutil

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
		if len(which_itp)>1: 
			raise Exception('molecule %s is repeated somewhere in the force field %s'%(name,self.dirname))
		elif len(which_itp)==0: raise Exception('cannot find molecule %s in force field %s'%(name,self.dirname))
		else: return self.itps[which_itp[0]].molecules[name]

class GMXTopology:
	"""
	Represent a molecule topology.
	"""
	#---regex the ITP format
	_regex_molecule = r'^(\s*\[\s*moleculetype\s*\]\s*.*?)(?=\s*\[\s*moleculetype|\Z)'
	_regex_bracket_entry = r'^\s*\[\s*(.*?)\s*\]\s*(.*?)(?=(?:^\s*\[|\Z))'
	_regex_commented_line = r'^(\s*[\;\#].+|\s*)$'
	_regex_ifdef_block = r"(?:\n#(if%sdef)\s*(.*?)\s*\n)(.*?)(\n#endif\s*\n)"
	_regex_define = r"^\s*(\#define.+)$"
	#---abstract definition of different ITP entries
	_entry_abstracted = {
		'moleculetype':{'records':'molname nrexcl','lines':1},
		'atoms':{'records':'id type resnr resname atom cgnr charge mass typeB chargeB massB'},
		'bonds':{'records':'i j funct length force'},
		'constraints':{'records':'i j funct length'},
		'angles':{'records':'i j k funct angle force'},
		'dihedrals':{'records':'i j k l funct angle force'},
		'position_restraints':{'records':'ai  funct  fcx    fcy    fcz'},
		'exclusions':{'records':'i j'},
		'virtual_sites3':{'records':'site n0 n1 n2 funct a b'},
		'pairs':{'records':'ai aj funct c0 c1 c2 c3'},
		'cmap':{'records':'ai aj ak al am funct'},
		}
	_entry_order = "moleculetype atoms bonds angles dihedrals constraints position_restraints".split()
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

		self.ifdefs = []
		self.ifdefs.extend(kwargs.get('ifdefs',[]))
		if self.itp_source:
			with open(self.itp_source) as fp: self.itp_raw = fp.read()
			#---extract definition lines
			defines = re.findall(r"^\s*(\#define.+)$",self.itp_raw,re.M)
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
		#---if no source we create a blank topology
		else:
			self.defines = []

	def entry_pre_proc(self,match):

		"""
		Catalogue and apply preprocessor flags, namely ifdef.
		"""

		match_proc = str(match)
		
		if False:
			#---take or leave ifn?def...endif blocks based on the pre_proc_flags
			for key,val in self.pre_proc_flags.items():
				keeper = self._regex_ifdef_block%{True:'',False:'n'}[val]
				match_proc = re.sub(keeper,r"\2",match_proc,flags=re.M+re.DOTALL)
				dropper = self._regex_ifdef_block%{True:'',False:'n'}[not val]
				match_proc = re.sub(dropper,"",match_proc,flags=re.M+re.DOTALL)
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
		
