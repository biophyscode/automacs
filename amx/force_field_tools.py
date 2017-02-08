#!/usr/bin/env python

"""
Force field tools mediate naming schemes between various force fields.
"""

import os,json,glob
from topology_tools import GMXTopology
from common import force_field_family

charmm_lipids = {
	
}

landscape_spec = {
	'martini':{
		'ion':{'files':'inputs/martini/martini-sources.ff/martini-v2.0-ions.itp'},
		'lipid':{'files':'inputs/martini/martini-sources.ff/martini_v2.0_lipids_all_201506.itp'},
		},
	'charmm':{
		'ion':{'files':'inputs/charmm/charmm36.ff/ions.itp'},
		'lipid':{'files':['inputs/charmm/lipid-tops/lipid*.itp']},
		}
	}

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

	def __init__(self,ff=None):
		"""
		This class wraps the landscape files.
		"""
		self.objects = {}
		if not ff: ff = force_field_family()

		#---load the ions
		for cat,spec in landscape_spec[ff].items():
			if 'files' in spec:
				files = [spec['files']] if type(spec['files'])!=list else spec['files']
				files_collect = [i for j in [glob.glob(expr) for expr in files] for i in j]
				if not files_collect: raise Exception('cannot find files via "%s"'%files)
				for fn in files_collect:
					for name,mol in GMXTopology(fn).molecules.items():
						if name in self.objects: 
							raise Exception('molecule named %s already registered'%name)
						resnames = [a['resname'] for a in mol['atoms']]
						if not len(list(set(resnames)))==1: 
							raise Exception('molecule with multiple resnames under development: %s'%name)
						try:
							charge = sum([float(a['charge']) for a in mol['atoms']])
						except: raise Exception(
							'failed to compute charge. problem with the ITP file or reader.')
						obj = {
							'cat':cat,
							'n':len(mol['atoms']),
							'atoms':[a['atom'] for a in mol['atoms']],
							'resname':list(set(resnames))[0],
							'charge':sum([float(a['charge']) for a in mol['atoms']]),
							}
						self.objects[name] = obj
			else: raise Exception('you must supply files list in the landscape spec')

		#---populate categories
		self.categories = list(set([v['cat'] for k,v in self.objects.items()]))

	def objects_by_category(self,cat):
		"""
		Return all object names in a particular category.
		"""
		return [k for k,v in self.objects.items() if v['cat']==cat]

	def lipids(self): return [k for k,v in self.objects.items() if v['cat']=='lipid']
	def anions(self): return [k for k,v in self.objects.items() if v['cat']=='ion' and v['charge'] < 0]
	def cations(self): return [k for k,v in self.objects.items() if v['cat']=='ion' and v['charge'] > 0]

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

