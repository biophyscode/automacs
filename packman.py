#!/usr/bin/env python

import os,glob
from .misc import treeview
from .config import read_config,write_config
from .bash import bash
from .handler import Handler

def packs():
	conf = read_config()
	treeview(dict(packages=conf.get('packages',{})))

def github_install(source):
	"""Install something simple from github."""
	#! testing with export FLOCK_VERSION=0.2.3 && \
	#!   make github_install source="https://github.com/discoteq/flock/\
	#!   releases/download/v${FLOCK_VERSION}/flock-${FLOCK_VERSION}.tar.xz"
	conf = read_config()
	site = conf.get('packages_env',{}).get('spot','senv')
	# the site holds src and also has the full environment in it
	site_dn = os.path.expanduser(os.path.abspath(site))
	if not os.path.isdir(site): os.mkdir(site)
	for key in ['src']:
		dn = os.path.join(site_dn,key)
		if not os.path.isdir(dn): os.mkdir(dn)
	src_dn = os.path.join(site_dn,key)
	bash('wget %s'%source,cwd=src_dn)
	# see https://unix.stackexchange.com/questions/229504 
	#   for discussion of how difficult it is to get the directory name
	# introspect on the directory
	dns_before = set([i for i in glob.glob(os.path.join(src_dn,'*')) if os.path.isdir(i)])
	bash('tar xvf %s'%os.path.basename(source),cwd=src_dn)
	#dns = set([i for i in glob.glob(os.path.join(src_dn,'*')) if os.path.isdir(i)])
	dns = set([i for i in glob.glob(os.path.join(src_dn,'*')) if os.path.isdir(i)])-dns_before
	if len(dns)!=1: raise Exception('found non-unique new directories: %s'%dns)
	dn_unpack = dns.pop()
	# decide on a place to install
	# make inside the new directory
	bash('./configure --prefix=%s'%site_dn,cwd=dn_unpack)
	bash('make',cwd=dn_unpack)
	bash('make install',cwd=dn_unpack)
	#! returning site_dn for now
	return site_dn

class PackageInstance(Handler):
	def simple(self,path):
		"""A package with a single argument must point to just the binary."""
		return path

class SimplePackages(Handler):
	def get(self,package,installer):
		# get the ortho configuration
		from . import conf
		packs = conf.get('packages',{})
		# install the package if not available
		if package not in packs: 
			#! from ortho import confirm
			#! NOT WORKING confirm('okay to install %s?'%package)
			return installer()
		# currently returning a single package via Handler
		else: return PackageInstance(**conf['packages'][package]).solve
