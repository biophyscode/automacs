#!/usr/bin/env python

from __future__ import print_function
#! once we added replicator/__init__.py to expose pipeline in 
#!   ortho/__init__.py we had to change e.g. from ortho import read_config
#!   hence internal ortho imports need to have the path to the submodule
from ortho.requires import requires_python,requires_python_check
from ortho.dictionary import MultiDict
from ortho.bash import bash_basic,bash
from ortho.handler import Handler,introspect_function
from ortho.config import read_config
from ortho.data import delveset,catalog

import re,tempfile,os,copy
import datetime as dt
import uuid

class SpotLocal:
	"""Make a local directory."""
	#! needs cleanup option
	def __init__(self,site=None,persist=False):
		"""Make a local folder."""
		abspath = lambda x: os.path.abspath(os.path.expanduser(x))
		if persist and site==None: 
			raise Exception('the persist flag is meaningless without site')
		if not site:
			ts = dt.datetime.now().strftime('%Y%m%d%H%M') 
			code = uuid.uuid4().hex[:2].upper()
			self.path = 'repl_%s.%s'%(ts,code)
			#! alternate location for making one-off sites?
			os.mkdir('./%s'%self.path)
			self.abspath = abspath(site)
		else: 
			self.path = site
			self.abspath = abspath(site)
			if persist and os.path.isdir(self.abspath): 
				print('status found persistent spot: %s'%self.abspath)
			else: os.mkdir(self.abspath)

class Runner:
	"""Execute a file with Bash."""
	def __init__(self,**kwargs):
		self.script = kwargs.pop('script')
		self.cwd = kwargs.pop('cwd')
		self.log = kwargs.pop('log','log')
		self.fn = kwargs.pop('fn')
		self.path_full = self.script_fn = os.path.join(self.cwd,self.fn)
		self.subs = dict(path=self.script_fn,fn=self.fn)
		self.cmd = kwargs.pop('cmd','bash %(fn)s')%self.subs
		if kwargs: raise Exception('unprocessed kwargs: %s'%kwargs)
		self.run()
	def run(self):
		if self.script:
			with open(self.path_full,'w') as fp: fp.write(self.script)
		print('status running command %s'%self.cmd)
		bash_basic(self.cmd,cwd=self.cwd,log=self.log)

class ReplicatorSpecial(Handler):

	def dockerfiles(self,dockerfiles):
		# unorthodox: this function overwrites itself with its key
		#   note that this is a neat way to hook something: we expect the 
		#   ReplicatorSpecial to get a portion of a YAML file and just add
		#   it to the class right here, however the way this is called from
		#   replicator_read_yaml means we can easily process it here
		self.dockerfiles = dockerfiles

	#! UNDER CONSTRUCTION def interface(self,interface):
	#! import ipdb;ipdb.set_trace()

class DockerFileChunk(Handler):

	def substitutes(self,text,subs):
		self.text = text%subs

class DockerFileMaker(Handler):

	def sequence(self,sequence,addendum=None):
		"""Assemble a sequence of dockerfiles."""
		index = MultiDict(base=self.meta['dockerfiles'].dockerfiles,
			underscores=True)
		self.dockerfile = [] 
		for item in sequence:
			item_lookup = index.get(item,None)
			if not item_lookup:
				raise Exception('cannot find dockerfile: %s'%item)
			comment = '# section: %s\n'%item
			self.dockerfile.append(comment+self.refine(item_lookup))
		self.dockerfile = '\n'.join(self.dockerfile)
		if addendum: 
			self.dockerfile += "\n# addendum"
			for i in addendum: 
				self.dockerfile += "\n%s"%i

	def raw(self,raw):
		"""Set a verbatim Dockerfile under the raw key."""
		self.dockerfile = raw

	def refine(self,this):
		"""Refine the Dockerfiles."""
		if isinstance(this,dict): 
			this = DockerFileChunk(**this).text
		else: pass
		return this

### SUPERVISOR

def hook_watch(*args_out,**kwargs):
	strict = kwargs.pop('strict',False)
	if kwargs: raise Exception('unprocessed kwargs: %s'%kwargs)
	def wrapper(function):
		introspect = introspect_function(function)
		def decorator(self,**kwargs):
			# process incoming arguments with at signs
			for arg in args_out:
				# identify arguments that are both in the hook argument list
				#   and also are arguments accepted by the function
				if arg in kwargs and (arg in introspect['args'] or arg in introspect['kwargs']):
					# get the "real" answer to the hook query
					# note that we strip the @-syntax
					value = kwargs[arg]
					result = read_config(hook=value,strict=strict).get(value,value)
					kwargs[arg] = result
			# run the function and return
			finding = function(self,**kwargs)
			return finding
		# we attach the original introspection for the Handler, which needs this
		#   to decide how to route the arguments from the constructor to the method
		decorator._introspected = introspect
		return decorator
	return wrapper

class ReplicatorGuide(Handler):

	"""
	def __init__(self,*args,**kwargs):
		print('status subclassed in the ReplicatorGuide 1')
		super().__init__(*args,**kwargs)
	"""

	def bash(self,call):
		"""Run a bash call."""
		bash(call)

	def simple(self,script,site=None,persist=False):
		"""
		Execute a script.
		"""
		spot = SpotLocal(site=site,persist=persist)
		run = Runner(script=script,fn='script.sh',cwd=spot.path)

	def simple_docker(self,script,dockerfile,tag,site=None,persist=False):
		"""
		Run a script in a docker container.
		"""
		dfm = DockerFileMaker(meta=self.meta,**dockerfile)
		spot = SpotLocal(site=site,persist=persist)
		with open(os.path.join(spot.path,'Dockerfile'),'w') as fp: 
			fp.write(dfm.dockerfile)
		script_build = '\n'.join([
			'docker build -t %s .'%tag,])
		# write the script before building the docker
		with open(os.path.join(spot.path,'script.sh'),'w') as fp: 
			fp.write(script)
		run = Runner(script=script_build,fn='script_build.sh',
			log='log-build',cwd=spot.path,local_bash=False)
		run = Runner(script=None,
			#! note that this name needs to match the COPY command in Docker
			cwd=spot.path,fn='script.sh',log='log-run',
			cmd='docker run %s'%tag)#+' %(path)s')

	@hook_watch('prelim','site','identity',strict=False)
	def docker_compose(self,compose,dockerfile,site,
		command,script=None,persist=True,rebuild=True,cleanup=True,
		prelim=None,identity=None,indirect=False,cname=None,notes=None):
		"""
		Prepare a docker-compose folder and run a command in the docker.
		"""
		# the identity key is hook-able, but right now we do not set a proper
		#   hook and instead have it hard-coded below, where we add the user
		#   key to docker compose services lists when running on linux. note
		#   that the linux check and modification of docker compose file can
		#   later be moved to a real hook if desired
		if indirect: raise Exception('you cannot run this! (indirect: true)')
		is_linux = False
		try: 
			check_linux = bash('uname -a',scroll=False)
			if re.match('^Linux',check_linux['stdout']):
				is_linux = True
		except: pass
		if is_linux:
			user_uid = os.getuid()
			user_gid = os.getgid()
		requires_python_check('yaml')
		import yaml
		if prelim:
			result = read_config(hook=prelim).get(prelim,prelim)
			#! do something with result? right now this is just a do hook
		spot = SpotLocal(site=site,persist=persist)
		# added a switch in case no dockerfile build is happening
		if dockerfile:
			dfm = DockerFileMaker(meta=self.meta,**dockerfile)
			dockerfile_fn = os.path.join(spot.path,'Dockerfile')
			with open(dockerfile_fn,'w') as fp: 
				fp.write(dfm.dockerfile)
		# add the user to all docker-compose.yml services on Linux
		if is_linux:
			for key in compose.get('services',{}):
				compose['services'][key]['user'] = '%d:%d'%(user_uid,user_gid)
		# the cname flag gets container name from the command line
		#   and adds it to all of the compose recipes at start time because
		#   if we add it to the recipe by default it turns off some features
		#! this feature does not work with docker exec for some reason
		if cname:
			for service in compose['services']:
				if 'container_name' in compose['services']:
					raise Exception(('received cname from the command line but '
						'the service "%s" already has a container named %s and we '
						'refuse to override this')%(service,
						compose['services']['container_name']))
				else: compose['services'][service]['container_name'] = cname
		compose_fn = os.path.join(spot.path,'docker-compose.yml')
		with open(compose_fn,'w') as fp:
			fp.write(yaml.dump(compose))
		# script is optional. it only runs if you run a docker command below
		#   which also depends on it via an entrypoint
		if script:
			script_fn = os.path.join(spot.path,'script.sh')
			with open(script_fn,'w') as fp: 
				fp.write(script)
		# added a switch in case no dockerfile build is happening
		if dockerfile and rebuild: 
			cmd = 'docker-compose build'
			print('status from %s running command %s'%(spot.path,cmd))
			bash_basic('docker-compose build',cwd=spot.path)
		# no need to log this since it manipulates a presumably 
		#   persistent set of files
		print('status running command %s'%command)
		#! note that we could use docker_compose just for building if we 
		#!   made the rebuild True when no script or command. this might be
		#!   somewhat more elegant? this could be done with another method
		#!   for clarity
		#! failures during rebuild still deposit you in the previous container
		#!   and since this is mildly useful sometimes, we allow it anyway
		bash_basic(command,cwd=spot.path)
		# clean up
		#! note that this is a design choice
		if cleanup:
			if script: os.remove(script_fn)
			try: os.remove(dockerfile_fn)
			except: pass
			try: os.remove(compose_fn)
			except: pass

	def docker_compose_no_build(self,compose,site,
		command,script=None,persist=True,rebuild=True,cleanup=True,
		prelim=None,identity=None,indirect=False,cname=None,notes=None):
		return self.docker_compose(dockerfile=None,
			compose=compose,site=site,command=command,
			script=script,persist=persist,rebuild=rebuild,cleanup=cleanup,
			prelim=prelim,identity=identity,indirect=indirect,cname=cname,
			notes=notes)

	def via(self,via,overrides=None,mods=None,notes=None,cname=None):
		"""
		Run a replicate with a modification. Extremely useful for DRY.
		"""
		if not overrides: overrides = {}
		# get dependency graph
		vias = dict([(i,j['via']) for i,j in self.meta['complete'].items() 
			if not i.startswith('_') and isinstance(j,dict) and 'via' in j])
		paths = {}
		via_keys = list(vias.keys())
		for key in via_keys:
			paths[key] = [key]
			val = key
			while val in vias:
				key_this = vias[val]
				if key_this in paths[key]:
					raise Exception(('detected circular reference in "via" '
						'methods starting from: %s: %s')%(key,str(paths[key])))
				else: paths[key].append(key_this)
				val = key_this
		# paths that are not part of the via-tree
		paths_non_via = [i for i,j in self.meta['complete'].items()
			if not i.startswith('_') and isinstance(j,dict) and 'via' not in j]
		# get this specific upstream path
		if via in paths:
			# from the origin, get the references
			paths_this = tuple(paths[via])[::-1]
			first = paths_this[0]
		elif via in paths_non_via:
			first = via
			paths_this = []
		else: raise Exception('error in resolving "via" path')
		fname = self._classify(*self.meta['complete'][first].keys())
		if fname=='via': 
			raise Exception('eldest parent of this "via" graph needs a parent: %s'%str(paths_this))
		outgoing = copy.deepcopy(self.meta['complete'][first])
		for stage in paths_this[1:]:
			outgoing.update(**copy.deepcopy(self.meta['complete'][stage].get('overrides',{})))
		# for the simplest case we must apply the overrides
		outgoing.update(**overrides)
		#!!! this needs tested!
		#!  deprecated method with no recursion
		if False:
			if via not in self.meta['complete']: 
				raise Exception('reference to replicate %s is missing'%via)
			fname = self.classify(*self.meta['complete'][via].keys())
			outgoing = copy.deepcopy(self.meta['complete'][via])
			#! recursion on the "via" formula needs to happen here
			outgoing.update(**overrides)
		# the mods keyword can be used to surgically alter the tree of hashes
		if mods:
			for path,value in catalog(mods):
				delveset(outgoing,*path,value=value)
		# via calls docker_compose typically
		#! make sure the following does not cause conflicts
		outgoing['indirect'] = False
		#! pass cname from CLI to the target function
		if cname: outgoing['cname'] = cname
		getattr(self,fname)(**outgoing)

	def singularity_via_vagrant(self,vagrant_site):
		"""
		Run something in Singularity in Vagrant (on macos).
		"""
		spot = SpotLocal(site=vagrant_site,persist=True)
		print(spot.abspath)
		raise Exception('yay')

def get_jupyter_token(container):
	"""Check docker logs for a container."""
	result = bash('docker logs %s'%container,scroll=False)
	matched = re.findall(r':(\d+)/\?token=(.*?)\s',result['stdout'])
	if len(matched)==1: raise Exception('cannot locate the token')
	port,token = int(matched[-1][0]),matched[-1][1]
	print('status notebook is available at http://localhost:%d/?token=%s'%(port,token))
