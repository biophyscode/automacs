#!/usr/bin/env python

"""
Developing a generic API interface here.
"""

from ortho import bash,delve,catalog

gmx_call_templates = """
pdb2gmx -f STRUCTURE -ff FF -water WATER -o GRO.gro -p system.top -i BASE-posre.itp -missing TRUE -ignh TRUE
editconf -f STRUCTURE.gro -o GRO.gro
grompp -f MDP.mdp -c STRUCTURE.gro -p TOP.top -o BASE.tpr -po BASE.mdp
mdrun -s BASE.tpr -cpo BASE.cpt -o BASE.trr -x BASE.xtc -e BASE.edr -g BASE.log -c BASE.gro -v TRUE
genbox -cp STRUCTURE.gro -cs SOLVENT.gro -o GRO.gro
solvate -cp STRUCTURE.gro -cs SOLVENT.gro -o GRO.gro
make_ndx -f STRUCTURE.gro -o NDX.ndx
genion -s BASE.tpr -o GRO.gro -n NDX.ndx -nname ANION -pname CATION
trjconv -f STRUCTURE.gro -n NDX.ndx -center TRUE -s TPR.tpr -o GRO.gro
genconf -f STRUCTURE.gro -nbox NBOX -o GRO.gro
"""

if False:
	class GenericNixInterface:
		"""
		Interface to a BASH program.
		"""
		templates = {'echo':'echo "HELLO WORLD"'}
		def __init__(self,**kwargs):
			backend = kwargs.pop('backend','bash')
			extras = kwargs.pop('extras',{})
			self.templates.update(**extras)
			if backend!='bash': raise Exception('dev')
			if kwargs: raise Exception('unprocessed kwargs: %s'%kwargs)
		def run(self,*args,**kwargs):
			if len(args)>1: raise Exception
			else: name = args[0]
			return self.templates[name]

class TerminalInterface:
	def __init__(self,templates):
		self.templates = templates
		#! check key redundancies here
		if False:
			cat = catalog(self.templates)
			arguments = {}
			for c in cat:
				if 'required' in c:
					listify(c[c.index('required')+1])
			import pdb;pdb.set_trace()
	def generate_caller(self):
		def caller(name,*args,**kwargs):
			"""..."""
			call = []
			print(name)
			if name not in self.templates:
				raise Exception('unknown API call: %s'%name)
			# a single argument must be be found in the top level of templates
			if len(args)==0: 
				if (len(self.templates[name])>1 
					and 'default' in self.templates[name]):
					this = self.templates[name]['default']
				# if no marked default we assume the subdict is the default
				else: this = self.templates[name]
			else: this = delve(self.templates[name],*args)
			# process required keys

			import pdb;pdb.set_trace()

			call_string = ' '.join(call)
			return call_string
		return caller

class Argument:
	FILE = 'FILE'
	DIRECTORY = 'DIRECTORY'
	STRING = 'STRING'
	def __init__(self,key,value):
		"""Match the key against a type and validate its value."""
		pass

#! initial formulation
gmx_command_templates = {
	# see cascade of comments below for an example
	'pdb2gmx':{
		# default requires no extra tokens
		# required arguments
		'required':{
			# string added to terminal call with substututions
			'-f %(structure)s':{
				# unique item in the tuple is the kwarg
				('structure','f',):
					# the value must conform to this type
					Argument.FILE},
			'-ff %(force_field,)':{
				('ff','force_field','f'):
					Argument.DIRECTORY},
			'-water %(water)':{
				('water','w',):
					Argument.STRING},
		}
	}
}

def is_force_field():
	global ti

#! developing an alternate formulation
gmx_command_templates = {
	'pdb2gmx':{
		'call':"%(gmx)s%(suffix)s%(spacer)s%(name)s",
		'arguments':{
			'structure':{'kind':Argument.FILE,'required':True,
				'alias':{'f','structure'},},
			'force_field':{'kind':is_force_field,'required':True,
				'alias':{'ff','force_field'},},
		}
	}
}

gmx_command_templates = """
pdb2gmx:
  
"""

class TerminalInterface:
	def __init__(self,templates,**kwargs):
		self.templates = templates
		self.meta = kwargs.pop('meta',{})
		if kwargs: raise Exception('unprocessed kwargs: %s'%kwargs)
	def generate_caller(self):
		def caller(name,*args,**kwargs):
			call = []
			# a single argument must be be found in the top level of templates
			if len(args)==0: 
				if name not in self.templates:
					raise Exception('unknown API call: %s'%name)
				this = self.templates[name]
			elif (name,)+args not in self.templates:
				raise Exception('cannot find call: %s'%str((name,)+args))
			else: this = self.templates[(name,)+args]
			# process required keys
			import pdb;pdb.set_trace()
			call_string = ' '.join(call)
			return call_string
		return caller

def testing_interface():
	global gmx_interface
	meta = 'share_directory'
	ti = TerminalInterface(
		templates=gmx_command_templates,
		meta=meta)
	gmx_run = ti.generate_caller()
	gmx_run('pdb2gmx')
