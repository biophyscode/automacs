#!/usr/bin/env python

"""
GROMACS API
This supplies the gmx command.

The gmx function at the bottom is imported in the following way. The 
bootstrap.py supplies import instructions to config.json when the make command
is first run. These import instructions (in the "frameworks" key at the root of
the config.json) include modules to import. One of those modules is amx/gromacs.
When amx/gromacs is imported by amx/__init__.py (using the magic_importer), it
imports the gmx function from api.py (this file). The magic_importer distributes
this function to the rest of the module somewhat "magically" i.e. by sending
any items in the decorate, subs dictionary to all other modules via sys.modules. 
This unorthodox import strategy means that everything in the module can access
some elements of the global namespace, specifically the state, settings, and 
also the gmx function. This saves a lot of effort in moving those around via 
imports. We prefer not to import gmx, state, settings in the usual way because
these are provided "live" during the execution loop. Ask Ryan if you need more
clarification on this design choice. 


"""

from __future__ import print_function
import ortho
from ortho import read_config,bash,DotDict
from amx.reporter import call_reporter
import yaml
import re,sys

class GMXShellMaster(object):
	"""
	Formulate a call to GROMACS. Used by GMXReverseAPI to make the call.
	"""
	def __init__(self):
		# set the call explicitly with `make set @gmx_call="path/to/executable"`
		#   or use the syntax described in hooks.hook_handler to set
		#   a function to serve as the hook
		# note that we allow GROMACS to be missing since this constructor
		#   runs every time amx is loaded, since it always loads the gromacs
		#   submodule. 
		#! import ipdb;ipdb.set_trace()
		try: 
			conf = ortho.read_config(hooks=True)
			self.gmx = conf['gmx_call']
		except: 
			self.gmx = 'gmx'
			print('warning','gromacs could not be located.')
	def call(self,name,tail):
		"""The master call only sends subcommands to a single command."""
		# +++ a command is a master subcommand and arguments
		return '%s %s %s'%(self.gmx,name,tail)

class GMXReverseAPI(yaml.YAMLObject):
	"""
	Convert a reverse API specification into an interface with GROMACS.
	Recommend mapping this to a function called gmx_run for use in AUTOMACS.
	Weirdness in YAMLObject:
		we use a single master_call instance as an attribute for our 
		reverse API because the YAMLObject ignores init, where we would usually
		add information about which keys we expect in the yaml, or how to get
		the command that a subcommand requires. since we have no init, we use
		a single class instance master_call to get e.g. gmx_mpi and then we
		write the methods for developing the subcommand without reference to
		any of the keys in the subcommand's dictionary in the yaml. it would be
		nice to have a list of expected kwargs to be more precise, but that
		would increase our description length, so we omit it for now and simply
		rely on the functions like e.g. GMXShellCall.formulate to throw
		errors on bogus keys or when keys are missing. in this sense the spec
		is somewhat emergent from the execution of those functions. the 
		advantage is we do not waste lines developing required and optional 
		flags, which is the typical approach for the Handler method
	"""
	yaml_tag = '!gromacs_reverse_api'
	# a single class attribute provides the shell master, which gives you "gmx"
	master_call = GMXShellMaster()
	def gmx(self,name,**kwargs):
		"""
		Get a BASH command for a GROMACS event. This method is exposed to
		globals and distributed throughout the gromacs module.
		"""
		# the name of this functions shows up in the call reporter
		# the magic_importer always provides the state but we check here
		if 'state' not in globals():
			raise Exception('the GROMACS API cannot see the state')
		else: here = state.here
		#! add protection for log and inpipe
		log = kwargs.pop('log',None)
		inpipe = kwargs.pop('inpipe',None)
		if not log: raise Exception('every gromacs call gets a log')
		# +++ all log files are prepended
		log_fn = 'log-%s'%log
		if name not in self.__dict__: 
			raise Exception('cannot find command: %s'%name)
		subcommand = self.__dict__[name]
		# the call is the master call prepended to the formulated subcommand
		cmd = GMXReverseAPI.master_call.call(
			name=name,tail=subcommand.formulate(**kwargs))
		# logs are relative to cwd
		# note that the special scroll method works better with weird newlines
		#   whereas scroll=True and scroll_log=True prints log file names
		kwargs_bash = {'scroll':'special','scroll_log':True}
		if inpipe!=None: kwargs_bash.update(scroll=False,inpipe=inpipe)
		bash(cmd,log=state.here+log_fn,cwd=here,**kwargs_bash)
		return cmd

class GMXShellCall(yaml.YAMLObject):
	yaml_tag = '!bash_gromacs'
	# all shell calls use the same master, a class attribute
	master_call = GMXReverseAPI.master_call
	# note that init is not used by YAMLObject and we found that it is far
	#   more clumsy to make instances of GMXShellCall have their own information
	#   about the master call. much more elegant to have a single GMXShellMaster
	#   object which is an attribute so all GMXShellCall can see it
	def call(self): return GMXShellCall.master_call.call(self.formulate())
	def get_kwargs_to_flag(self):
		"""
		Incoming keyword arguments are mapped to the names (parent) of each 
		argument in order to prevent redundant matching. We construct the 
		mapping for this match here.
		"""
		kwargs_to_flag = {}
		# argument names are the parents of their nodes, under the subcommand
		for argname,detail in self.arguments.items():
			# the argument name (which keys the argument dict in YAML) can 
			#   serve as the kwarg to the gmx function
			if argname in kwargs_to_flag: 
				raise Exception('some flag is also an argument: %s'%argname)
			kwargs_to_flag[argname] = argname
			# we also allow flags to map to the argument name
			#! get the flag, handling tagged objects here
			#!   note that it would be better for tagged objects to mimic dict!
			if isinstance(detail,dict): flag = detail.get('flag',None)
			else: flag = detail.__dict__.get('flag',None)
			if flag:
				if flag in kwargs_to_flag:
					raise Exception(
						'flag %s for argument %s is already mapped'%(
							flag,argname))
				kwargs_to_flag[flag] = argname
		return kwargs_to_flag
	def get_flags(self):
		"""Get the flag for each argument (default is the argument name)."""
		return dict([(i,j.get('flag',i)) for i,j in self.arguments.items()])
	def interpret_value(self,value,argument):
		# validate this object if possible
		if hasattr(argument,'validate'): 
			incoming = argument.validate(name=argument,value=value)
			# any return value is assumed to be a modified value
			if incoming!=None: value = incoming
		if argument.get('bool',False): return bool(value)
		else: return value
	def build_argument(self,flag,value):
		if isinstance(value,bool): 
			return '-%s%s'%('no' if value==False else '',flag)
		else: return '-%s %s'%(flag,value)
	def formulate(self,**kwargs):
		"""Turn kwargs to an arguments list for the subcommand."""
		# intercept base here
		if hasattr(self,'base') and 'base' in kwargs: 
			base = self.base
			# save the base string to this dict for later
			base['base'] = kwargs.pop('base')
		else: base = {}
		# kwargs_to_flag maps incoming keyword arguments to argument name
		kwargs_to_flag = self.get_kwargs_to_flag()
		# flags maps argument name (parent of its node) to flag
		flags = self.get_flags()
		# prevent double-definitions by popping from a list as we add flags
		unused_flags = sorted(set(kwargs_to_flag.values()))
		# required flags are tracked in another list
		requirements = dict([(i,j.get('required',False)) 
			for i,j in self.arguments.items()])
		arguments = []
		for key,val in kwargs.items():
			# get the flag from the flags dictinary keyed by argument name
			flag_this = flags[kwargs_to_flag[key]]
			# +++ arguments are built here
			val = self.interpret_value(value=val,
				argument=self.arguments[kwargs_to_flag[key]])
			sub = self.build_argument(flag_this,val)
			arguments.append(sub)
			requirements.pop(kwargs_to_flag[key])
		possibly_missing = [i for i,j in requirements.items() if j]
		required_missing = []
		# see if missing values have defaults
		for key in possibly_missing:
			if key in self.arguments and 'default' in self.arguments[key]:
				#! repeat argument building here
				flag_this = flags[kwargs_to_flag[key]]
				val = self.arguments[key]['default']
				sub = self.build_argument(flag_this,val)
				arguments.append(sub)
			elif key in base:
				#! repeat argument building here
				flag_this = flags[kwargs_to_flag[key]]
				# +++ base strings are applied to other arguments 
				val = base[key]%base['base']
				sub = self.build_argument(flag_this,val)
				arguments.append(sub)
			else: 
				required_missing.append(key)
		if any(required_missing):
			raise Exception('missing value for %s'%required_missing)
		# +++ the arguments list is a space-sparated list of values
		return ' '.join(arguments)

class CommandTemplateTag(yaml.YAMLObject):
	"""
	Parent class that allows the yaml tags to act as dictionaries, like the 
	other nodes in the dictionary, in the formulate step. This is essential 
	to the use of yaml tags: the nodes look like dictionaries because they
	have the get,__getitem__ methods, but they also have extra methods, namely
	a validate method.
	"""
	def get(self,k,d=None):
		"""Special sauce to ensure backups work."""
		return self.__dict__.get(k,d)
	def __getitem__(self,k): return self.__dict__[k]

class Structure(CommandTemplateTag):
	yaml_tag = '!structure'
	extensions = ['gro','pdb']
	def validate(self,name,value):
		if not re.match(r'^(.*?)\.(%s)'%('|'.join(self.extensions)),value):
			raise Exception(
				'argument %s: %s needs an extension: %s'%(
					name,value,self.extensions))

class ForceField(CommandTemplateTag):
	yaml_tag = '!force_field'
	#! opportunity for special handling

"""
functions need ported:
	gmx_get_share
	gmx_get_machine_config
	gmx_get_paths
"""

### MAIN

# the main API is really a gromacs function from above
# wrap in a function called gmx for traceback and clarity in the log file
gmx_interface = yaml.load(
	open(read_config().get(
	'gromacs_command_templates',
	'amx/gromacs/commands.yaml')).read())

def gmx(name,**kwargs):
	"""
	This function is the primary interface between python and GROMACS.
	"""
	global gmx_interface
	# wrap the main interface function so the call_reporter output is elegant
	try: return gmx_interface.gmx(name,**kwargs)
	except Exception as e:
		from ortho import tracebacker
		# we traceback manually here or else the exception is irrelevant
		tracebacker(e)
		print('[ERROR] failed to prepare gromacs command: "%s" with '
			'kwargs: %s. see exception above. exiting.'%(name,kwargs))
		sys.exit(0)
