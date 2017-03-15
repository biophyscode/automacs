#!/bin/bash
"exec" "python" "-B" "$0" "$@"

__doc__ = """

MAKEFACE (a.k.a. MAKEfile interFACE)
------------------------------------

A crude but convenient way to make a command-line interface for python. This makeface.py connects the makefile 
to arbitrary python functions found in files specified by the ``commands`` key in ``config.py`` which is 
managed by the :any:`acme <acme>` module.

Note: you avoid using ``make`` keywords as python argument names (e.g. "w" and "s") and avoid using ``*args`` 
and ``**kwargs`` because arguments are passed from the ``Makefile`` to the python functions by using the 
`inspect <https://docs.python.org/2/library/inspect.html>`_ module for introspection. You can access python 
functions from the terminal by running ``make my_python_function some_true_bool_flag kwarg="some value"``. 
Set ``commands`` in the ``config.py`` managed by :any:`acme <acme>` to specify which files provide functions 
to the interface. You can set ``__all__`` in these files to hide extraneous functions from ``make``. 
"""

#---settings for globbing for functions
config_fn = 'config.py'
config_key = 'commands'
makeface_funcs = {}

#---invalid flags from Makefile
drop_flags = ['w','--','s','ws','sw']

verbose = False

import os,sys,re,glob
import inspect,traceback

#---utility functions

def str_or_list(x): 
	"""Turn a string or a list into a list."""
	if type(x)==str: return [x]
	elif type(x)==list: return x
	else: raise Exception('str_or_list expects a string or a list')

def strip_builtins(obj):
	"""Remove builtins from a hash in place."""
	#---! whoa this is weird! we wish to collect functions without preventing them from printing...
	if '__all__' in obj.keys(): keys = obj['__all__']
	else: keys = [key for key in obj.keys() if not key.startswith('__')]
	#---! 
	hidden = obj.pop('_not_all',[])
	for h in hidden:
		if h not in keys: raise Exception('_not_all asks to hide %s but it is absent'%h)
		keys.remove(h)
	if '_not_all' in keys: keys.remove('_not_all')
	#---if you pop __builtins__ here then the imported functions cannot do essentials e.g. print
	#---...so instead we pass along a copy
	return dict([(key,obj[key]) for key in keys])

def abspath(path):
	"""Get the right path."""
	return os.path.abspath(os.path.expanduser(path))

def import_local(fn):
	"""Import a local script manually."""
	if os.path.join(os.getcwd(),os.path.dirname(abspath(fn))) in sys.path: 
		mod = __import__(re.sub(r'\.py$','',os.path.basename(fn)))
		return strip_builtins(mod.__dict__)
	else: raise Exception('could not import locally')

def import_remote(script,is_script=False):
	"""Import a script as a module, directly, iff it is not in the path."""
	dn,fn = os.path.dirname(script),os.path.basename(script)
	assert is_script or os.path.isdir(dn),'cannot find directory "%s" for script %s'%(dn,script)
	#assert os.path.isfile(script),'cannot find file "%s"'%fn
	dn_abs = os.path.join(os.getcwd(),dn)
	assert dn_abs not in sys.path,'found "%s" in sys.path already'%dn_abs
	paths = list(sys.path)
	#---prevent modification of paths while we import
	#---! after moving makeface to the runner directory, we loose the '' at the beginning of sys.path
	#---! ...note that running ipdb's set_trace adds it, so the imports work during debugging, but not runtime
	sys.path.insert(0,dn_abs)
	sys.path.insert(0,'')
	if verbose: print('[NOTE] remotely importing %s'%script)
	try: mod = __import__(os.path.splitext(fn)[0])
	#---on import failure we collect functions from the script manually
	except Exception as e:
		tracebacker(e)
		print('[ERROR] remote importing of script %s returned an error: %s'%(script,str(e))) 
		sys.exit(1)
		#---! unlock the following to do manual imports if you think you need them
		mod = {}
		print('[MAKEFACE] about to load a script for ... ')
		exec(open(script).read(),mod)
		print('[WARNING] one of your libraries ("%s") was loaded manually'%script)
	sys.path = paths
	return strip_builtins(mod.__dict__)

def fab_deprecated(text,*flags):
	"""On the chopping block."""
	colors = dict(fail='\033[91m',warning='\033[93m',header='\033[95m',okblue='\033[95m',
		okgreen='\033[92m',endc='\033[0m',bold='\033[1m',underline='\033[4m')
	if flags and sys.stdout.isatty()==True: 
		text = ''.join(colors[f] for f in flags)+text+colors['endc']
	return text

def fab(text,*flags):
	"""Colorize the text."""
	#---three-digit codes: first one is style (0 and 2 are regular, 3 is italics, 1 is bold)
	colors = {'gray':(0,37,48),'cyan_black':(1,36,40),'red_black':(1,31,40),'black_gray':(0,37,40),
		'white_black':(1,37,40),'mag_gray':(0,35,47)}
	if flags and sys.stdout.isatty()==True: 
		if any(f for f in flags if f not in colors): raise Exception('cannot find a color in %s'%str(flags))
		for f in flags[::-1]: 
			style,fg,bg = colors[f]
			text = '\x1b[%sm%s\x1b[0m'%(';'.join([str(style),str(fg),str(bg)]),text)
	return text

def tracebacker(e):
	"""
	"""
	#---standard traceback handling
	exc_type,exc_obj,exc_tb = sys.exc_info()
	tag = fab('[TRACEBACK]','gray')
	tracetext = tag+' '+re.sub(r'\n','\n%s'%tag,str(''.join(traceback.format_tb(exc_tb)).strip()))
	print(fab(tracetext))
	print(fab('[ERROR]','red_black')+' '+fab('%s'%e,'cyan_black'))

def makeface(*arglist):
	"""
	Route ``make`` commands into python.
	"""
	#---stray characters
	arglist = tuple(i for i in arglist if i not in drop_flags)
	#---unpack arguments
	if arglist == []: raise Exception('[ERROR] no arguments to controller')
	args,kwargs = [],{}
	arglist = list(arglist)
	funcname = arglist.pop(0)
	#---regex for kwargs. note that the makefile organizes the flags for us
	regex_kwargs = r'^(\w+)\="?([\w:~\-\.\/\s]+)"?$'
	while arglist:
		arg = arglist.pop(0)
		#---note that it is crucial that the following group contains all incoming 
		if re.match(regex_kwargs,arg):
			parname,parval = re.findall(regex_kwargs,arg)[0]
			kwargs[parname] = parval
		else:
			if sys.version_info<(3,3): 
				#---the following will be removed by python 3.6
				argspec = inspect.getargspec(makeface_funcs[funcname])
				argspec_args = argspec.args
			else:
				sig = inspect.signature(makeface_funcs[funcname])
				argspec_args = [name for name,value in sig.parameters.items() 
					if value.default==inspect._empty or type(value.default)==bool]
			#---! note that a function like runner.control.prep which uses an arg=None instead of just an
			#---! ...arg will need to make sure the user hasn't sent the wrong flags through.
			#---! needs protection
			if arg in argspec_args: kwargs[arg] = True
			else: args.append(arg)
	args = tuple(args)
	if arglist != []: raise Exception('unprocessed arguments %s'%str(arglist))

	#---"command" is a protected keyword
	if funcname != 'back' and 'command' in kwargs: kwargs.pop('command')
	print('[MAKEFACE] calling %s with args="%s" and kwargs="%s"'%(funcname,args,kwargs))
	#---if we are debugging then we call without try so that the debugger in sitecustomize.py can
	#---...pick things up after there is an exception (because pm happens after)
	if os.environ.get('PYTHON_DEBUG','no') in ['pdb','ipdb']:
		makeface_funcs[funcname](*args,**kwargs)
	else:
		#---if no (auto)debugging then we simply report exceptions as a makeface error
		try: makeface_funcs[funcname](*args,**kwargs)
		except Exception as e: 
			tracebacker(e)
			sys.exit(1)
		except KeyboardInterrupt:
			print('okay okay ... exiting ...')
			sys.exit(1)

if __name__ == "__main__": 
	try: from logo import logo
	except: logo = ""
	if logo: print(logo)
	#---read configuration to retrieve source scripts
	#---note this happens every time (even on make tab-completion) to collect scripts
	#---...from all open-ended sources. timing: it only requires about 3 ms
	if not os.path.isfile(config_fn): raise Exception('cannot locate %s'%config_fn)
	if 'config_fn' in globals() and 'config_key' in globals(): 
		with open(config_fn) as fp: configurator = eval(fp.read())
		source_scripts = str_or_list(configurator.get('commands',[]))
	else: raise Exception('need to specify config_fn and config_key')
	#---filter sys.argv
	argvs = [i for i in sys.argv if i not in drop_flags]
	if source_scripts:
		for sc in source_scripts:
			fns = glob.glob(sc)
			for fn in fns: 
				assert os.path.isfile(fn),'cannot locate "%s" requested from config,commands'
				#---protect against ambiguity between scripts and modules in this importing scheme
				if os.path.isdir(os.path.splitext(fn)[0]) and os.path.isfile(fn):
					print('[ERROR] naming redundancy: "%s" is both a directory and a file'%fn)
					sys.exit(1)
				#---import as a local module
				if (os.path.join(os.getcwd(),os.path.dirname(fn)) in sys.path
					or os.path.dirname(fn)=='.'): 
					new_funcs = import_local(fn)
					makeface_funcs.update(**new_funcs)
					if len(argvs)==1 and verbose: 
						print('[NOTE] imported remotely from %s'%fn)
						print('[NOTE] added functions: %s'%(' '.join(new_funcs)))
				else: 
					new_funcs = import_remote(fn)
					makeface_funcs.update(**new_funcs)
					if len(argvs)==1: 
						if verbose: 
							print('[NOTE] imported remotely from %s'%fn)
							print('[NOTE] added functions: %s'%(' '.join(new_funcs)))

	#---prune non-callables from the list of makeface functions
	for name,obj in list(makeface_funcs.items()):
		if not hasattr(obj,'__call__'): 
			print('[WARNING] removing non-callable %s from makeface'%name)
			del makeface_funcs[name]
	#---command aliases for usability
	commands_aliases = configurator.get('commands_aliases',[])
	if any([len(i)!=2 for i in commands_aliases]): 
		raise Exception('commands_aliases must be a list of tuples that specify (target,alias) functions')
	#----fails on docs.py when looking for preplist
	for j,i in commands_aliases:
		if i not in makeface_funcs:
			raise Exception('cannot find target command-line function "%s" for alias "%s"'%(i,j)) 
		#---note that we remove the original function after making the alias to avoid redundancy
		else: makeface_funcs[j] = makeface_funcs.pop(i)
	#---if no argument, make returns valid targets
	if len(argvs)==1: 
		#---this formatting is read by the makefile to get the valid targets (please don't remove it)
		print('[STATUS] available make targets: %s'%(' '.join(makeface_funcs.keys())))
		from datapack import asciitree
		asciitree({'make targets':list(sorted(makeface_funcs.keys()))})
		print('[USAGE] `make <target> <args> <kwarg>="<val>" ...`')
	else: makeface(*argvs[1:])
