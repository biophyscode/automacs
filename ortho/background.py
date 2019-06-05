#!/usr/bin/env python

"""
BACKRUN
Run things in the background.
"""

from __future__ import print_function
import os,subprocess,tempfile

def backrun_old(**specs):
	"""
	Run a script in the background with a new group ID and a script which will kill the job and children.
	"""
	#! this is well-validated and useful. screen version developing below might be more elegant
	cwd = specs.get('cwd','./')
	sudo = specs.get('sudo',False)
	if 'log' in specs: log_fn = specs['log']
	elif 'name' in specs: log_fn = 'log-backrun-%s'%specs['name']
	else: raise Exception('need argument: name or log')
	if 'stopper' in specs: stopper_fn = specs['stopper']
	elif 'name' in specs: stopper_fn = 'script-stop-%s'%specs['name']
	else: raise Exception('need argument: name or stopper')
	# sometimes we want the stopper to be executable but othertimes we want to avoid this
	#   since we might name the stopper like a pid file and we don't want users to get confused
	scripted = specs.get('scripted',True)
	instructs = ['cmd','bin','bash']
	if sum([i in specs for i in instructs])!=1: raise Exception('backrun requires one of: %s'%instructs)
	if 'cleanup' in specs and 'bash' not in specs: 
		raise Exception('cleanup only compatible with explicit bash scripts')
	# run a command
	elif 'cmd' in specs:
		cmd_full = "%snohup %s > %s 2>&1 &"%(specs.get('pre',''),specs['cmd'],log_fn)
	# run a script
	elif 'bin' in specs:
		#! should we ensure the script is executable? security problems?
		cmd_full = "%snohup ./%s > %s 2>&1 &"%(specs.get('pre',''),specs['script'],log_fn)
	# write a script and run it
	elif 'bash' in specs:
		fp = tempfile.NamedTemporaryFile(delete=False)
		fp.write(specs['bash'])
		if 'cleanup' in specs: fp.write('\n'+specs['cleanup'])
		fp.close()
		cmd_full = "%snohup bash %s > %s 2>&1 &"%(specs.get('pre',''),fp.name,log_fn)
	print('[BACKRUN] running from "%s": `%s`'%(cwd,cmd_full))
	if 'bash' in specs: print('[BACKRUN] running the following script:\n'+
		'\n'.join(['[BACKRUN] | %s'%i for i in specs['bash'].splitlines()]))
	job = subprocess.Popen(cmd_full,shell=True,cwd=cwd,preexec_fn=os.setsid,executable='/bin/bash')
	#! weird problems: if job.returncode!=0: raise Exception('backrun failure on `%s`:'%cmd_full)
	#! check for port failure?
	ask = subprocess.Popen('ps xao pid,ppid,pgid',shell=True,
		stdout=subprocess.PIPE,stderr=subprocess.PIPE,executable='/bin/bash')
	stdout,stderr = ask.communicate()
	print('[BACKRUN] pgid=%d kill_switch=%s'%(job.pid,stopper_fn))
	# notes are passed through as comments
	notes = specs.get('notes',None)
	if notes: term_command = '%s\n'%notes
	else: term_command = ''
	term_command += '%spkill -%s -g %d'%('sudo ' if sudo else '',specs.get('killsig','TERM'),job.pid)
	if specs.get('double_kill',False): term_command = term_command+'\n'+term_command
	kill_switch = os.path.join(cwd,stopper_fn)
	kill_switch_coda = specs.get('kill_switch_coda',None)
	with open(kill_switch,'w') as fp: 
		fp.write(term_command+'\n')
		#! the following sudo on cleanup only works for a one-line command
		if kill_switch_coda: fp.write('\n# cleanup\n%s%s\n'%('sudo ' if sudo else '',kill_switch_coda))
	if scripted: os.chmod(kill_switch,0o744)
	job.communicate()

def backrun(cmd,lock,log,cwd='./',executable='/bin/bash',coda=None,block=False,
	killsig='TERM',sudo=False,scripted=True,kill_switch_coda=None,notes=None):
	"""Run something in the background with a lock file."""
	if os.path.isfile(lock): raise Exception('lockfile %s exists'%lock)
	kill_switch = os.path.join(cwd,lock)
	script = tempfile.NamedTemporaryFile(delete=False)
	if not block: cmd_full = "nohup %s > %s 2>&1 &"%(cmd,log)
	# note that blocking really defeats the purpose of "background" running
	#   but makes this code usable in other situations i.e. lockness.sh
	else: cmd_full = "%s > %s 2>&1"%(cmd,log)
	text = 'trap "rm -f %s %s" EXIT'%(
		script.name,kill_switch)+'\n'+cmd_full+(
		'' if not coda else '\n# coda\n'+coda)
	with open(script.name,'w') as fp: fp.write(text)
	print('status script text follows')
	print('\n'.join('[STATUS] | %s'%i for i in text.splitlines()))
	print('status running script %s'%script.name)
	job = subprocess.Popen([executable,script.name],cwd=cwd,
		preexec_fn=os.setsid,executable=executable)
	ask = subprocess.Popen('ps xao pid,ppid,pgid',shell=True, #! shell OK?
		stdout=subprocess.PIPE,stderr=subprocess.PIPE,executable='/bin/bash')
	stdout,stderr = ask.communicate()
	print('status backrun: pgid=%d kill_switch=%s'%(job.pid,lock))
	term_command = '%s%spkill -%s -g %d'%(
		'%s\n'%notes if notes else '',
		'sudo ' if sudo else '',
		killsig,job.pid)
	with open(kill_switch,'w') as fp: 
		fp.write(term_command+'\n')
		#! the following sudo on cleanup only works for a one-line command
		if kill_switch_coda: fp.write('\n# cleanup\n%s%s\n'%(
			'sudo ' if sudo else '',kill_switch_coda))
	if scripted: os.chmod(kill_switch,0o744)
	job.communicate()

def screen_background():
	"""..."""
	#!? exploring an alternate version? why was this abandoned?
	"""
	notes that pgid is 5473
	the screen number is 5474

	ps xao pid,ppid,pgid | egrep "547(3|4)"
	 5474     1  5474
	 5475  5474  5475

	make backrun cmd="bash script.sh" log="log-this" stopper="lockfile"
	make backrun2 cmd="/Users/rpb/worker/factory/env/envs/py2/bin/python /Users/rpb/worker/factory/env/envs/py2/bin/jupyter-notebook --no-browser --port 8021 --port-retries=0 --NotebookApp.iopub_data_rate_limit=10000000000 --notebook-dir=/Users/rpb/worker/factory" log="log-this" lock="lockfile"
	"""
	cmd = '/Users/rpb/worker/factory/env/envs/py2/bin/python /Users/rpb/worker/factory/env/envs/py2/bin/jupyter-notebook --no-browser --port 8021 --port-retries=0 --NotebookApp.iopub_data_rate_limit=10000000000 --notebook-dir=/Users/rpb/worker/factory'
	cmd_screen = "screen -dmS notebook %s"%cmd
	cwd = './'
	job = subprocess.Popen(cmd_screen,
		shell=True,cwd=cwd,preexec_fn=os.setsid,executable='/bin/bash')
	print(job.pid)
	job.communicate()
