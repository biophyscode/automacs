Configuration
=============

Automacs clearly divides experiment parameters from settings required to run the code. The scientific parameters are placed in :ref:`experiment files <customize_experiments>` and are designed to be portable. Software locations, hardware settings, and the precise configuration of your copy of automacs are set in two places: one is specific to GROMACS, and the other configures automacs.

.. _gmx_config:

GROMACS
-------

Automacs needs to find GROMACS exeuctables at the terminal in order to run your simulations. If you install a single copy of GROMACS for all users, than the default configuration will suffice, but either way, automacs will look for a gromacs configuration file in one of two locations.

Running :any:`make prep <control.prep>` for the first time causes automacs to check for the configuration. If it can't find one, it throws an error and asks you to run the configure script. If you run :any:`make gromacs_config home <cli.gromacs_config>`, it will write the example configuration file to a hidden file in your home directory at ``~/.automacs.py``. You can override the global configuration with a local one, written to ``./gromacs_config.py``, by running :any:`make gromacs_config local <cli.gromacs_config>`, or by copying the file to the automacs root directory yourself. We recommend setting up a global configuration for a particular system, and using the local copies to customize particular simulations that might require more or less computing power.

These configuration files consist of a single dictionary called ``machine_configuration`` with keys that should correspond to a portion of the hostname. Any key that uniquely matches the hostname provides the configuration for the simulation (otherwise the ``LOCAL`` key provides the default configuration). The following example includes an entry for a popular supercomputer in Texas called ``stampede``.

.. code-block :: python

  machine_configuration = {
    #---the "LOCAL" machine is default, protected
    'LOCAL':dict(
      gpu_flag = 'auto',
      ),
    'stampede':dict(
      gmx_series = 5,
      #---refer to a string that contains the PBS header flags
      cluster_header = stampede_header,
      ppn = 16,
      walltime = "24:00",
      nnodes = 1,
      #---many systems use the "_mpi" suffix on the executables
      suffix = '',
      #---many systems will only run GROMACS binaries through mpi
      mdrun_command = '$(echo "ibrun -n NPROCS -o 0 mdrun_mpi")',
      allocation = 'ALLOCATION_CODE_HERE',
      submit_command = 'sbatch',
      ),
    }

Users can customize the number of processors per node (``ppn``), the number of nodes (``nnodes``), allocation codes, and even the batch submission command so that these jobs can run properly on many different machines. These parameters are packaged into a ``cluster-continue.sh`` file within each step directory when users run :any:`make cluster <cli.cluster>` on their supercomputing platform. The default configuration provided by :any:`make gromacs_config local <cli.gromacs_config>` provides a few useful examples. Users can submit ``cluster-continue.sh`` directly to the queue to continue the jobs. The ``extend`` and ``until`` parameters in the machine configuration are used to set the number of additional or total picoseconds to run for, otherwise the jobs will consume all of the available walltime and gently stop just before it's up.

Since each cluster typically has its own `PBS header <http://www.adaptivecomputing.com/products/open-source/torque/>`_ format, users can place these in text files (e.g. ``stampede_header`` above). Automacs will automatically replaced any capitalized text in these headers with the value corresponding to keys in the ``machine_configuration`` dictionary. For example, the ``nnodes = 1`` setting causes ``NNODES`` in the ``stampede_header`` to be replaced with the number ``1``. This replacement strategy makes it easy to choose a specific configuration for new jobs, or to set the default configuration on a machine using :any:`make gromacs_config home <cli.gromacs_config>` once without having to bother with it when you create new simulations.

Versions
~~~~~~~~

Many systems have multiple copies of GROMACS which can be loaded or unloaded using `environment modules <http://modules.sourceforge.net/>`_. To load a certain module, you can add them to a string or list in the ``module`` key in the ``machine_configuration``. You can also add ``module`` commands to the cluster header scripts described above.

.. _code_config :

Automacs
--------

Automacs can use a number of different extension modules which can be easily shared with other users by packaging them in `git repositories <https://git-scm.com/>`_. Most users will opt to automatically clone several extensions at once using the :ref:`setup <bootstrap>` procedure described below. Individual extensions can also be directly added to a copy of automacs using a simple command which manipulates the local ``config.py`` file. This file describes all of paths that automacs uses, so that you are free to store your codes wherever you like. Extensions must be added from git repositories using the :any:`make set <acme.set_config>` utility, which writes ``config.py``.

.. code-block :: bash
  
  make set module ~/path/to/extension.git local/path/to/extension
  make set module source="https://github.com/username/extension" spot="inputs/path/to/extension"

The ``spot`` argument is unconstrained; you can store the codes anywhere within the root directory. We prefer to put minor extensions in the ``inputs`` folder, and major extensions directly in the root directory. The ``config.py`` file will change as you add modules and interface functions. A local copy of your config.py is rendered :doc:`here <config>`, as part of the :ref:`live documentation <live_documentation>` of this copy of automacs.

.. _bootstrap:

Setup
~~~~~

At the top of the documentation we recommend that users run the :any:`make setup <cli.setup>` command. Running e.g. ``make setup all`` will pull all of the standard modules from their internet sources (typically `github <https://github.com/biophyscode>`_, however private repositories are also allowed as long as you use ssh aliases).

Cloning the ``proteins`` code repository (part of the ``protein`` and ``all`` collections) will give you access to the ``protein`` experiment listed under :any:`make prep <control.prep>` along with a few other experiments. We recommend using this as an example to get familiar with the automacs framework. Running ``make go protein reset`` after the setup will run a simulation of the `villin headpiece <http://www.rcsb.org/pdb/explore.do?structureId=1yrf>`_. The starting structure is set in the ``pdb_source`` key in the protein experiment file. All of the experiment files can be viewed in this documentation by reading the experiments subsections of the :ref:`components <components>` list.

.. note that we do not link to protein_expts.py above because its location might change and users should get used to consulting the components section

.. _config_file:

Config file
~~~~~~~~~~~

This script clones a copy of automacs, and generates an initial copy of ``config.py`` with the bare minimum settings. It then uses ``make set`` to add extension modules, and to point the code to two command-line interface modules found in ``amx/cli.py`` and ``inputs/docs/docs.py`` using ``make set commands``. The latter is responsible for compiling this documentation and is written to take advantage of the :any:`makefile interface <interface>`.

Starting simulations often requires starting configurations such as a protein crystal structure or the initial configuration for a polymer or bilayer. These files tend to be large, and should not be packaged alongside code. You can always place them in their own extension module. 

.. _finding_experiments:

Paths
~~~~~

The ``config.py`` file describes the rules for finding experiments. Since many extensions may provide many different standalone experiments and test sets, you may have a large list of experiments. Rather than requiring that each experiment has its own file, you can organize multiple experiments into one :doc:`experiment file <customize_experiments>`. Automacs finds these files according to the ``inputs`` item in ``config.py``. This can be a single string with a path to your experiments file, or a list of paths. Any path can contain wildcards. For the most flexibility, you can also set ``inputs`` to ``'@regex^.*?_expts\\.py$'``, where everything after ``@regex`` is a regular expression for matching *any file* in the automacs subtree. In this example, we require all experiment files to be named e.g. ``my_experiment_group_expts.py``.

.. _running_commands:

Interfaces
~~~~~~~~~~

Another item in the ``config.py`` dictionary is called ``commands``. It provides explicit paths to python scripts containing command-line interface functions described in the :any:`interface <interface>` section.

.. _simulation_source_material :

Bulky inputs
~~~~~~~~~~~~

Starting simulations often requires starting configurations such as a protein crystal structure or the initial configuration for a polymer or bilayer. These files tend to be large, and should not be packaged alongside code. You can always place them in their own extension module.

.. live_documentation

"Live" Docs
-----------

This documentation uses the modules list ``config.py`` to include the automatic documentation of any extension modules alongside this walkthrough. These are listed in the :ref:`components <components>` section below. Some extensions may only include starting structures or raw data, in which case they will be blank. This scheme ensures that adding codes to your copy of automacs will make it easy to read the accompanying documentation. Each copy of the documentation also serves as a "live" snapshot of the available codes.
