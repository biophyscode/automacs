#!/usr/bin/env python

from __future__ import print_function
from __future__ import unicode_literals
import os,sys,subprocess,io,time,re
# queue and threading for reader for bash function with scrolling
import threading
if (sys.version_info > (3, 0)): import queue  # pylint: disable=import-error
else: import Queue as queue
import ortho

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

def bash_newliner(line_decode,log=None):
	"""Handle weird newlines in BASH streams."""
	# note that sometimes we get a "\r\n" or "^M"-style newline
	#   which makes the output appear inconsistent (some lines are prefixed) so we 
	#   replace newlines, but only if we are also reporting the log file on the line next
	#   to the output. this can get cluttered so you can turn off scroll_log if you want
	line = re.sub('\r\n?',r'\n',line_decode)
	if log:
		line_subs = ['[LOG] %s | %s'%(log,l.strip(' ')) 
			for l in line.strip('\n').splitlines() if l] 
	else: line_subs = [l.strip(' ') for l in line.strip('\n').splitlines() if l] 
	if not line_subs: return None # previously continue in a loop
	line_here = ('\n'.join(line_subs)+'\n')
	return line_here

def bash(command,log=None,cwd=None,inpipe=None,scroll=True,tag=None,
	announce=False,local=False,scroll_log=True):
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
			stdout,stderr = proc.communicate(input=inpipe)
		# no log and no input pipe
		else: 
			# scroll option pipes output to the screen
			if scroll:
				empty = '' if sys.version_info<(3,0) else b''
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
	# this method can handle universal newlines while the threading method cannot
	elif log and scroll=='special':
		with io.open(log,'wb') as writes, io.open(log,'rb',1) as reads:
			proc = subprocess.Popen(command,stdout=writes,
				cwd=cwd,shell=True,universal_newlines=True)
			while proc.poll() is None:
				sys.stdout.write(reads.read().decode('utf-8'))
				time.sleep(0.5)
			# read the remaining
			sys.stdout.write(reads.read().decode('utf-8'))
	# log to file and print to screen using the reader function above
	elif log and scroll:
		# via: https://stackoverflow.com/questions/31833897/
		# note that this method also works if you remove output to a file
		#   however I was not able to figure out how to identify which stream 
		#   was which during iter, for obvious reasons
		#! note that this fails with weird newlines i.e. when GROMACS supplies
		#!   a "remaining wall clock time" and this problem cannot be overcome
		#!   by setting universal_newlines with this scroll method. recommend
		#!   that users instead try the special method above, which works fine
		#!   with unusual newlines
		proc = subprocess.Popen(command,cwd=cwd,shell=True,executable='/bin/bash',
			stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=1)
		qu = queue.Queue()
		threading.Thread(target=reader,args=[proc.stdout,qu]).start()
		threading.Thread(target=reader,args=[proc.stderr,qu]).start()
		empty = '' if sys.version_info<(3,0) else b''
		with open(log,'ab') as fp:
			for _ in range(2):
				for _,line in iter(qu.get,None):
					# decode early, encode late
					line_decode = line.decode('utf-8')
					# note that sometimes we get a "\r\n" or "^M"-style newline
					#   which makes the output appear inconsistent (some lines are prefixed) so we 
					#   replace newlines, but only if we are also reporting the log file on the line next
					#   to the output. this can get cluttered so you can turn off scroll_log if you want
					if scroll_log:
						line = re.sub('\r\n?',r'\n',line_decode)
						line_subs = ['[LOG] %s | %s'%(log,l.strip(' ')) 
							for l in line.strip('\n').splitlines() if l] 
						if not line_subs: continue
						line_here = ('\n'.join(line_subs)+'\n')
					else: line_here = re.sub('\r\n?',r'\n',line_decode)
					# encode on the way out to the file, otherwise print
					# note that the encode/decode events in this loop work for ascii and unicode in both
					#   python 2 and 3, however python 2 (where we recommend importing unicode_literals) will
					#   behave weird if you print from a script called through ortho.bash due to locale issues
					#   described here: https://pythonhosted.org/kitchen/unicode-frustrations.html
					#   so just port your unicode-printing python 2 code or use a codecs.getwriter
					print(line_here,end='')
					# do not write the log file in the final line
					fp.write(line.encode('utf-8'))
	# log to file and suppress output
	elif log and not scroll:
		output = open(log,'w')
		kwargs = dict(cwd=cwd,shell=True,executable='/bin/bash',
			stdout=output,stderr=output)
		if inpipe: kwargs['stdin'] = subprocess.PIPE
		proc = subprocess.Popen(command,**kwargs)
		if not inpipe: stdout,stderr = proc.communicate()
		else: stdout,stderr = proc.communicate(input=inpipe.encode('utf-8'))
	else: raise Exception('invalid options')
	if not scroll and stderr: 
		if stdout: print('error','stdout: %s'%stdout.decode('utf-8').strip('\n'))
		if stderr: print('error','stderr: %s'%stderr.decode('utf-8').strip('\n'))
		raise Exception('bash returned error state')
	# we have to wait or the returncode below is None
	# note that putting wait here means that you get a log file with the error 
	#   along a standard traceback to the location of the bash call
	proc.wait()
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
	if not scroll:
		if stderr: stderr = stderr.decode('utf-8')
		if stdout: stdout = stdout.decode('utf-8')
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
	if log:
		# bash can do tee with stdout and stderr with this technique
		# via https://stackoverflow.com/questions/692000
		cmd_tee =  '%(cmd)s > >(tee -a %(log)s) 2> >(tee -a %(log)s >&2)'%dict(
			log=log,cmd=cmd)
		ortho.bash(command=cmd_tee,cwd=cwd)
	else: os.system('cd %s && %s'%(cwd,cmd))
