#!/usr/bin/env python

#from __future__ import print_function
from ortho.requires import requires_python
from ortho.dictionary import MultiDict
from ortho.bash import bash_basic
from ortho.handler import Handler
import re,tempfile,os,copy
import datetime as dt
import uuid

__all__ = ['repl','test_clean','test_help','docker_clean']

### TOOLS

class SpotLocal:
	"""Make a local directory."""
	#! needs cleanup option
	def __init__(self,site=None,persist=False):
		"""Make a local folder."""
		if persist and site==None: raise Exception('the persist flag is meaningless without site')
		if not site:
			ts = dt.datetime.now().strftime('%Y%m%d%H%M') 
			code = uuid.uuid4().hex[:2].upper()
			self.path = 'repl_%s.%s'%(ts,code)
			os.mkdir('./%s'%self.path)
		else: 
			self.path = site
			if persist and os.path.isdir(self.path): 
				print('status','found persistent spot: %s'%self.path)
			else: os.mkdir(site)

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
		bash_basic(self.cmd,cwd=self.cwd,log=self.log)

class ReplicatorSpecial(Handler):
	taxonomy = {
		'dockerfiles':{'dockerfiles'},}
	def dockerfiles(self,**kwargs):
		self.dockerfiles = kwargs.pop('dockerfiles')
		if kwargs: raise Exception

class DockerFileChunk(Handler):
	taxonomy = {
		'substitutes':{'text','subs'},}
	def substitutes(self,text,subs):
		self.text = text%subs

class DockerFileMaker(Handler):
	taxonomy = {
		'sequence':{'base':{'sequence'},'opts':{'addendum'}},}
	def sequence(self,sequence,addendum=None):
		"""Assemble a sequence of dockerfiles."""
		index = MultiDict(base=self.meta['dockerfiles'].dockerfiles,underscores=True)
		self.dockerfile = '\n'.join([self.refine(index[i]) for i in sequence])
		if addendum: 
			for i in addendum: self.dockerfile += "\n%s"%i
	def refine(self,this):
		"""Refine the Dockerfiles."""
		if isinstance(this,dict): 
			return DockerFileChunk(**this).text
		else: return this

### SUPERVISOR

class ReplicatorGuide(Handler):
	taxonomy = {
		'simple':{'base':{'script'},'opts':{'site','persist'}},
		'simple_docker':{'base':{'script','dockerfile','tag'},'opts':{'site','persist'}},
		'docker_compose':{
			'base':{'script','dockerfile','site','compose','command'},
			'opts':{'persist','rebuild'}},
		'via':{'via','overrides'},}

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

	@requires_python('yaml')
	def docker_compose(self,script,compose,dockerfile,site,
		command,persist=True,rebuild=True):
		"""
		Prepare a docker-compose folder and run a command in the docker.
		"""
		import yaml
		dfm = DockerFileMaker(meta=self.meta,**dockerfile)
		spot = SpotLocal(site=site,persist=persist)
		with open(os.path.join(spot.path,'Dockerfile'),'w') as fp: 
			fp.write(dfm.dockerfile)
		with open(os.path.join(spot.path,'docker-compose.yml'),'w') as fp:
			fp.write(yaml.dump(compose))
		with open(os.path.join(spot.path,'script.sh'),'w') as fp: 
			fp.write(script)
		if rebuild: bash_basic('docker-compose build',cwd=spot.path)
		# no need to log this since it manipulates a presumably persistent set of files
		bash_basic(command,cwd=spot.path)

	def via(self,via,overrides):
		"""
		Run a replicate with a modification. Extremely useful for DRY.
		"""
		if via not in self.meta['complete']: 
			raise Exception('reference to replicate %s is missing'%via)
		fname = self.classify(*self.meta['complete'][via].keys())
		outgoing = copy.deepcopy(self.meta['complete'][via])
		outgoing.update(**overrides)
		getattr(self,fname)(**outgoing)

### READERS

@requires_python('yaml')
def replicator_read_yaml(source,name=None):
	"""
	Read a replicator instruction and send it to the Guide for execution.
	"""
	import yaml
	with open(source) as fp: 
		# we load into a MultiDict to forbid spaces (replaced with underscores) in top-level dictionary.
		instruct = MultiDict(base=yaml.load(fp.read()),underscores=True,strict=True)
	# special handling
	reference = {}
	for key in ReplicatorSpecial.taxonomy:
		if key in instruct: 
			reference[key] = ReplicatorSpecial(name=key,**{key:instruct.pop(key)})
	# leftovers from special handling must be tests
	if not name and len(instruct)>1: 
		raise Exception(
			('found multiple keys in source %s. you must choose '
				'one with the name argument: %s')%(source,instruct.keys()))
	elif not name and len(instruct)==1: 
		test_name = instruct.keys()[0]
		print('status','found one instruction in source %s: %s'%(source,test_name))
	elif name:test_name = name
	else: raise Exception('source %s is empty'%source)
	if test_name not in instruct: 
		raise Exception('cannot find replicate %s'%test_name)
	test_detail = instruct[test_name]
	reference['complete'] = instruct
	return dict(name=test_name,detail=test_detail,meta=reference)

### INTERFACE

def test_clean():
	os.system(' rm -rf repl_*')

def repl(**kwargs):
	"""
	Run a test.
	Disambiguates incoming test format and sends it to the right reader.
	Requires explicit kwargs from the command line.
	"""
	# read the request according to format
	if (set(kwargs.keys())<={'source','name'} 
		and re.match(r'^(.*)\.(yaml|yml)$',kwargs['source'])):
		this_test = replicator_read_yaml(**kwargs)
	else: raise Exception('unclear request')
	# run the replicator
	rg = ReplicatorGuide(name=this_test['name'],
		meta=this_test['meta'],**this_test['detail'])

def test_help():
	#!!! retire this eventually
	print('make tester source=deploy_v1.yaml name=simple_test')
	print('make tester source=deploy_v1.yaml name=simple_docker')
	print('rm -rf test-no1 && make tester source=deploy_v1.yaml name=no1')

def docker_clean():
	os.system('docker rm $(docker ps -a -q)')
	os.system('docker rmi $(docker images -f "dangling=true" -q)')
