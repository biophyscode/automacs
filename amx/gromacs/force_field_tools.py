#!/usr/bin/env python

"""
Force field tools mediate naming schemes between various force fields.
"""

import os,json,glob,re
from topology_tools import GMXTopology

charmm_lipids = {
	
}

#---! we think the following section will replace landscape.json
#---! note that a landscape.json was removed from the charmm module but can be found in the history

landscape_spec = {
	'martini':{
		'ion':{'files':'inputs/martini/martini-sources.ff/martini-v2.0-ions.itp'},
		'lipid':{'files':'inputs/martini/martini-sources.ff/martini_v2.0_lipids_all_201506.itp'},
		},
	'charmm':{
		'ion':{'files':'inputs/charmm/charmm36.ff/ions.itp'},
		'tip3p':{'files':'inputs/charmm/charmm36.ff/tip3p.itp'},
		#---updated this: 'lipid':{'files':['inputs/charmm/lipid-tops/lipid*.itp']},
		#---! dangerous to hard-code the path to charmm instead of putting this in expts file
		'lipid':{'files':['inputs/charmm/charmm36.ff/lipids/%s.itp'%i for i in 
			['DOPC','DOPS','POPC','DOPE','SAPI','PI2P']]},
		'sterol':{'files':['inputs/charmm/charmm36.ff/lipids/CHL1.itp']},
		}
	}

special_defs = {
	'martini':{'SOL':'W'},
	'charmm':{'SOL':'W'},
}

def force_field_family():
	"""
	Get the family name for the force field i.e. charmm or martini.
	"""
	if not state.force_field: 
		raise Exception('force_field_family needs to find force field in settings or state')
	is_charmm = re.search('charmm',state.force_field)
	is_martini = re.search('martini',state.force_field)
	if is_charmm and is_martini: 
		raise Exception('force field matches both charmm and martini somehow: %s'%state.force_field)
	elif not is_charmm and not is_martini:
		raise Exception('force field matches neither charmm nor martini: %s'%state.force_field)
	else: return 'charmm' if is_charmm else 'martini'
	
class Landscape:
	"""
	Handle force field naming schemes.

	! lay out the types in meta.json?
	This class reads the force field files according to types and exposes them to automacs in a way that
	makes it easy to ask for ion definitions by type.
	"""

	#---canonical protein residue names for all force fields
	protein_residues = ['GLH','ILE','ALAD','GLUH','GLN','HISH','ASN1','HYP','GLY','HIP',
		'ARGN','MSE','CYS1','GLU','CYS2','CYS','HISE','ASP','SER','HSD','HSE','PRO','CYX','ASPH',
		'ORN','HSP','HID','HIE','LYN','DAB','ASN','CYM','HISD','VAL','THR','HISB','HIS','HIS1',
		'HIS2','TRP','HISA','ACE','ASH','CYSH','PGLU','LYS','PHE','ALA','QLN','MET','LYSH','NME',
		'LEU','ARG','TYR']

	def __init__(self,ff=None,cwd=None):
		"""
		This class wraps the landscape files.
		"""
		self.objects = {}
		if not ff: ff = force_field_family()
		cwd = os.getcwd() if not cwd else cwd

		#---???
		self.itps = {}
		for cat,spec in landscape_spec[ff].items():
			if 'files' in spec:
				files = [spec['files']] if type(spec['files'])!=list else spec['files']
				files_collect = [i for j in [glob.glob(os.path.join(cwd,expr)) for expr in files] for i in j]
				if not files_collect: raise Exception('cannot find files via "%s"'%files)
				for fn in files_collect:
					#---? check for overwrites
					#---save the topologies by ITP file
					self.itps[fn] = GMXTopology(fn).molecules
					for name,mol in self.itps[fn].items():
						if name in self.objects: 
							raise Exception('molecule named %s already registered'%name)
						resnames = [a['resname'] for a in mol['atoms']]
						if not len(list(set(resnames)))==1: 
							raise Exception('molecule with multiple resnames under development: %s'%name)
						try: charge = sum([float(a['charge']) for a in mol['atoms']])
						except: raise Exception(
							'failed to compute charge. problem with the ITP file or reader.')
						obj = {
							'cat':cat,
							'n':len(mol['atoms']),
							'atoms':[a['atom'] for a in mol['atoms']],
							'resname':list(set(resnames))[0],
							'charge':sum([float(a['charge']) for a in mol['atoms']]),
							'fn':fn,}
						self.objects[name] = obj
			else: raise Exception('you must supply files list in the landscape spec')

		#---! recent changes to the data structure above are useful but to get the GMXTopology object
		#---! ...you have to do: land.itps[land.objects['POPC']['fn']]['POPC']

		#---special defs go right into members
		for key,val in special_defs[ff].items(): self.__dict__[key] = val

		#---populate categories
		self.categories = list(set([v['cat'] for k,v in self.objects.items()]))

	def objects_by_category(self,cat):
		"""
		Return all object names in a particular category.
		"""
		return [k for k,v in self.objects.items() if v['cat']==cat]

	def lipids(self): return [k for k,v in self.objects.items() if v['cat']=='lipid']
	def sterols(self): return [k for k,v in self.objects.items() if v['cat']=='sterol']
	def anions(self): return [k for k,v in self.objects.items() if v['cat']=='ion' and v['charge'] < 0]
	def cations(self): return [k for k,v in self.objects.items() if v['cat']=='ion' and v['charge'] > 0]
	def ions(self): return [k for k,v in self.objects.items() if v['cat']=='ion']

	def protein_selection(self):
		"""
		Return a protein selection string for make_ndx.
		"""
		#---! note that we do not match this to the protein ITP in e.g. martini just yet
		return ' or '.join(['r %s'%i for i in self.protein_residues])

	def my(self,struct,cat):
		"""
		Get the item names for a GMXStructure.
		Uses atom names. Returns any atom names that apply, so this is really ion-specific !!!
		"""
		if not hasattr(self,cat): raise Exception('category %s not in this landscape'%cat)
		object_names = getattr(self,cat)()
		return [i for j in [self.objects[o]['atoms'] for o in object_names] for i in j]
