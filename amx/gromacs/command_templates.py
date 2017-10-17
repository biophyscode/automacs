#!/usr/bin/env python

#---command formulations
#---note gromacs has a tricky syntax for booleans so 
#---...we use TRUE and FALSE which map to -flag and -noflag
#---! more explicit documentation for this format
gmx_call_templates = """
pdb2gmx -f STRUCTURE -ff FF -water WATER -o GRO.gro -p system.top -i BASE-posre.itp -missing TRUE -ignh TRUE
editconf -f STRUCTURE.gro -o GRO.gro
grompp -f MDP.mdp -c STRUCTURE.gro -p TOP.top -o BASE.tpr -po BASE.mdp
mdrun -s BASE.tpr -cpo BASE.cpt -o BASE.trr -x BASE.xtc -e BASE.edr -g BASE.log -c BASE.gro -v TRUE
genbox -cp STRUCTURE.gro -cs SOLVENT.gro -o GRO.gro
solvate -cp STRUCTURE.gro -cs SOLVENT.gro -o GRO.gro
make_ndx -f STRUCTURE.gro -o NDX.ndx
genion -s BASE.tpr -o GRO.gro -n NDX.ndx -nname ANION -pname CATION
trjconv -f STRUCTURE.gro -n NDX.ndx -center TRUE -s TPR.tpr -o GRO.gro
genconf -f STRUCTURE.gro -nbox NBOX -o GRO.gro
"""
