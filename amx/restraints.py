#!/usr/bin/env python

import re,os,glob,json,shutil,copy
from force_field_tools import Landscape
from topology_tools import GMXTopology

def transform_itp_martini_copy(itp_fn,specs):
	"""
	Modify an ITP file.
	Moved from the MARTINI bundle.
	This function is a double loop that matches different molecule types with restraints you might request.
	"""
	#---restraints options listing
	specs_add_restraints = 'which naming restraints'.split()
	#---each restraints option listing has a different method for changing restraints
	if set(specs.keys())==set(specs_add_restraints):
		itp = GMXTopology(itp_fn)
		for mol in list(itp.molecules.keys()):
			mol_spec = itp.molecules[mol]

			#---note that the "which":"lipids" checks the tags for each ITP in the meta.json to see if there are
			#---...any lipids in that ITP (but it might be the combined one, so there are other things)
			#---...this is why we perform a secondary check here

			"""
			Modifications to generalize this.
			First we identify lipids by force field class and then apply restraints by class too or something?
			"""
			if state.ff_class == 'martini':
				raise Exception('yo you need the old-school martini version. or fix this one hint hint?')

			#---see if the object is a lipid
			#---! previously we had to run an extra check for GL1 in the martini version because it has 
			#---! ...different molecule types in one itp file
			import ipdb;ipdb.set_trace()
			if is_lipid:
				#---we already have tail names, so we get the last one
				tail_names = [sorted([mol_spec['atoms'][j]['atom'] 
					for j in k])[-1] for k in [atoms_tail_1,atoms_tail_2]]
				#---generate blank restraints
				posres_custom = {'funct': '1','fcy':'0','ai':'1','fcx':'0','fcz':'0'}
				#---hard-coding martini naming rules for head and tail atoms
				posres_all = [dict(posres_custom) for i in range(len(mol_spec['atoms']))]
				#---apply tail restraints if necessary
				if 'martini_glycerol' in specs['restraints']:
					atom_name = 'GL1'
					atoms = [i['atom'] for i in mol_spec['atoms']]
					for key,value in specs['restraints']['martini_glycerol'].items():
						if key not in 'xyz': raise Exception('restraints, martini_glycerol keys must be in xyz')
						posres_all[atoms.index(atom_name)]['fc%s'%key] = value
				if 'martini_tails' in specs['restraints']:
					for atom_name in tail_names: 
						atoms = [i['atom'] for i in mol_spec['atoms']]
						for key,value in specs['restraints']['martini_glycerol'].items():
							if key not in 'xyz': raise Exception('restraints, martini_glycerol keys must be in xyz')
							posres_all[atoms.index(atom_name)]['fc%s'%key] = value
				#---in some cases we want to restrain both the alternate group and the original
				#---...so we apply position restraints to the original here, and later copy it to the alternate
				if specs['naming']=='alternate_restrain_both':
					itp.molecules[mol]['position_restraints'] = posres_all	
				if specs['naming']=='same': mol_name = mol
				elif specs['naming'] in ['alternate','alternate_restrain_both']: 
					if len(mol)>4: raise Exception('name %s is too long. cannot make an alternate'%mol)
					mol_name = mol+'R'
					if mol_name in itp.molecules:
						raise Exception(
							'alternate for %s is %s but that is already in the molecules list'%(mol,mol_name))
					#---in the alternate scheme we make two copies of the lipid, 
					#---...and the "R"-suffixed has the restraints
					itp.molecules[mol_name] = deepcopy(itp.molecules[mol])
					#---apply the name in the correct entries
					#---this is important since the molname and resname are different items
					itp.molecules[mol_name]['moleculetype']['molname'] = mol_name
					for a in itp.molecules[mol_name]['atoms']:
						a['resname'] = mol_name
				else: raise Exception('unclear naming scheme')
				#---apply the position restraints we generated above
				itp.molecules[mol_name]['position_restraints'] = posres_all
	else: raise Exception('transform_itp cannot processes specs keys: "%s"'%specs.keys())
	return itp

def transform_itp(itp,specs):
	"""
	Modify an ITP. Used by the restraint_maker.
	This function is a double loop that matches different molecule types with restraints you might request.
	We modify the ITP in-place so that we can do several modifications if necessary.
	"""
	land = Landscape()
	restraints = specs.pop('restraints')
	naming = specs.pop('naming')
	target_type = specs.pop('which')
	if specs: raise Exception('unprocessed specs')
	#---we apply the transformation to the valid molecules
	for mol in list(itp.molecules.keys()):
		mol_spec = itp.molecules[mol]
		atom_names = map(lambda x:x['atom'],mol_spec['atoms'])
		#---BEGIN TRANFORMATION TYPES
		if target_type=='lipids' and mol in land.lipids():
			#---loop over restraint types
			for restraint_type,rspec in restraints.items():
				if restraint_type=='charmm_tails':
					#---to restrain lipid tails in charmm we get the highest numbered C2N and C3N atoms
					atom_names_targets = ['C%d%d'%(j,max([int(re.match('^C%d(\d+)'%j,i).group(1)) 
						for i in atom_names if re.match('^C%d(\d)+$'%j,i)])) for j in [2,3]]
				elif restraint_type=='charmm_glycerol':
					#---the glycerol group in charmm is named C1, C2, C3
					atom_names_targets = ['C1']
				else: raise Exception('unclear restraint type: %s'%restraint_type)
				#---once we select the atom names for this target, we apply the restraints
				kwargs = dict([('fc%s'%k,v) for k,v in rspec.items()])
				itp.restrain_atoms(*atom_names_targets,**dict(mol=mol,**kwargs))
		elif target_type=='sterols' and mol in land.sterols():
			#---loop over restraint types
			for restraint_type,rspec in restraints.items():
				if restraint_type=='sterol_out':
					atom_names_targets = {'CHL1':['C3']}[mol]
				elif restraint_type=='sterol_in':
					atom_names_targets = {'CHL1':['C26']}[mol]
				else: raise Exception('unclear restraint type: %s'%restraint_type)
				#---once we select the atom names for this target, we apply the restraints
				kwargs = dict([('fc%s'%k,v) for k,v in rspec.items()])
				itp.restrain_atoms(*atom_names_targets,**dict(mol=mol,**kwargs))
		else: print('[NOTE] the molecule %s escapes unscathed!'%mol)

def restraint_maker():
	"""
	Change something about a topology.
	Adapted from the MARTINI lipidome codes.
	"""
	#---settings
	base_ff = state.base_force_field
	if not os.path.isdir(base_ff): raise Exception('base force field must be a directory: %s'%base_ff)
	if not os.path.isfile(os.path.join(base_ff,'meta.json')): 
		raise Exception('base force field requires a meta.json file: %s'%base_ff)

	#---get the metadata for the incoming force field
	with open(os.path.join(base_ff,'meta.json')) as fp: meta = json.load(fp)
	if not os.path.isdir(state.deposit_site): os.mkdir(state.deposit_site)

	#---interpret instructions from the settings
	for out_ff,specs_listing in state.wants.items():

		#---we deposit the new force field in the deposit site
		out_ff_dn = os.path.join(state.deposit_site,out_ff)

		#---! minor hack whereby we copy the whole force field and just overwrite parts of it
		#---! ...note that this might be dangerous
		#---! note that this also copies meta.json but we might want to make a note of the mod
		#---! removed protection that stops you from overwriting the automatic force field
		shutil.copytree(base_ff,out_ff_dn)

		#---! previously checked the meta.json to make sure all the itps it points to are available
		#---! ...but we removed this check. NEED A STANDARDIZED meta.json class
		#---the meta.json has keys that list itps, and itps as keys. we take the latter only, and only apply 
		#---...restraints to itp files with the same molecule type e.g. lipids
		#---! note that this is redundant with the Landscape and the meta.json is turning into a mess
		valid_target_itps = []
		for key in meta.keys():
			#---first make sure it is an ITP file and not a special key e.g. "definitions"
			if re.match('^.+\.itp',key):
				#---next make sure that at least one of the restrain specs is a type e.g. lipids
				#---...that is also in the list of tags for this itp file
				#---! this seems clumsy
				if any([i in [i['which'] for i in specs_listing] for i in meta[key]]):
					valid_target_itps.append(key)
		#---apply rules to all itps
		for itp_name in valid_target_itps:
			#---each value in "wants" is a list of restraint items that must be applied so that we can 
			#---...restrain different molecule types e.g. lipids and sterols
			#---first we get the itp and then we pass it around
			itp_fn = os.path.join(base_ff,itp_name)
			print('[NOTE] applying restraints (if any) to %s'%itp_fn)
			itp = GMXTopology(itp_fn)
			if type(specs_listing)!=list: 
				raise Exception('the wants dictionary must have values that are lists of restraint specs')
			#---loop over all desired transformation; modify itp according to rules
			for specs in specs_listing: transform_itp(itp,copy.deepcopy(specs))
			#---if our itp is in a subdir of the ff directory we might have to make it
			out_fn = os.path.join(out_ff_dn,itp_name)
			if (os.path.isdir(os.path.split(os.path.dirname(out_fn))[1]) and 
				not os.path.isdir(os.path.dirname(out_fn))): os.mkdir(os.path.dirname(out_fn))
			#---the naming scheme only modifies the file internally. it is always rewritten
			itp.write(out_fn,overwrite=True)
	print('[WARNING] just made a new topology but make sure that your atoms are correctly modified!')
