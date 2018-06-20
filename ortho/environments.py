#!/usr/bin/env python

from __future__ import print_function
from __future__ import unicode_literals
from .bash import bash
from .config import write_config,read_config
import sys,os,datetime,time

__doc__ = """
ENVIRONMENT MANAGER
Read the `envs` key from the config.json (or use a default) to construct or refresh an environment.
Designed to be used with the default anaconda instructions below. We read `reqs_conda.yaml` to build
the environment but the name and python version are set in the instructions below.

Possible unit test:
rm -rf config.json env logs/* && python=python3 make && \
python=python3 make env conda_py2 && python=python3 make debug
"""

"""
ALTERNATE FACTORY INSTALLATION
Use the following bash script to bootstrap an alternate factory method.
This method pipes a new `envs` variable into the config.json and hence overwrites the previous one.
Note that you can also use the standard bootstrap.py method to include these instructions in a default config.

#!/bin/bash

<<EOF

Instructions for installing anaconda from the factory.
Run `bash instruct_anaconda.sh` to set these.
Note that this file may be redundant with defaults in environments.py.

EOF
read -d '' incoming << EOF

{'conda_py2':{
	'where':'env',
	'style':'anaconda',
	'sources':{
		'installer':'./Miniconda3-latest-Linux-x86_64.sh',
		'vmd':'./vmd-1.9.1.bin.LINUXAMD64.opengl.tar',
		},
	'name':'py2',
	#! complete the entry here. see default_envs below
	},
}

EOF
# use `make set` to overwrite the environment in config.json
incoming=$(echo $incoming | sed -e 's/ //g')
make set envs=\"$incoming\"
"""

# default environments if they are absent from config.json
default_envs = dict([
	('conda_py%d'%v,{
		'where':'env',
		'style':'anaconda',
		'sources':{
			'installer':'./miniconda.sh',
			'reqs':'reqs.yaml',},
		'name':'py%d'%v,
		'update':False,
		'python_version':2,
		'install_commands':[
			"this = dict(sources_installer=self.sources['installer'],where=self.where,"+
				"extra=' -u' if self.update else '')",
			"bash('bash %(sources_installer)s -b -p %(where)s%(extra)s'%this,log='logs/log-anaconda-env')",
			"bash('source %s && conda update -y conda'%os.path.join(self.where,'bin','activate'),"+
				"log='logs/log-conda-update')",
			"bash('source %(where_env)s && conda create "+
				"python=%(version)s -y -n %(name)s'%dict(name=self.name,version=self.python_version,"+
				"where_env=os.path.join(self.where,'bin','activate')),"+
				"log='logs/log-create-%s'%self.name)",
			"bash('source %(where_env)s py2 && conda env update --file %(reqs)s'%"+
				"dict(reqs=self.sources['reqs'],where_env=os.path.join(self.where,'bin','activate')),"+
				"log='logs/log-conda-refresh')",
			"bash('make set activate_env=\"%s %s\"'%(os.path.join(self.where,'bin','activate'),self.name))",],
		'refresh_commands':[
			"bash('source %(where_env)s py2 && conda env update --file %(reqs)s'%"+
				"dict(reqs=self.sources['reqs'],where_env=os.path.join(self.where,'bin','activate')),"+
				"log='logs/log-conda-refresh')",],}
	# provide python 2 and python 3 environment options
	) for v in [2,3]])

class Factory:
	def __init__(self,*args,**kwargs):
		if kwargs: raise Exception('unprocess kwargs %s'%kwargs)
		self.conf = conf # pylint: disable=undefined-variable
		self.envs = self.conf.get('envs',default_envs)
		self.logs_space()
		if not self.envs: raise Exception('no environments yet!')
		if not args:
			if kwargs.get('all',False):
				# no arguments and the all kwargs runs through all environments
				for name,detail in self.envs.items(): self.validate(name,detail)
			else: print('warning','use `make env_list` to see available environments and use '
				'`make environ <name>` to install or refresh one or `make environ all=True` for all')
		else: 
			# only make environments for the arguments
			for arg in args:
				if arg not in self.envs: raise Exception('cannot find env %s'%arg)
				else: self.validate(arg,self.envs[arg])
	def logs_space(self):
		"""Logs are always written to the same place."""
		if not os.path.isdir('logs'): os.mkdir('logs')
	def validate(self,name,detail):
		"""
		Check or create an environment.
		Environment data comes from only one place in the `envs` key of the config.json file however it can 
		be placed there by a bootstrap.py with a default configuration or a BASH script described above.
		The only requirement is that it has the following keys: where, sources, style, and install_commands.
		The install commands are exec'd in place in this function. The default envs are set above.
		"""
		self.install_commands = detail.get('install_commands',[])
		self.sources = detail.get('sources',{})
		# all top level keys are part of self
		self.__dict__.update(**detail)
		if 'sources' not in self.__dict__: self.sources = []
		missing_keys = [i for i in ['install_commands'] if i not in self.__dict__]
		if any(missing_keys): raise Exception('environment definition is missing %s'%missing_keys)
		# check if the environment is installed yet
		is_installed = self.conf.get('installed',{}).get(name,None)
		if not is_installed:
			print('status','running commands to install the environment')
			# check sources to preempt an anaconda error
			for source_name,source_fn in self.sources.items():
				if not os.path.isfile(source_fn):
					raise Exception('cannot find source "%s" requested by env %s: %s'%(
						source_name,name,source_fn))
			# use exec to loop over commands. note that the install_commands can use the where,sources,style,
			# ... etc which are set above by default from the detail. note that the default configuration
			# ... above provides an example for using self-referential syntax
			for cmd in self.install_commands: 
				print('run','`%s`'%cmd)
				exec(cmd)
		# if the environment is already installed we simply run refresh commands
		else:
			# note that the installed instructions override the envs instructions when we do a refresh
			# ... in case you want to change the reqs file later on
			self.__dict__.update(**is_installed)
			#! note that we need a better way to edit a nested dictionary. if you want to update the reqs 
			#! ... file you need to edit a nested config.json,installed,<name>,sources,reqs
			print('status','refreshing preexisting environment %s'%self.name) # pylint: disable=no-member
			for cmd in self.conf['installed'][name].get('refresh_commands',[]):
				print('run','`%s`'%cmd)
				exec(cmd)
		# log that this environment has been installed
		self.conf = read_config()
		if 'installed' not in self.conf: self.conf['installed'] = {}
		ts = datetime.datetime.fromtimestamp(time.time()).strftime('%Y.%m.%d.%H%M')
		detail['timestamp'] = ts
		self.conf['installed'][name] = detail
		write_config(self.conf)

#!? previous set of codes for some kind of avoiding ~/.local method?
"""
#---we use the conda environment handler to avoid using the user site-packages in ~/.local
env_etc = 'env/envs/py2/etc'
env_etc_conda = 'env/envs/py2/etc/conda'
for dn in [env_etc,env_etc_conda]:
	if not os.path.isdir(dn): os.mkdir(dn)
for dn in ['activate.d','deactivate.d']: os.mkdir(os.path.join(env_etc_conda,dn))
with open(os.path.join(env_etc_conda,'activate.d','env_vars.sh'),'w') as fp:
	fp.write('#!/bin/sh\nexport PYTHONNOUSERSITE=True\n')
with open(os.path.join(env_etc_conda,'deactivate.d','env_vars.sh'),'w') as fp:
	fp.write('#!/bin/sh\nunset PYTHONNOUSERSITE\n')
"""

def environ(*args,**kwargs): 
	"""The env command instantiates a Factory."""
	Factory(*args,**kwargs)

def env_list(text=False):
	from .misc import treeview
        conf_this = conf # pylint: disable=undefined-variable
	treeview(conf_this.get('envs',default_envs),style={False:'unicode',True:'pprint'}[text])
	print('note','The following dictionaries are instructions for building environments. '
		'You can build a new environment by running `make env <name>`. See environments.py for more docs.')

extension_styles = {
	'distutils':{'spot'},}

def register_extension(name,style,**kwargs):
	"""Register an extension module that was installed locally."""
	if 'extensions' not in conf: conf['extensions'] = {}
	if extension_styles[style]!=set(kwargs.keys()):
		raise Exception('cannot match style "%s" in available extension styles: %s'%(style,extension_styles))
	conf['extensions'][name] = kwargs
	write_config(conf)

def load_extension(name):
	"""Load an extension module."""
	target = conf.get('extensions',{}).get(name,None)
	if not target: raise Exception('cannot find target "%s" in the config.json extensions'%name)
	matches = [k for k,v in extension_styles.items() if v==set(target.keys())]
	if len(matches)==0: raise Exception('cannot match extension "%s": %s'%(name,target))
	elif len(matches)>1: raise Exception('redundant matches for "%s" %s'%(name,target))
	else: style = matches[0]
	if style=='distutils': sys.path.insert(0,target['spot'])
	else: raise Exception('incomplete extension load')
