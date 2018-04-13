#!/usr/bin/env python

"""
IMPORTER
--------

Custom imports and shared namespaces for linking codes.

This module is never run directly. Instead, it is read by the ACME initializer at runner/__init__.py, and 
then injected into any __init__.py file for top-level modules that participate in the ACME importing scheme.
This largely serves two functions: (1) importing all functions from various locations specified by an 
experiment, and (2) exporting shared variables to all functions required by our simulation. The former 
simplifies your import statements, and the latter saves you from sending data between functions willy nilly.
"""

#---acme-inflected modules must use the following __init__.py 
#---...to use this importer.py and the corresponding ACME features

"""
#---import the runner and auto-import this module (if not sphinx)
import os,sys,shutil
if not os.path.basename(sys.argv[0])=='sphinx-build':
	#---find config.py in a parent directory
	root_dns = [os.path.abspath(os.path.join(__file__,*('..' for j in range(i+1)))) for i in range(5)]
	try: root_dn = next(f for f in root_dns if os.path.isfile(os.path.join(f,'config.py')))
	except: raise Exception('cannot find config.py in any (reasonable) parent of %s'%__file__)
	config = {}
	with open(os.path.join(root_dn,'config.py')) as fp: config = eval(fp.read())
	#---connect to runner
	sys.path.insert(0,os.path.abspath(os.path.dirname(config['acme'])))
	acme_mod = __import__(os.path.basename('runner'))
	reqs = 'DotDict,state,settings,expt,call_reporter,acme_submodulator,finished'.split(',')
	globals().update(**dict([(k,acme_mod.__dict__[k]) for k in reqs]))
	exec(acme_submodulator)
"""

_msg_no_global_imports = 'absolutely no "import *" allowed in a module which decorates with '+\
	'call_reporter. remove them from %s (or its submodules) or use'+\
	'"_acme_silence = False" before "exec(acme_submodulator)" in your __init__.py'

from acme import read_config,get_path_to_module

def get_extras(extensions):
	"""
	We allow two kinds of notations for specifying extension modules.
	The easiest method is to specify a file or a glob.
	You can also use e.g. `@name/subdir/*.py` where "name" represents the parent directory for a module
	in the config.py. Recall that the modules list in config.py consists of source-destination pairs where
	the sources is a (probably remote) git repository, and the destination is a local path inside this
	instance of automacs. The dirname of the basename is the parent directory, and must be unique. This means
	you can have a "proteins" packages wherever you want, but only once. Then you can refer to it via 
	"@proteins/somewhere/script.py" to use it as an extension regardless of where it is stored. This allows
	for dynamic storage of different modules depending on user preferences.
	"""
	extras = []
	specials = [i for i in extensions if re.match('^@',i)]
	regulars = [i for i in extensions if not re.match('^@',i)]
	if any(specials):
		for special in specials:
			extra = get_path_to_module(special)
			#---extra can now be a glob or a path
			extra_fns = glob.glob(extra)
			if not extra_fns:
				raise Exception('extension %s returned no files'%extra)
			extras.extend([i for i in extra_fns if os.path.basename(i)!='__init__.py'])
	if any(regulars):
		for ask in regulars:
			#---we only allow __init__.py if it is an explicit path
			#---...however this allows you to import entire modules this way
			if os.path.basename(ask)=='__init__.py':
				extras.append(os.path.abspath(os.path.join(os.getcwd(),expt.cwd_source,ask)))
				continue
			fns = [i for i in glob.glob(os.path.abspath(os.path.join(os.getcwd(),expt.cwd_source,ask)))
				if os.path.basename(i)!='__init__.py']
			if not fns:
				raise Exception('request for extension %s returned no files'%ask)
			extras.extend(fns)
	#---it is extremely important to filter out even blank __init__.py files because they cause that 
	#---...problem where like a billion slashes interspersed with "call_reporter" are written to stdout
	return extras

import glob,re
str_types = [str] if (sys.version_info>(3,0)) else [str,unicode]

#---settings
verbose = True
event_log = {}
verbose_pedantic = False
protected_signals = ['_not_all','_not_reported']
if verbose: from datapack import asciitree

cwd = os.getcwd()
here = os.path.dirname(__file__)
if verbose_pedantic: print('[ACME] automatic imports from %s'%here)
#---save the paths now so we can reset it when we are done
paths = list(sys.path)

#---path includes the current directory
if here not in sys.path: sys.path.insert(0,here)

#---select all valid python scripts in the current folder for imports
sub_scripts = [os.path.basename(i) for i in glob.glob(os.path.join(os.path.dirname(__file__),'*.py'))]
sub_scripts_valid = [i for i in sub_scripts if not os.path.basename(i)=='__init__.py']
core_import_mapping,core_import_mapping_explicit = [],[]
#---import instructions overrides the method above. this allows the user to more carefully specify 
#---...the import targets. this feature was developed to separate GROMACS from LAMMPS
if '_import_instruct' in globals():
	sub_scripts_valid_grouped = _import_instruct.get('special_import_targets',[])
	sub_scripts_valid = []
	#---formulate the list of submodule targets for the import scheme
	for tag,items in sub_scripts_valid_grouped: sub_scripts_valid.extend(items)
	invalid_targets = [i for i in sub_scripts_valid if os.path.basename(i)=='__init__.py' 
		or not os.path.isfile(os.path.join(os.path.dirname(__file__),i))]
	if any(invalid_targets): raise Exception('invalid import targets: %s'%invalid_targets)
	#---ensure all imports are not-by-filename
	for fnum,fn in enumerate(sub_scripts_valid):
		if os.path.sep in fn: 
			if os.path.basename(fn) in sub_scripts_valid: 
				raise Exception('the submodule target %s is already in sub_scripts_valid (%s)'%(fn,sub_scripts_valid))
			sub_scripts_valid[fnum] = os.path.basename(fn)
			dn = os.path.join(os.path.dirname(__file__),os.path.dirname(fn))
			if dn not in sys.path: sys.path.insert(0,dn)
	core_import_mapping_raw = _import_instruct.get('import_rules',[])
	#---reformulate the mapping to route all of the functions
	for import_from,import_to in core_import_mapping_raw:
		for i in dict(sub_scripts_valid_grouped)[import_from]:
			for j in dict(sub_scripts_valid_grouped)[import_to]:
				#---keep track of import movements by basename. note that there is a check for 
				#---...repetition above
				core_import_mapping.append(tuple([os.path.basename(k) for k in [i,j]]))
	#---extract explicit import rules
	core_import_mapping_explicit = _import_instruct.get('import_rules_explicit',[])
	#---report the function mappings
	#---! are we missing the other keys from _import_instruct?
	event_log['core_mapping'] = ['%(name)s from %(source)s to %(target)s'%i 
		for i in core_import_mapping_explicit]

#---get "my" name -- the name of this module
event_log['this'] = my_name = os.path.split(os.path.dirname(__file__))[-1]

#---track accumulating submodules, their functions, and shared extensions
subs,stable,washes = {},{},dict([(k,{'objects':{},'sources':{}}) for k in ['side','back']])
wash_signals = {'side':'_shared_extensions','back':'_extension_override'}

#---relative paths (cwd is always with acme.py) tell us if we are a top-level acme module
is_tops = os.path.basename(os.path.abspath(os.path.join(__file__,'../../')))==os.path.basename(os.getcwd())
#---turn the silencer off if we are a top-level acme module
event_log['_acme_silence'] = _acme_silence = globals().get('_acme_silence',not is_tops)

#---get extensions
extras_in = expt.pop('EXTENSIONS',[])
sub_scripts_valid_extras = get_extras(extras_in)
event_log['shared'] = {}

#---we load everything into a dictionary which is then exported to globals for clarity
amx_exports = {}

#---import all targeted submodules
for sub in sub_scripts_valid + sub_scripts_valid_extras:
	stable_prev = list(stable.keys())
	#---add parent paths for far-off submodules 
	sub_local = sub
	if sub in sub_scripts_valid_extras: 
		if os.path.dirname(sub) not in sys.path: 
			sys.path.insert(0,os.path.dirname(sub))
		sub_local = os.path.basename(sub)
	if verbose_pedantic: print('[ACME] module %s collects %s'%(my_name,sub_local))
	try:
		#---manually import the local and save it in the subs dictionary
		#---we perform a standard locals/globals import here, and then remove _not_all
		subs[sub] = test = __import__(os.path.splitext(sub_local)[0],globals(),locals())
		#---it is O.K. to remove _not_all afterwards as long as it was in the incoming module
		#---...if it weren't in the incoming module then maybe another module put it in globals
		vars_intercepted = test.__dict__.get('_not_all',[])
		for key in vars_intercepted:
			if key in amx_exports and key in test.__dict__: del amx_exports[key]
		#---! if vars_intercepted: event_log['codes'][sub]['_not_all'] = vars_intercepted
	except Exception as e: 
		from makeface import tracebacker
		tracebacker(e)
		sys.exit(1)
		raise Exception('[ERROR] acme import failure: %s'%e)
	#---loop over callables and decorate them with the logging/report function
	these_functions = [i for i in dir(test) if i not in protected_signals]
	_use_call_reporter = not _acme_silence
	if _use_call_reporter:
		#---disallow call_reporter and "import *" because it causes an ugly recursion problem
		with open(test.__file__) as fp: _raw_script = fp.read()
		if re.search('import \*',_raw_script): raise Exception(_msg_no_global_imports%test.__file__)
	for key in these_functions: 
		#---callables listed in "_not_all" are not imported at all
		if key in test.__dict__.get('_not_all',[]): continue
		#---callables listed in "_not_reported" are not reported (hence silent)
		if callable(test.__dict__[key]) and key not in test.__dict__.get('_not_reported',[]): 
			#---only use the reporter if we are a top-level acme module (not a submodule)
			#---...otherwise it will run call_reporter on tons of exported submodules
			#---also avoid the call_reporter on e.g. classes (which have no __code__)
			if _use_call_reporter and hasattr(test.__dict__[key],'__code__'): 
				if verbose_pedantic: print('[ACME] collected (reported) object: %s'%key)
				stable[key] = amx_exports[key] = call_reporter(test.__dict__[key],state)
			else:
				if verbose_pedantic: print('[ACME] collecting object: %s'%key)
				stable[key] = amx_exports[key] = test.__dict__[key]
				#---only pass main modules back to the stable for later
				if sub not in sub_scripts_valid_extras: stable[key] = test.__dict__[key]
		#---import everything else into this global namespace
		elif callable(test.__dict__[key]): 
			if verbose_pedantic: print('[ACME] collecting object: %s'%key)
			stable[key] = amx_exports[key] = test.__dict__[key]
			#---only pass main modules back to the stable for later
			if sub not in sub_scripts_valid_extras: stable[key] = test.__dict__[key]
	#---! should we have an else here to send variables from e.g. amx submodules to the extensions?
	#---every subpackage gets a copy of shared variables
	test.state,test.settings,test.expt = state,settings,expt
	#---send the call_reporter back to the module in case calls to locals in the module should be logged
	test.call_reporter = call_reporter

	#---if this is a core-submodule check rules and then perform import/exports
	if sub in [j[1] for j in core_import_mapping]:
		sources = [i for i,j in core_import_mapping if sub==j]
		if any([i not in subs for i in sources]): 
			raise Exception('import rules in _import_instruct have the wrong sequence')
		for i in sources: test.__dict__.update(**subs[i].__dict__)

	#---if this is an extension, check for backwash/sidewash
	if sub in sub_scripts_valid_extras:
		for wash_type in ['side','back']:
			signal = wash_signals[wash_type]
			#---see if the imported code signals the wash
			if signal in test.__dict__:
				for wash in test.__dict__[signal]:
					if wash in washes[wash_type]['objects']:
						raise Exception('found item %s in %s in module %s'%(wash,sub,my_name)+
							' but it was already added by %s'%washes[wash_type]['sources'][wash])
					#---make sure the signal is accurate
					if wash not in test.__dict__:
						raise Exception('requested %s %s was not found in %s'%(signal,wash,sub))
					washes[wash_type]['objects'][wash] = test.__dict__[wash]
					#---record the source of this wash in case there is a conflict
					washes[wash_type]['sources'][wash] = sub
		#---after back/side-washing, populating the stable, we export the local functions to the extensions
		for key in stable: test.__dict__[key] = stable[key]

	#---! at the end of each loop we report what has been added to amx_exports
	for key in list(set(stable.keys())-set(stable_prev)):
		event_log['shared'][key] = os.path.relpath(sub,cwd)

#---record washes
#---! NO REPORTING ON SIDEWASH YET!
for which in ['back']:
	backwash = washes.get('back',{})
	if backwash:
		for key,val in backwash['sources'].items(): 
			event_log['shared'][str(key)] = str(os.path.relpath(val,cwd))

#---explicit function mappings
for route in core_import_mapping_explicit:
	#---send the subject from source to target
	try: subs[route['target']].__dict__[route['name'] ] = subs[route['source']].__dict__[route['name'] ]
	except: raise Exception('explicit import failed %s'%route)

#---coda for more custom rules
if '_import_instruct' in globals() and 'coda' in _import_instruct: exec(_import_instruct['coda'])

#---send overrides from the extensions back to the main codes
for sub in [i for i in subs if i not in sub_scripts_valid_extras]:
	for key,val in washes['back']['objects'].items(): 
		if verbose_pedantic: print('[ACME] sending override back to main codes: %s'%key)
		subs[sub].__dict__[key] = val
#---send shared extensions "sideways" over to the other extensions
for sub in [i for i in subs if i in sub_scripts_valid_extras]:
	for key,val in washes['side']['objects'].items(): 
		if verbose_pedantic: print('[ACME] sending override over to extensions: %s'%key)
		subs[sub].__dict__[key] = val

###!!! does the above actually work? what does subs do? it looks like nothing happens to it
###!!! ALSO TEST BACKWASH, SIDEWASH

#---iterative reexecution may rely on things that happen in init, so we always run that
#---...as long as makeface.py is the first command in the call and we are doing "run"
#---...since "run" is the only function that you would use when doing iterative reexecution
if ('init' in globals() and hasattr(init,'__call__') and state.get('status',None)=='error' and
	len(sys.argv)>0 and sys.argv[0]=='exec.py'): 
	print('[NOTE] detected an error state so we are executing init again')
	init()

#---report the imports
if verbose:
	import textwrap
	# invert the log to show where everything came from
	exports_log = {}
	for key,val in event_log['shared'].items():
		if val not in exports_log: exports_log[val] = []
		exports_log[val].append(key)
	event_log['shared'] = {}
	for key,val in exports_log.items():
		event_log['shared'][key] = textwrap.wrap(', '.join(sorted(val)),width=50)	
	# more print modifications
	event_log['main'] = textwrap.wrap(', '.join(sorted(sub_scripts_valid)),width=50)
	if sub_scripts_valid_extras:
		event_log['extensions'] = textwrap.wrap(', '.join(sorted([str(os.path.relpath(i,cwd)) 
			for i in sub_scripts_valid_extras])),width=50)
	asciitree(dict(imports=event_log))

#---export the collected automacs module into globals
#---note that users can still import amx in multiple ways i.e. with "from amx import *" in the parent script
#---...and "import amx" in an extension module if they wish to have more control. as long as it's called 
#---..."amx" it will be imported here. note also that the state is spread to amx components by the 
#---..._import_instruct variable which is essential to carefully merging these modules *and* sharing these 
#---...key variables via a highly 
#---...unorthodox but effective reverse-import that happens in this file. this does not prevent other amx 
#---...modules from importing from e.g. the gromacs submodule in the standard way, which complements the 
#---..._import_instruct method to complete the inter-module connections necessary for amx to work. to recap: 
#---...the _import_instruct will merge key modules e.g. gromacs *and* give it the state using the 
#---...acme_submodulator while standard imports are also allowed as long as those funnctions do not require 
#---...the special variables like state
globals().update(**amx_exports)
#---the state contains a pointer to amx. this is an end-run around the "from amx import *" method which 
#---...allows you to get globals e.g. functions from extension modules when you do not have the global 
#---...namespace, as long as you have the state. we register amx with _funcs so it is not saved to JSON later 
if '_funcs' not in state: state._funcs = []
state._funcs.append('amx')
state.amx = amx_exports

#---reset the paths
sys.path = list(paths)
