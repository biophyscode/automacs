#!/usr/bin/python env

import re,os,glob

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
		'atoms':{'records':'id type resnr resname atom cgnr charge'},
		'bonds':{'records':'i j funct length force'},
		'constraints':{'records':'i j funct length'},
		'angles':{'records':'i j k funct angle force'},
		'dihedrals':{'records':'i j k l funct angle force'},
		'position_restraints':{'records':'ai  funct  fcx    fcy    fcz'},
		'exclusions':{'records':'i j'},
		'virtual_sites3':{'records':'site n0 n1 n2 funct a b'}
		}
	_entry_order = "moleculetype atoms bonds angles dihedrals constraints position_restraints".split()
	#---specify the ITP format for a molecule type
	_entry_defns = dict([(name,{'lines':details.get('lines','many'),'regex':
		'^\s*%s$'%(''.join(["(?P<"+kw+">.*?)\s"+('+' if dd<len(details['records'].split())-1 else '*') 
			for dd,kw in enumerate(details['records'].split())])),
		}) for name,details in _entry_abstracted.items()])
	#---drop any lines that only have comments
	_lam_strip_commented_lines = lambda self,x:[i.strip() for i in x.split('\n') 
		if not re.match(self._regex_commented_line,i)]
	#---amino acid codes
	_aa_codes3 = ['TRP','TYR','PHE','HIS','ARG','LYS','CYS','ASP','GLU',
		'ILE','LEU','MET','ASN','PRO','HYP','GLN','SER','THR','VAL','ALA','GLY']
	_aa_codes1 = 'WYFHRKCDEILMNPOQSTVAG'

	def __init__(self,itp,**kwargs):

		"""
		Unpack an ITP file.
		"""

		self.molecules = {}
		self.itp_source = itp

		self.ifdefs = []
		self.ifdefs.extend(kwargs.get('ifdefs',[]))
		with open(self.itp_source) as fp: self.itp_raw = fp.read()
		#---extract definition lines
		defines = re.findall(r"^\s*(\#define.+)$",self.itp_raw,re.M)
		self.defines = list(set(defines))
		#---! need to add a check in case the defines are sequential and they override each other
		#---extract raw molecule types and process them
		for match in re.findall(self._regex_molecule,self.itp_raw,re.M+re.DOTALL):
			match_proc = self.entry_pre_proc(match)			
			moldef = self.process_moleculetype(match_proc)
			self.molecules[moldef['moleculetype']['molname']] = moldef

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

		assert name in self._entry_defns,'developing GMXTopology. missing entry for "%s"'%name
		spec = self._entry_defns[name]
		valids = self._lam_strip_commented_lines(text)
		lines = spec.get('lines',None)
		if lines and lines!='many':
			assert len(valids)==lines,'too many lines in %s'%name
		if lines == 1: 
			return {name:re.search(spec['regex'],valids[0]).groupdict()}
		else: 
			out = {name:[re.search(spec['regex'],v).groupdict() 
				for v in valids if not re.match('^\s*;',v)]}
			return out

	def process_moleculetype(self,text):

		"""
		Interpret a single moleculetype entry from a GROMACS itp file.
		"""

		entries = {}
		text_entries = re.findall(self._regex_bracket_entry,text,re.M+re.DOTALL)
		for name,entry in text_entries:
			entries.update(**self.entry_proc(name,entry))
		return entries

	def write(self,fn):
		"""
		Write an ITP file.
		"""
		if os.path.isfile(fn): raise Exception('refusing to overwrite %s'%fn)
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
					for key in self._entry_abstracted[entry]['records'].split():
						line += '%s '%str(o[key])
					text.append(line)
			mol_entries.append('\n'.join(text))
		with open(fn,'w') as fp: fp.write('\n'.join(mol_entries))
