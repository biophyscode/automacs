#!/usr/bin/env python

"""
KICKSTART SCRIPTS
"""

kickstarters = {'all':"""
make set module source="$up/amx-proteins.git" spot="amx/proteins"
make set module source="$up/amx-extras.git" spot="inputs/extras"
make set module source="$up/amx-docs.git" spot="inputs/docs"
make set commands inputs/docs/docs.py
make set module source="$up/amx-vmd.git" spot="inputs/vmd"
make set commands inputs/vmd/quickview.py
make set module source="$up/amx-bilayers.git" spot="inputs/bilayers"
make set module source="$up/amx-martini.git" spot="inputs/martini"
make set module source="$up/amx-charmm.git" spot="inputs/charmm"
make set module source="$up/amx-structures.git" spot="inputs/structure-repo"
make set module source="$up/amx-polymers.git" spot="inputs/polymers"
""",
'proteins':"""
make set module source="$up/amx-proteins.git" spot="amx/proteins"
make set module source="$up/amx-extras.git" spot="inputs/extras"
make set module source="$up/amx-docs.git" spot="inputs/docs"
make set commands inputs/docs/docs.py
make set module source="$up/amx-vmd.git" spot="inputs/vmd"
"""
}
