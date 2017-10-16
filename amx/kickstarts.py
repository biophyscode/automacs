#!/usr/bin/env python

"""
KICKSTART SCRIPTS
"""

#---directory for current locations of popular modules
git_addresses = {
	'github':'https://github.com/',
	'proteins':'biophyscode',
	'homology':'ejjordan',
	'bilayers':'bradleyrp',
	'extras':'bradleyrp',
	'docs':'bradleyrp',
	'martini':'bradleyrp',
	'charmm':'bradleyrp',
	'vmd':'bradleyrp',
	'polymers':'bradleyrp',
	'structures':'bradleyrp',}

kickstarters = {
'all':"""
make set module source="%(github)s%(proteins)s/amx-proteins.git" spot="inputs/proteins"
make set module source="%(github)s%(extras)s/amx-extras.git" spot="inputs/extras"
make set module source="%(github)s%(docs)s/amx-docs.git" spot="inputs/docs"
make set commands inputs/docs/docs.py
make set module source="%(github)s%(vmd)s/amx-vmd.git" spot="inputs/vmd"
make set commands inputs/vmd/quickview.py
make set module source="%(github)s%(bilayers)s/amx-bilayers.git" spot="inputs/bilayers"
make set module source="%(github)s%(martini)s/amx-martini.git" spot="inputs/martini"
make set module source="%(github)s%(charmm)s/amx-charmm.git" spot="inputs/charmm"
make set module source="%(github)s%(structures)s/amx-structures.git" spot="inputs/structure-repo"
"""%git_addresses,
'proteins':"""
make set module source="%(github)s%(proteins)s/amx-proteins.git" spot="amx/proteins"
make set module source="%(github)s%(homology)s/amx-homology" spot="amx/homology"
make set module source="%(github)s%(extras)s/amx-extras.git" spot="inputs/extras"
make set module source="%(github)s%(docs)s/amx-docs.git" spot="inputs/docs"
make set commands inputs/docs/docs.py
make set module source="%(github)s%(vmd)s/amx-vmd.git" spot="inputs/vmd"
"""%git_addresses,
'bradley':"""
make set module source="%(github)s%(proteins)s/amx-proteins.git" spot="inputs/proteins"
make set module source="%(github)s%(extras)s/amx-extras.git" spot="inputs/extras"
make set module source="%(github)s%(docs)s/amx-docs.git" spot="inputs/docs"
make set commands inputs/docs/docs.py
make set module source="%(github)s%(vmd)s/amx-vmd.git" spot="inputs/vmd"
make set commands inputs/vmd/quickview.py
make set module source="%(github)s%(bilayers)s/amx-bilayers.git" spot="inputs/bilayers"
make set module source="%(github)s%(martini)s/amx-martini.git" spot="inputs/martini"
make set module source="%(github)s%(charmm)s/amx-charmm.git" spot="inputs/charmm"
make set module source="%(github)s%(structures)s/amx-structures.git" spot="inputs/structure-repo"
make set module source="%(github)s%(polymers)s/amx-polymers.git" spot="inputs/polymers"
make set module source="%(github)s%(homology)s/amx-homology" spot="inputs/homology"
"""%git_addresses,
}
