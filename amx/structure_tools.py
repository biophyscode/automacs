#!/usr/bin/env python

import sys,os,re
import numpy as np
import scipy
import json

#---! note that within the main module we import the normal way
from common import dotplace

#---SELECTIONS

"""
SELECTION PARSER
currently requires fully explicit parentheses to denote order of operations (i.e., no trinary operations)
words in the sentence must be compatible with GMXStructure.select.
candidate for inclusion in GMXStructure, since structure must be passed to all functions
"""

def operator(x,op,y,structure):
	"""Perform a single logical operation on an atom selection."""
	assert op in ['and','or']
	v = structure.select(x,return_bools=True) if type(x)==str else x
	w = structure.select(y,return_bools=True) if type(y)==str else y
	try:
		if op=='and': combo = np.all((v,w),axis=0)
		elif op=='or': combo = np.any((v,w),axis=0)
	except:
		import ipdb;ipdb.set_trace()
	return combo

def operator_abstract(a,op,b,sentence,structure): 
	"""Recursive function which calls for operations on "a operator b" phrases in parentheses."""
	operands = [None,None]
	for oo,operand in enumerate([a,b]):
		if not operand.isdigit(): operands[oo] = operand
		else: operands[oo] = operator_abstract(*sentence[int(operand)],sentence=sentence,structure=structure)
	return operator(operands[0],op,operands[1],structure)

def parse(text,structure):
	"""Parse a sentence with explicit order of operations defined by parentheses."""
	regex_operator = '\(\s*([\w\s]*?)\s*(or|and)\s*([\w\s]*?)\s*\)'
	sentence = []
	class Tokenize():
		def __init__(self): 
			self.index = -1+len(sentence)
		def __call__(self,match): 
			sentence.append(match.groups())
			self.index += 1
			return "%d"%self.index
	while True:
		if not re.search(regex_operator,text): break 
		else: text = re.sub(regex_operator,Tokenize(),text)
	return operator_abstract(*sentence[-1],sentence=sentence,structure=structure)

#---CLASSES
#-------------------------------------------------------------------------------------------------------------

class GMXStructure:

	meta_keys = ['atom_names','residue_names','residue_indices','points']
	
	def __init__(self,fn=None,center=False,**kwargs):

		"""
		Store the relevant information from a GRO file.
		UNDER EARLY DEVELOPMENT!
		"""

		#---parse an incoming file
		if fn:
			with open(fn,'r') as fp: lines = fp.readlines()
			#---extract the floats
			try: pts = [[float(j) for j in i.strip('\n')[20:].split()] for i in lines[2:-1]]
			#---backup regex in case values run together
			except: 
				runon_regex = \
					'^\s*([-]?[0-9]+\.?[0-9]{0,3})\s*([-]?[0-9]+\.?[0-9]{0,3})\s*([-]?[0-9]+\.?[0-9]{0,3})'
				pts = [[float(j) for j in re.findall(runon_regex,i[20:])[0]] for i in lines[2:-1]]
			#---extract metadata
			atom_names = [i.strip('\n')[10:15].strip(' ') for i in lines[2:-1]]
			residue_names = [i[5:10].strip() for i in lines[2:-1]]
			residue_indices = [int(i[0:5].strip()) for i in lines[2:-1]]
			#---! currently this is only a string
			box_vectors = lines[-1]
		#---require remaining specification from kwargs if no input file
		else:
			reqs = ['pts','atom_names','residue_names','residue_indices','box']
			assert all(i in kwargs for i in reqs),'missing a required parameter in reqs'
			pts,atom_names,residue_names,residue_indices,box_vectors = [kwargs[i] for i in reqs]
			box_vectors = ''.join(['  %.05f'%x for x in box_vectors])+'\n'
		#---format and store
		self.__dict__.update(**{
			'box':box_vectors,
			'points':np.array([i[:3] for i in pts]),
			'atom_names':np.array(atom_names),
			'residue_names':np.array(residue_names),
			'residue_indices':np.array(residue_indices),
			})
		self.fix_residue_numbering()

	def get_landscape(self,fn):
		"""
		"""
		#---identify molecule types from the landscape for the bilayer_sorter
		if os.path.splitext(fn)[1]=='.yaml':
			import yaml
			with open(fn) as fp: land = yaml.load(fp.read())
		elif os.path.splitext(fn)[1]=='.json':
			with open(fn) as fp: land = json.loads(fp.read())
		else: raise Exception('landscape file at %s must be either json or yaml'%fn)
		return land

	def regroup(self):
		"""
		Sort everything in the system so it follows the composition order.
		"""

		"""
		note that this is designed for lipids
			WILL NEED ALTERNATE METHOD FOR PROTEINS BECAUSE OF THE RESIDUE ISSUE INVOLVED
			because the structure is:
				system
					molecule -- not properly identified in the gro
						residue

		pseudocode:
			first identify all of the components of the system using the composition reader
			pull them out of the main list in order

		for dope debugging: !import code; code.interact(local=vars())

		"""

		#---get the name changes ???
		name_changes = self.residue_names[1:]!=self.residue_names[:-1]
		#---get resnames in order of those that appear first
		resnames,rn_inds = np.unique(self.residue_names,return_index=True)
		resnames = resnames[np.argsort(rn_inds)]
		#---! would be better to match the resnames here with the system.top
		#---! ULTRA-ANNOYING ION NAMING CONVENTION. Sticking to resname "ion" because 
		#---! ... I must have done that for a good reason (since I remember it requiring a lot of work)
		if resnames[-1]!='ION': raise Exception('ions have been hacked for martini please fix them')
		indices = [np.where(self.residue_names==r)[0] for r in resnames[:-1]]
		#---! handle ions separately by adding their positions to the end of the list which will be catted
		indices += [np.where(np.all((self.residue_names=='ION',self.atom_names==i),axis=0))[0]
			for i in [state.composition[j][0] for j in range(-2,0)]]
		reindexed = np.concatenate(indices)

		self.residue_names = self.residue_names[reindexed]
		self.atom_names = self.atom_names[reindexed]
		self.residue_indices = self.residue_indices[reindexed]
		self.points = self.points[reindexed]
		#print('UNDER DEVELOPMENT!!!!!!!!!!')
		#import pdb;pdb.set_trace()

	def fix_residue_numbering(self):

		"""
		Ensure coherent residue numbering.
		"""

		#---! optimize this
		changed_resnum = np.concatenate((np.where(self.residue_indices[1:]!=
			self.residue_indices[:-1])[0]+1,[len(self.residue_indices)]))
		self.residue_indices = (np.concatenate([np.ones(i)*ii for ii,i in 
			enumerate(np.concatenate((changed_resnum[:1],
			changed_resnum[1:]-changed_resnum[:-1])))])+1).astype(int)

	def add(self,another,before=False,**kwargs):

		"""
		Add another GRO to this one.
		"""

		if type(before)==bool: 
			first,second = [self,another][::-1*before]
			for key in self.meta_keys:
				self.__dict__[key] = np.concatenate((first.__dict__[key],second.__dict__[key]))
		else:
			assert type(before)==str
			first,second = [self,another]
			#---insert at a particular index corresponding to the first observation of 'before' resname
			index_wedge = np.where(self.residue_names==before)[0][0]
			for key in self.meta_keys:
				self.__dict__[key] = np.concatenate((first.__dict__[key][:index_wedge],
					second.__dict__[key],first.__dict__[key][index_wedge:]))

	def write(self,out_fn):

		"""
		Write a GRO file.
		"""

		grospec = {'residue_indices'}

		self.renumber()
		residue_inds_abs = self.residue_indices
		self.residue_indices = self.residue_indices%100000
		lines = ['NAME HERE']
		lines += ['%d'%len(self.points)]
		#---in python 3 protect against writing the byte notation
		for key in ['residue_names','atom_names']:
			#---! sloppy! only does something if python 3 changed everything to bytes
			try: self.__dict__[key] = np.array([i.decode() for i in self.__dict__[key]])
			except: pass
		for ii,x in enumerate(self.points):
			#---only the second column needs to be left-aligned hence the dictionary
			line = ''.join({1:'{:<5}'}.get(kk,'{:>5}').format(self.__dict__[k][ii])
				for kk,k in enumerate(['residue_indices','residue_names','atom_names'])
				)+'%5d'%((ii+1)%100000)+''.join([dotplace(y) for y in self.points[ii]])
			lines.append(line)
		lines += [self.box]
		with open(out_fn,'w') as fp: fp.write('\n'.join(lines))
		self.residue_indices = residue_inds_abs

	def cog(self,*inds):

		"""
		Given a set of index lists (presumably returned from select), return the centroid of centroids.
		"""

		return np.array([self.points[i].mean(axis=0) for i in inds]).mean(axis=0)

	def select(self,text,return_bools=False):

		"""
		DEVELOPING!!!
		Return atom indices for items that match a particular selection.
		"""

		import yaml
		land = yaml.load(open('inputs/charmm/landscape.yaml').read())

		#---match residue specifications with a range e.g. "resid 56-76"
		regex_all = '^\s*all\s*$'
		regex_protein = '^\s*protein\s*$'
		regex_resid = '^(not)?\s*resid\s+([0-9]+)-([0-9]+)\s*$'
		regex_resname = '^(not)?\s*resname\s+(.*?)\s*$'

		#---advanced processing if parentheses
		if re.search('\(',text):
			target = parse(text,self)
		#---standard syntax matching
		elif re.match(regex_all,text): target = np.arange(len(self.points))
		elif re.match(regex_protein,text): 
			target = np.in1d(self.residue_names,land['alias']['protein'])
		elif re.match(regex_resid,text):
			invert,lower,upper = re.match(regex_resid,text).groups()
			target = np.in1d(self.residue_indices,np.arange(int(lower),int(upper)+1).astype(int))
			if invert: target = ~target
		elif re.match(regex_resname,text):
			invert,resname = re.search(regex_resname,text).groups()
			target = self.residue_names==resname
			if invert: target = ~target
		#---intuitive matching from the landscape if the text fails all other regexes
		else:
			target = np.array([self.residue_names==i for i in 
				[kk for kk,k in land['objects'].items() if k['is']==text 
				and 'resname' in k['parts']]]).any(axis=0)
		if return_bools: return target
		else: return np.where(target)[0]

	def remove(self,inds):

		"""
		Remove atoms corresponding to a selection.
		"""

		keepers = np.ones(len(self.points)).astype(bool)
		keepers[inds] = False
		for key in self.meta_keys:
			self.__dict__[key] = self.__dict__[key][keepers]

	def trim(self,gap=0.3,subject=None,discard=None):

		"""
		Remove nearby waters. Recapitulates much of trim_waters in common.py but is adapted slightly.
		The discard
		"""

		if not subject: not_water_inds = self.select('resname %s'%wordspace.sol)
		else: not_water_inds = self.select(subject)
		if not discard: water_inds = self.select('not resname %s'%wordspace.sol)
		else: water_inds = self.select(discard)
		status('[COMPUTE] KDTree for close waters')
		tree_not_water = scipy.spatial.KDTree(self.points[not_water_inds])
		close_dists,neighbors = tree_not_water.query(self.points[water_inds],distance_upper_bound=gap)
		status('[COMPUTE] done')
		#---get all close points, reindex from water to absolute, perform "same residue as"
		waters_in_zone = np.where(np.in1d(self.residue_indices,np.unique(
			self.residue_indices[water_inds[np.where(close_dists<=gap)]])))[0]
		self.remove(waters_in_zone)

	def detect_composition(self):
		"""
		Infer the topology.
		"""
		if not state.landscape_metadata:
			raise Exception('state/settings needs `landscape.yaml` for metadata')
		resnames,resnames_inds = np.unique(self.residue_names,return_index=True)
		resnames = resnames[np.argsort(resnames_inds)]
		composition = [(r,len(np.unique(
			self.residue_indices[np.where(self.residue_names==r)[0]]))) for r in resnames]
		#---check for cases where residue name is ION and the atom name distinguishes them
		ion_entries = [i for i in zip(self.residue_names,self.atom_names) if i[0]=='ION']
		if ion_entries and len(np.unique(list(zip(*ion_entries))[1]))>1:
			resnames = list([i for i in resnames if i!='ION'])
			#---detect composition by atom name
			ions,ions_inds = np.unique(list(zip(*ion_entries))[1],return_index=True)
			ions = ions[np.argsort(ions_inds)]
			composition = [(r,len(np.unique(
				self.residue_indices[np.where(self.residue_names==r)[0]]))) for r in resnames]
			for ion_name in ions: 
				composition.append((ion_name,np.sum(self.atom_names==ion_name)))
		land = self.get_landscape(state.landscape_metadata)
		#---! should we be manipulating lipids here?
		#state.lipids = [i for i in list(zip(*composition))[0] if i in list(zip(*filter(lambda x: x[1].get('is',False)=='lipid',land['objects'].items())))[0]]

		#---! the following line is highly incorrect -- cannot rely only on the lasdscape for this! !!!!
		#state.lipids = [k for k,v in land['objects'].items() if v.get('is','')=='lipid']
		#---! so for now we disable it for the flat top!!!!!!!! 

		#---remove tuples for JSON
		#---! EXTREMELY ANNOYING DEBUGGING PROBLEM IS THAT JSON CANNOT DO numpy.str_
		#---! ...add a converter in the statesave function !!!
		composition = [[str(i),int(j)] for i,j in composition]
		return composition

	def renumber(self):

		"""
		Renumber residues.
		"""

		resids = np.zeros(len(self.points))
		resids[np.where(self.residue_indices[1:]!=self.residue_indices[:-1])[0]+1] = 1
		self.residue_indices = (np.cumsum(resids)+1).astype(int)

