#!/usr/bin/python

"""
AUTOMACS CONFIGURATION

locations:
	1. ./config.py for custom hardware/software settings for a single automacs run
	2. ~/.automacs.py for system-wide settings in the absence of a local config.py

cluster headers:
	most clusters require shebang-prefixed commands that tell the system how to run the codes
	these should be stored as strings in this file and referred by `cluster_header` keys in the
	machine_configuration dictionary so that AUTOMACS can generate cluster submission scripts

defaults:
	if no system is specified, AUTOMACS will use the settings in the "LOCAL" subdictionary
	there are no required keys in the machine_configuration sub-dictionaries
	the gpu_flag is passed to GROMACS via "mdrun -nb <gpu_flag>"
	additional entries are used to configure remote machines		
	they will be used if the key is a substring in the hostname
	modules is a string or list of modules to load
	otherwise the GROMACS executables must be in the path
	you may also supply a cluster_header for use on TORQUE clusters
	any keys in the entry will overwrite uppercase keys in the header
	we prefer uppercase regex substitutions by AUTOMACS over bash variables
	see the examples below for XSEDE resources
"""

compbio_cluster_header = """#!/bin/bash
#PBS -l nodes=NNODES:ppn=NPROCS,walltime=WALLTIME:00:00
#PBS -j eo 
#PBS -q opterons
#PBS -N gmxjob
echo "Job started on `hostname` at `date`"
cd $PBS_O_WORKDIR
#---commands follow
"""

gordon_header = """#!/bin/bash
#PBS -q normal
#PBS -l nodes=NNODES:ppn=PPN:native
#PBS -l walltime=WALLTIME:00
#PBS -N gmxjob
#PBS -j eo
#PBS -A upa124
#PBS -m abe
#PBS -V
cd $PBS_O_WORKDIR
. /etc/profile.d/modules.sh
module load gromacs
"""

comet_header = """#!/bin/bash     
#SBATCH --job-name="v651"  
#SBATCH --output="gmxjob.%j.%N.out"  
#SBATCH --partition=compute  
#SBATCH --nodes=NNODES
#SBATCH --ntasks-per-node=PPN 
#SBATCH --export=ALL  
#SBATCH -t WALLTIME:00  

module purge
module load gnutools
module load openmpi_ib
module load gromacs
"""

stampede_header = """#!/bin/bash
#SBATCH -A ALLOCATION
#SBATCH -J gmx.gmxjob
#SBATCH -o gmx.gmxjob.o%j
#SBATCH -e gmx.gmxjob.e%j
#SBATCH -n NPROCS 
#SBATCH -p normal
#SBATCH -t WALLTIME:00 
set -x
module load boost
module load cxx11
module load gromacs
"""

#---AUTOMACS selects a subdictionary below depending on your system
#---note that the keys should be strings that match a substring of your HOSTNAME
machine_configuration = {
	#---the "LOCAL" machine is default, protected
	'LOCAL':dict(
		gpu_flag = 'auto',
		),
	'stampede':dict(
		gmx_series = 5,
		cluster_header = stampede_header,
		ppn = 16,
		walltime = "24:00",
		nnodes = 1,
		suffix = '',
		mdrun_command = '$(echo "ibrun -n NPROCS -o 0 mdrun_mpi")',
		allocation = 'ALLOCATION_CODE_HERE',
		submit_command = 'sbatch',
		),
	'gordon':dict(
		gmx_series = 5,
		cluster_header = gordon_header,
		ppn = 16,
		walltime = "24:00",
		nnodes = 3,
		suffix = '_mpi',
		mdrun_command = \
			'$(echo "mpirun_rsh -np $NPROCS -hostfile '+\
			'$PBS_NODEFILE GMX_ALLOW_CPT_MISMATCH=1 $(which mdrun_mpi)")',
		submit_command = 'qsub',
		),
	'comet':dict(
		gmx_series = 5,
		cluster_header = comet_header,
		ppn = 24,
		walltime = "24:00",
		nnodes = 1,
		suffix = '_mpi',
		mdrun_command = '$(echo "ibrun -n NPROCS -o 0 gmx_mpi mdrun")',
		submit_command = 'sbatch',
		),
	'compbio':dict(
		nnodes = 1,
		nprocs = 16,
		gpu_flag = 'auto',
		modules = 'gromacs/gromacs-4.6.3',
		cluster_header = compbio_cluster_header,
		walltime = 24,
		submit_command = 'qsub',
		),
	}
