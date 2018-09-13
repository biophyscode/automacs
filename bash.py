#!/usr/bin/env python

from __future__ import print_function
from __future__ import unicode_literals
import os,sys,subprocess,io,time
# queue and threading for reader for bash function with scrolling
import threading
if (sys.version_info > (3, 0)): import queue  # pylint: disable=import-error
else: import Queue as queue

def command_check(command):
	"""Run a command and see if it completes with returncode zero."""
	print('[STATUS] checking command "%s"'%command)
	try:
		with open(os.devnull,'w') as FNULL:
			proc = subprocess.Popen(command,stdout=FNULL,stderr=FNULL,shell=True,executable='/bin/bash')
			proc.communicate()
			return proc.returncode==0
	except Exception as e: 
		print('warning','caught exception on command_check: %s'%e)
		return False

def reader(pipe,queue):
	"""Target for threading for scrolling BASH function below."""
	try:
		with pipe:
			for line in iter(pipe.readline,b''):
				queue.put((pipe, line))
	finally: queue.put(None)

def bash(command,log=None,cwd=None,inpipe=None,scroll=True,tag=None,
	announce=False,local=False):
	"""
	Run a bash command.
	Development note: tee functionality would be useful however you cannot use pipes with subprocess here.
	Vital note: log is relative to the current location and not the cwd.
	"""
	if announce: 
		print('status',
			'ortho.bash%s runs command: %s'%(' (at %s)'%cwd if cwd else '',str(command)))
	merge_stdout_stderr = False
	if local: cwd_local = str(cwd)
	if not cwd or local: cwd = '.'
	if local: 
		if log: log = os.path.relpath(log,cwd_local)
		pwd = os.getcwd()
		os.chdir(cwd_local)
	if log == None: 
		# no present need to separate stdout and stderr so note the pipe below
		merge_stdout_stderr = True
		kwargs = dict(cwd=cwd,shell=True,executable='/bin/bash',
			stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
		if input: kwargs['stdin'] = subprocess.PIPE
		proc = subprocess.Popen(command,**kwargs)
		if inpipe and scroll: raise Exception('cannot use inpipe with scrolling output')
		if inpipe: 
			#! note that some solutions can handle input
			#!   see: https://stackoverflow.com/questions/17411966
			#!   test with make_ndx at some point
			stdout,stderr = proc.communicate(input=str(inpipe).encode())
		# no log and no input pipe
		else: 
			# scroll option pipes output to the screen
			if scroll:
				empty = '' if sys.version_info<3 else b''
				#! universal_newlines?
				for line in iter(proc.stdout.readline,empty):
					sys.stdout.write((tag if tag else '')+line.decode('utf-8'))
					sys.stdout.flush()
				proc.wait()
				if proc.returncode:
					raise Exception('see above for error. bash return code %d'%proc.returncode)
			# no scroll waits for output and then checks it below
			else: stdout,stderr = proc.communicate()
	# alternative scroll method via https://stackoverflow.com/questions/18421757
	# special scroll is useful for some cases where buffered output was necessary
	elif log and scroll=='special':
		with io.open(log,'wb') as writes, io.open(log,'rb',1) as reads:
		    proc = subprocess.Popen(command,stdout=writes,cwd=cwd,shell=True)
		    while proc.poll() is None:
		        sys.stdout.write(reads.read())
		        time.sleep(0.5)
		    # Read the remaining
		    sys.stdout.write(reader.read())
	# log to file and print to screen using the reader function above
	elif log and scroll:
		# via: https://stackoverflow.com/questions/31833897/
		# note that this method also works if you remove output to a file
		#   however I was not able to figure out how to identify which stream was which during iter
		#! needs tested in Python 3
		#! note that this was failing with `make go protein` in automacs inside
		#!   the replicator. it worked with `make prep protein && python -u ./script.py`
		#!   and without the unbuffered output it just dumps it at the end
		proc = subprocess.Popen(command,cwd=cwd,shell=True,executable='/bin/bash',
			stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=1)
		qu = queue.Queue()
		threading.Thread(target=reader,args=[proc.stdout,qu]).start()
		threading.Thread(target=reader,args=[proc.stderr,qu]).start()
		empty = '' if sys.version_info<3 else b''
		with open(log,'ab') as fp:
			for _ in range(2):
				for _,line in iter(qu.get,None):
					#! maybe one-line refresh method in py3: print(u'\r'+'[LOG]','%s: %s'%(log,line),end='')
					#! not sure how this handles flush
					#! change the below to tag and test with skunkworks
					print('[LOG] %s: %s'%(log,line.decode('utf-8')),end=empty)
					fp.write(line)
	# log to file and suppress output
	elif log and not scroll:
		output = open(log,'w')
		kwargs = dict(cwd=cwd,shell=True,executable='/bin/bash',
			stdout=output,stderr=output)
		if inpipe: kwargs['stdin'] = subprocess.PIPE
		proc = subprocess.Popen(command,**kwargs)
		if not inpipe: stdout,stderr = proc.communicate()
		else: stdout,stderr = proc.communicate(input=inpipe)
	else: raise Exception('invalid options')
	if not scroll and stderr: 
		if stdout: print('error','stdout: %s'%stdout.decode('utf-8').strip('\n'))
		if stderr: print('error','stderr: %s'%stderr.decode('utf-8').strip('\n'))
		raise Exception('bash returned error state')
	if proc.returncode: 
		if log: raise Exception('bash error, see %s'%log)
		else: 
			if stdout:
				print('error','stdout:')
				print(stdout.decode('utf-8').strip('\n'))
			if stderr:
				print('error','stderr:')
				print(stderr.decode('utf-8').strip('\n'))
			raise Exception('bash error with returncode %d and stdout/stderr printed above'%proc.returncode)
	if scroll==True: 
		proc.stdout.close()
		if not merge_stdout_stderr: proc.stderr.close()
	if local: os.chdir(pwd)
	return None if scroll else {'stdout':stdout,'stderr':stderr}

class TeeMultiplexer:
	"""
	Send stdout to file via: `stdout_prev = sys.stdout;sys.stdout = tee(stdout_prev,open('log','w'))`
	You must set the tee flag in config.json to write this file.
	"""
	# via: http://shallowsky.com/blog/programming/python-tee.html
	def __init__(self,_fd1,_fd2):
		self.fd1,self.fd2 = _fd1,_fd2
	def __del__(self):
		if self.fd1 != sys.stdout and self.fd1 != sys.stderr : self.fd1.close()
		if self.fd2 != sys.stdout and self.fd2 != sys.stderr : self.fd2.close()
	def write(self,text):
		self.fd1.write(text)
		self.fd2.write(text)
	def flush(self):
		self.fd1.flush()
		self.fd2.flush()

def bash_basic(cmd,cwd,log=None):
	"""
	Simplest wrapper around bash which uses os.system. 
	Note that the bash utility above is fully featured but sometimes produces weird output.
	For example, use in the replicator caught weird characters from ipdb even when it was not used.
	This function uses os.system which creates a subshell and hence uses a consequence-free cd command
	to move to the right spot, and tee to pipe output.
	Note that the log file for this function is local to the cwd, in contrast to the standard bash above.
	"""
	if log: os.system('cd %s && %s | tee %s 2>&1'%(cwd,cmd,log))
	else: os.system('cd %s && %s'%(cwd,cmd))
