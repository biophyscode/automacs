# 2018.07.18

developing an SOP for exposing functions to the CLI during an import
	use-case
		we have a single cli.py file for a module that uses ortho
		this cli.py file is in commands
		but it also imports functions from elsewhere
	issue when importing the cli.py function
		sometimes we have to use remote_import_script
			what brings us here?
				we need a formal way to perform imports from multiple locations
				without completely scrambling the paths and without ambiguity
		when we do, the ast just parses the script and finds functions
		anything imported is not actually imported when the ast runs
			so we cannot tell if it is a function
		the current hack is to use the importer to call it directly
			remote_import_script
	isolating the actual error
		use-case
			developing automacs with ortho
			commands is amx/runner and amx/cli.py
			the amx/cli.py contains a function that would run outside of amx because it configures it
			that function is in the amx package so I tried "from amx.gromacs.configurator import gromacs_config"
			this causes silent failure in ortho/cli.py collect_functions
			which first tries imports.importer and fails because it throws an exception
			the exception comes from a lack of an expt.json file which the amx package requires
				and perhaps the logic of this is worth revisiting later
				but if we don't throw an exception then we might not catch it until later in the execution loop
		identifying the silent failure for later
			note that silent failure occurs in collect_functions, which gleans functions if it cannot import
			added a strict flag to prevent this
			note that this is different than the strict flag in the imports 
			which just sidesteps the elaborate import scheme and performs pythonic imports
		added an import_check function to run the common
	minimum working example for using glean_functions
		for some reason your code will not import when we check for make targets
			note that this will be useful when we deal with dependencies later
		you can still access the function
		example which shows up as a make target even though it cannot import
			import notthere
			def dummyfunc(): print('hi')
	lesson: use this not that, when amx is not available
		gromacs_config = importer('amx/gromacs/configurator.py')['gromacs_config']
		from amx.gromacs.configurator import gromacs_config
	pending question: what is the use-case for import failures
		attempted to make an import yaml version where we need to activate the env to get yaml
			however it looks like we have yaml when importing
		basically the imports are useful because they prevent you from manipulating paths
		you can do a remote import which is very useful
		you can also import a script in a package without importing the whole package
			which is useful in the case of amx which has a config script that does not need the whole package
			and a main loop that needs certain things to be in place or else
			and this separation allows us to avoid clumsy modes or flags being passed around
		nevertheless it is not clear that the glean_functions is useful for handling the multiple use cases
			where we sometimes have yaml and sometimes do not
		perhaps we need a better test case
			best test case would be yaml for some functions and not for others
			but you can still run things without yaml
		actually this is key. the glean_functions allows some parts of the code to have different dependencies
		so if you have advanced stuff, it can run if the libraries are available
		this is a boon for backwards compatibility and for having a basic python backend for use on clusters
			without tons of work to manage dependencies

# 2018.07.19

coherent tracebacks
	recall DF had a problem with a function I renamed in one place but forgot to extend to other packages
	the traceback was very confusing
	currently debugging "make go proteins" and we print the error directly from the log
		using a fairly permissing regex
	if you read it in sequence the error files are:	
		ortho.cli.run_program
		amx.runner.chooser.experiment
		amx.runner.execution.execute
		ortho.imports.importer
		ortho.imports.import_strict
		importlib.import_module
		script.py has minimize
		amx.reporter.loud
		amx.gromacs.common.miniimize
	this can be confusing for a few reasons

state.get or state.q for fallback?
	note that currently get does not fall back to settings
		tested when adding maxwarn to equilibrate
	note that this prompted redevelopment of dotdict, the child class renamed to multidict etc

dotdict and the state/settings method
	the original automacs used variables called state and settings in a structured which I called "dotdict"
	the dotdict part was a really basic extension to dictionaries that allowed you to access the members like a class object
	this was a fairly trivial extension however it provided a nice syntax: you can just do state.val instead of state['val']
	another extension allowed you to add a backup dictionary or fallback so that if you looked for e.g. state.ionic_strength
		then if it was missing, it would check settings
		this prevented bloat and redundancy and the necessity of checking multiple dictionaries 
		and rectifying differences in case they were used differently
	there were several tricks to accomplish this
		for example self = self.__dict__, subclassing the dict, protecting its keys, etc
	looking up absent keys returned none which is nice for elegant control flow e.g. "if state.do_something:"
	there were problems, namely that the class was not very generic and that get did not work as expected
	redeveloped 
	so I developed a more generic version built on top of dotdict and tested it thoroughly
	development notes follow with a conclusion

# 2018.07.20

ortho gets dotdict and multidict because these are generic functions not specific to automacs
	and fairly useful. they include the following features:
		1. dictionary with access to keys with the dot operator identical to class attributes
		2. a fallback or "upstream" dictionary list for getting values
		3. which upstream dictionaries are noted when we perform a lookup
		4. an option for None to be returned instead of key faiilures
		5. fallback dictionaries are stored by value so they can be other dotdicts
		6. use of get and regular dictionary lookups also work
	these help improve the legibility of the code and allow users to separate the state from settings
		while still running everything through the state

# 2018.07.22

problematic debug mode
	try "from utils import status" in gromacs/calls.py and it is very difficult to debug
	try to debug the usual way with
		python -c "import ortho;ortho.get_targets(verbose=True,strict=True)"
	but this is opaque
		for two reasons: it does not activate the environment so yaml errors
		and the import messages are really an issue
	luckily I knew to just change to "from amx.utils import status" but still this is a possible weakness

added a note to glean functions 
	to explain how it can be useful to have parts of the code that do not require elaborate packages