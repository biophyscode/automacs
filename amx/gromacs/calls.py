#!/usr/bin/env python

from __future__ import print_function
import os,sys,re,subprocess,shutil,glob
from gromacs_commands import gmx_convert_template_to_call
from amx.utils import status

def gmx(program,**kwargs):
	"""
	Construct a GROMACS command and either run it or queue it in a script.
	"""
	#---pop off protected kwargs
	protected,_protected_kwargs = {},['log','inpipe','nonessential','custom']
	for key in _protected_kwargs: protected[key] = kwargs.pop(key,None)
	#---we always require a log
	if not protected['log']: raise Exception(
		'all calls to gmx require a log keyword (recall that we will prepend "log-" to it)')
	#---check that our program template is in the library
	if program not in state.gmxcalls and not protected['custom']:
		raise Exception('gmxcalls has no template for %s'%program)
	elif protected['custom']: program_spec = protected['custom']
	else: program_spec = state.gmxcalls[program]
	#---construct the command from the template
	call_spec = gmx_convert_template_to_call(kwargs=kwargs,spec=program_spec)
	cmd,recorded = call_spec['call'],call_spec['recorded']
	#---check for automatic overrides
	if 'gmx_call_rules' in state:
		#---check and apply all rules with the same command name
		for rule in [i for i in state.gmx_call_rules if i['command']==program]:
			#---ensure no conflicts. the gmx_call_rules will not override flags to gmx
			if '-'+rule['flag'] in recorded['flags']:
				raise Exception('gmx call rule "%s" conflicts with a flag in the call: "%s"'%(
					str(rule),str(recorded)))
			else: 
				#---update the record
				recorded['flags']['-'+rule['flag']] = rule['value']
				#---append to the command
				cmd += ' -%s %s'%(rule['flag'],str(rule['value']))
	#---use the decorator on select functions inside this (amx) module
	#---decorator is only available at run time because it comes from __init__.py
	try: gmx_run_decorated = call_reporter(gmx_run,state)
	except: gmx_run_decorated = gmx_run
	gmx_run_decorated(cmd,log=protected['log'],
		inpipe=protected['inpipe'],nonessential=protected['nonessential'])
	#---if the run works, we log the completed command 
	if 'history_gmx' not in state: state.history_gmx = []
	state.history_gmx.append(recorded)

gmx_error_strings = [
	'File input/output error:',
	'command not found',
	'Fatal error:',
	'Fatal Error:',
	'Can not open file:',
	'Invalid command line argument:',
	'Error in user input:'
	'Software inconsistency error',
	'Syntax error']

def gmx_run(cmd,log,nonessential=False,inpipe=None):
	"""
	Run a GROMACS command instantly and log the results to a file.
	!!! It would be useful to replace shell=True with proper arguments however commands like
	!!! ... `gmx make_ndx` are not being found without shell. Also note that I explored the possibility
	!!! ... of tailing the log file or piping it through the function or doing something with threading
	!!! ... or async I/O to watch the log during the run but this is really tricky.
	"""
	if log == None: raise Exception('[ERROR] gmx_run needs a log file to route output')
	#---if the log is an absolute path we drop the log there without prepending "log-"
	elif log and not os.path.basename(log)==log:
		if not os.path.isdir(os.path.dirname(log)): 
			raise Exception('cannot find directory for log %s'%log)
		log_fn = log
	#---local logs get "log-" prepended and drop in the here directory
	else: log_fn = state.here+'log-'+log
	#---previously wrote a bash-only log but it makes more sense to have a comprehensive automacs log
	output = open(log_fn,'w')
	os.chmod(log_fn,0o664)
	if inpipe == None:
		proc = subprocess.Popen(cmd,cwd=state.here,shell=True,executable='/bin/bash',
			stdout=output,stderr=output)
		proc.communicate()
	else:
		proc = subprocess.Popen(cmd,cwd=state.here,shell=True,executable='/bin/bash',
			stdout=output,stderr=output,stdin=subprocess.PIPE)
		proc.communicate(input=str(inpipe).encode())
	#---check for errors
	with open(log_fn,'r') as logfile: logfile_text = logfile.read()
	for msg in gmx_error_strings:
		if re.search(msg,logfile_text,flags=re.M)!=None: 
			if nonessential: print('[NOTE] command failed but it is nonessential')
			else: 
				#! error reporting may be duplicated in minimize and worth consolidating
				errors = re.findall('\n-{2,}(.*?(?:%s).*?)-{2,}'%('|'.join(gmx_error_strings)),
					logfile_text,re.M+re.DOTALL)
				for error in errors:
					status('caught error in %s:\n[ERROR] | '%log_fn,tag='error')
					print('\n[ERROR] | '.join(error.split('\n')))
					print('note',
						'the extracted output above may not capture the full error, so check the file')
				raise Exception('%s in %s'%(msg.strip(':'),log_fn))

def gmx_get_machine_config(hostname=None):
	"""
	Probe the local or global configuration to see how to run GROMACS.
	"""
	machine_config = {}
	#---!
	config_fn_global = '~/.automacs.py'
	config_fn_local = './gromacs_config.py'
	if os.path.isfile(config_fn_local): config_fn = config_fn_local
	elif os.path.isfile(os.path.expanduser(config_fn_global)): config_fn = config_fn_global	
	else: raise Exception('cannot find either a local (gromacs_config.py) or a global (~/.automacs.py) '
		'gromacs configuration. make one with `make gromacs_config (local|home)`')
	with open(os.path.expanduser(config_fn)) as fp: exec(fp.read(),machine_config)
	#---most of the machine configuration file are headers that are loaded into the main dictionary
	machine_config = machine_config['machine_configuration']
	this_machine = 'LOCAL'
	if not hostname:
		hostnames = [key for key in machine_config 
			if any([varname in os.environ and (
			re.search(key,os.environ[varname])!=None or re.match(key,os.environ[varname]))
			for varname in ['HOST','HOSTNAME']])]
	else: hostnames = [key for key in machine_config if re.search(key,hostname)]
	#---select a machine configuration according to the hostname
	if len(hostnames)>1: raise Exception('[ERROR] multiple machine hostnames %s'%str(hostnames))
	elif len(hostnames)==1: this_machine = hostnames[0]
	else: this_machine = 'LOCAL'
	print('[STATUS] setting gmxpaths for machine: %s'%this_machine)
	machine_config = machine_config[this_machine]
	#---! previously did some ppn calculations here
	return machine_config

def gmx_get_share():
	"""
	Figure out the share/gromacs/top directory.
	"""
	gmx_dn = subprocess.Popen('which %s'%state.gmxpaths['gmx'],
		shell=True,stdout=subprocess.PIPE,
		stderr=subprocess.PIPE).communicate()[0].strip()
	if sys.version_info>=(3,0): gmx_dn = gmx_dn.decode()
	return os.path.abspath(os.path.join(gmx_dn,'..','..','share','gromacs','top'))

def modules_load(machine_config):
	"""
	Interact with environment modules to load software.
	Currently used by get_gmx_paths but this is worth generalizing in the amx parent module.
	"""
	#---modules in LOCAL configuration must be loaded before checking version
	if 'module_path' in machine_config: module_path = machine_config['module_path']
	else:
		module_parent = os.environ.get('MODULESHOME','/usr/share/Modules/default')
		module_path = os.path.join(module_parent,'init','python.py')
	incoming = {}
	if sys.version_info<(3,0): execfile(module_path,incoming)
	else: exec(open(module_path).read(),incoming)
	#---note that modules that rely on dynamically-linked C-code must use EnvironmentModules
	modlist = machine_config['modules']
	if type(modlist)==str: modlist = modlist.split(',')
	for mod in modlist:
		#---always unload gromacs to ensure correct version
		try: incoming['module']('unload','gromacs')
		#---make sure that you can actually run a module load command
		except:
			raise Exception('try editing your python module file (and module function) to reflect'+
				"the folowing:\n(output, error) = subprocess.Popen(['/usr/bin/modulecmd', "+
				"'python'] +\n\targs, stdout=subprocess.PIPE).communicate()\n"+
				'or simply run using the factory environment')
		print('[STATUS] module load %s'%mod)
		#---running `make cluster <hostname>` on a different machine will cause 
		#---...an "Unable to locate a modulefile" error but this is not a problem. it might still be useful
		#---...to prepare the submission script locally in case automacs is misbehaving on clusters
		incoming['module']('load',mod)
	
def gmx_get_paths(override=False,gmx_series=False,hostname=None):
	"""
	Create a list of paths for GROMACS.
	"""
	gmx4paths = {'grompp':'grompp','mdrun':'mdrun','pdb2gmx':'pdb2gmx','editconf':'editconf',
		'genbox':'genbox','make_ndx':'make_ndx','genion':'genion','genconf':'genconf',
		'trjconv':'trjconv','tpbconv':'tpbconv','vmd':'vmd','gmxcheck':'gmxcheck','gmx':'gmxcheck'}
	gmx5paths = {'grompp':'gmx grompp','mdrun':'gmx mdrun','pdb2gmx':'gmx pdb2gmx',
		'editconf':'gmx editconf','genbox':'gmx solvate','make_ndx':'gmx make_ndx',
		'genion':'gmx genion','trjconv':'gmx trjconv','genconf':'gmx genconf',
		'tpbconv':'gmx convert-tpr','gmxcheck':'gmx check','vmd':'vmd','solvate':'gmx solvate','gmx':'gmx'}
	#---note that we tacked-on "gmx" so you can use it to find the share folder using gmx_get_share
	machine_config = gmx_get_machine_config(hostname=hostname)
	#---check the config for a "modules" keyword in case we need to laod it
	print('[STATUS] loading modules to prepare gromacs paths')
	if 'modules' in machine_config: modules_load(machine_config)
	#---basic check for gromacs version series
	suffix = '' if 'suffix' not in machine_config else machine_config['suffix']
	check_gmx = subprocess.Popen('gmx%s'%suffix,shell=True,executable='/bin/bash',
		stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	if override and 'gmx_series' in machine_config: gmx_series = machine_config['gmx_series']
	elif not gmx_series:
		#---! is this the best way to search?
		if not re.search('(C|c)ommand not found',str(check_gmx[1])): gmx_series = 5
		else:
			output = subprocess.Popen('mdrun%s -g /tmp/md.log'%suffix,shell=True,
				executable='/bin/bash',stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			if sys.version_info<(3,0): check_mdrun = ''.join(output)
			else: check_mdrun = ''.join([i.decode() for i in output])
			if re.search('VERSION 4',check_mdrun): gmx_series = 4
			elif not override: raise Exception('gromacs is absent. make sure it is installed. '+
				'if your system uses the `module` command, try loading it with `module load gromacs` or '+
				'something similar. you can also add `modules` in a list to the machine '+
				'configuration dictionary in your gromacs config file (try `make gromacs_config` '+
				'to see where it is).')
			else: print('[NOTE] preparing gmxpaths with override')

	if gmx_series == 4: gmxpaths = dict(gmx4paths)
	elif gmx_series == 5: gmxpaths = dict(gmx5paths)
	else: raise Exception('gmx_series must be either 4 or 5')

	#---! need more consistent path behavior here
	#---modify gmxpaths according to hardware configuration
	config = machine_config
	if suffix != '': 
		if gmx_series == 5:
			for key,val in gmxpaths.items():
				gmxpaths[key] = re.sub('gmx ','gmx%s '%suffix,val)
		else: gmxpaths = dict([(key,val+suffix) for key,val in gmxpaths.items()])
	if 'nprocs' in machine_config and machine_config['nprocs'] != None: 
		gmxpaths['mdrun'] += ' -nt %d'%machine_config['nprocs']
	#---use mdrun_command for quirky mpi-type mdrun calls on clusters
	if 'mdrun_command' in machine_config: gmxpaths['mdrun'] = machine_config['mdrun_command']
	#---if any utilities are keys in config we override and then perform uppercase substitutions from config
	utility_keys = [key for key in gmxpaths if key in machine_config]
	if any(utility_keys):
		for name in utility_keys:
			gmxpaths[name] = machine_config[name]
			for key,val in machine_config.items(): 
				gmxpaths[name] = re.sub(key.upper(),str(val),gmxpaths[name])
		del name
	#---even if mdrun is customized in config we treat the gpu flag separately
	if 'gpu_flag' in machine_config: gmxpaths['mdrun'] += ' -nb %s'%machine_config['gpu_flag']	
	#---export the gmxpaths to the state
	if 'state' in globals(): state.gmxpaths = gmxpaths
	return gmxpaths
	
