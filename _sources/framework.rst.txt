
.. _framework:

Framework
=========

The automacs codes have developed from a set of BASH, Perl, and Python scripts designed to construct specific simulations. Over time, the automacs developers chose `convention over configuration <https://en.wikipedia.org/wiki/Convention_over_configuration>`_ when designing new codes. This means that most functions are designed to be generic, discrete simulation steps create files with coherent naming schemes, and input/output flags for most functions look very similar. This makes the codes more general, and hence easy to apply to new simulations. Most of the variations between simulations are directed by experiments described in this section. Experiments are almost entirely specified by special python dictionaries and strings which are designed for readability.

In this section we describe the :any:`experiment files <experiments>`, :any:`file naming conventions <directory_structure>`, and :any:`namespaces <wordspace>`.

.. _experiments:

Experiments
-----------

A key design feature of automacs is that its computational experiments are specified almost entirely by text. While this text depends on many functions, we have sought to separate generic functions from highly-customized experiments so that users can easily reproduce, modify, and repeat experiments.

In the :any:`finding experiments <finding_experiments>` section, we explained that experiments can be located anywhere in the automacs directory tree as long as the ``config.py`` is set correctly and the experiments are written to scripts suffixed with ``_expts.py`` which only contain a single dictionary literal. This dictionary adds new experiments to the list (and automacs protects against redundant naming). 

*We highly recommend that users only create new experiments rather than modifying existing ones.* Our experiments have many parameters, and validated experiments in a test set should always be preserved for posterity. There is no limit to the number of experiments you can write, so the best practice is to use clear experiment names and avoid changing already-validated experiments.

.. _three_modes:

Modes
~~~~~

The :any:`make prep <control.prep>` command lists all available experiments organized into three modes: run, metarun, and quick. The :any:`make go <control.go>` function chooses the correct mode and executes them accordingly. Setting the mode is accomplished by including the right keys in your experiment dictionary (this is explained in the :any:`control flow <control_flow>` section below). Each type has a specific use case.

1. Experiments run with :any:`make run <control.run>` are the standard simulation type. They require a single procedure (or "parent script") which receives a single ``settings`` block that contains all of the settings. The ``protein`` demonstration is the canonical example of a run.
2. Experiments which use :any:`make metarun <control.metarun>` consist of a sequence of standard "run" experiments. Each step can contain its own settings, and these settings only override the defaults specified by the corresponding run. Each run creates a distinct step in the sequence.
3. Quick scripts are executed via :any:`make quick <control.quick>`. They do not use the ``make prep`` command, and are executed directly. Instead of using a parent script, they are executed directly from code embedded with the ``quick`` parameter in the experiment itself. Quick scripts can be part of a metarun sequence.

The "metarun" method allows you to create a sequence of simulation steps (which we sometimes call "chaining"). The information is passed between steps using ``state.json``, which is described below in the :any:`posterity <posterity> `

.. _control_flow:

Control flow
~~~~~~~~~~~~

Recall that each experiment is an item in a dictionary literal found in files suffixed with ``_expts.py`` according to the :any:`configuration <finding_experiments>`. Each of the three experiment types described in the previous section must have a specific set of keys validated by the :any:`controlspec code <controlspec>`.

*The best way to make a new experiment, of any type, is to copy one that already works.* This saves you the effort of parsing the :any:`controlspec code <controlspec>`. This code provides lists of required keys for each experiment type, along with their minor variations. It is designed to be extensible, so you can modify the control flow without too much trouble, however most of the test sets packaged with automacs extension modules include examples of all of the variations. 

If you fail to include the right keys, you will receive a specific error message. The standard experiment runs are the easiest, they require the following keys: ``['script','extensions','params','tags','settings','cwd']``. The ``cwd`` keys is appended automatically, the ``script`` is the relative path to the parent script, and the ``settings`` block holds the parameters for the experiment. The :any:`extensions <extensions>` allow your codes to import from *other* automacs extension modules (this helps eliminate redundancy across the codes). The ``tags`` are simple metadata used for distinguishing e.g. atomistic and coarse-grained simulations. The ``params`` key often points to a ``parameters.py`` file that can be read from :any:`write_mdp <automacs.write_mdp>`.

.. _settings_blocks:

Settings
~~~~~~~~

Aside from the ``script`` parameter, which supplies the path to the parent script (e.g. the ``protein.py`` script described :any:`earlier <protein-script>`), the ``settings`` block contains most of the parameters. The following is an example from the ``protein`` experiment.

.. code-block :: python

  step: protein                       # name of the folder is s01-protein
  force field: charmm27               # which gromacs-standard force-field to use (see pdb2gmx list)
  water: tip3p                        # which water model (another question from pdb2gmx)
  equilibration: nvt-short,nvt,npt    # which equilibration step to use (must have `input-name-in.mdp` below)
  pdb source: 1yrf                    # PDB code for download. overrides the start structure
  start structure: None               # path to PDB structure or None to use a single PDB in inputs
  protein water gap: 3.0              # Angstroms distance around the protein to remove water
  water buffer: 1.2                   # distance (nm) of solvent to the box wall 
  solvent: spc216                     # starting solvent box (use spc216 from gromacs share)
  ionic strength: 0.150               # desired molar ionic strength
  cation: NA                          # name of the cation for neutralizing the system
  anion: CL                           # name of the anion for neutralizing the system

  #---INTEGRATOR PARAMETERS generated via parameters.py
  mdp_specs:| {
    'group':'aamd',
    'mdps':{
      'input-em-steep-in.mdp':['minimize'],
      'input-em-cg-in.mdp':['minimize',{'integrator':'cg'}],
      'input-md-nvt-eq-in.mdp':['nvt-protein','nvt-protein',{'nsteps':10000}],
      'input-md-nvt-short-eq-in.mdp':['nvt-protein-short',{'nsteps':10000}],
      'input-md-npt-eq-in.mdp':['npt-protein',{'nsteps':10000}],
      'input-md-in.mdp':{'nsteps':100000},
      },
    }

The settings block is designed in a format meant to resemble `YAML <http://www.yaml.org/>`_ for its readability. Keys and values are separated by a colon, whitespace is omitted, and everything that follows the colon is interpreted first as python syntax, and if that fails, then as a float or a string. Multiline values (see ``mdp_specs`` above) are noted with ``:|`` instead of just a colon, and they continue until the arbitrary tab at the beginning of each line is absent. Commonts are allowed with hashes. These blocks are interpreted by the :any:`yamlb function <datapack.yamlb>`, which also uses the :any:`jsonify <datapack.jsonify>` function to check for repeated keys.

All of the settings are passed to ``expt.json``, unpacked into the global namespace variable mysteriously labelled ``settings``, and thereby exposed to any python functions imported by automacs. Note that the global namespace variable called ``state`` :any:`described below <wordspace>` will check ``settings`` if it cannot find a key that you ask for. In that sense, the ``settings`` are available everywhere in your code. See the :ref:`state <wordspace>` section below for more details. 

.. _extensions:

Extensions
----------

To avoid redundant codes in separate modules, the automacs modules can import codes from other modules. These codes are imported based on a list of `globs <https://en.wikipedia.org/wiki/Glob_(programming)>` in the ``extensions`` item of the experiment. These can be paths relative to the root directory that point to other modules. Alternately, users can use syntax sugar to access other modules by the name of their directory. For example, adding all of the codes in bilayer module to your experiment can be done by adding ``@bilayer/codes/*.py`` to your extensions list. The ``@bilayer`` will be replaced by the location of the bilayer module according to ``config.py``, typically ``inputs/bilayers``. The ``@module`` syntax sugar works in *any key in the settings blocks*, so that your experiments can draw from other extension modules without knowing where they are ahead of time. The path substitutions are handled in :any:`a special settings parser <loadstate.yamlb_special>`.

Any objects imported by the main ``amx`` module can be overridden by objects in the extension modules by adding their names to the ``_extension_override`` list at the top of the script. Similarly, objects can be automatically shared between extensions using the ``_shared_extensions`` list. These allow you to write a single code that either changes a core functionality in the main ``amx`` module or is shared with in-development extension modules. The import scheme is handled almost entirely in the ``runner/importer.py``, which is omitted from the documentation for technical reasons. One example of a shared extension is the :any:`dotplace <common.dotplace>` function, which makes sure ``gro`` file output has aligned decimal places. 

.. _wordspace:

State
-----

In order to transmit key settings and measurements between simulation procedure steps or within functions in the same procedure, we store them in an overloaded dictionary called the ``state``. We use a special :any:`DotDict <datapack.DotDict>` class to access dictionary keys as attributes. For this reason, *all spaces in the keys are replaced with underscores.* 

As we mentioned above, the ``state`` consults the ``settings`` when it cannot find a key that you ask for. This means that you can keep simulation parameters sequestered in the ``settings`` while keeping on-the-fly calculations in ``state``. Everything gets saved to ``state.json`` at the end.

We recommend accessing settings by using ``state``. In the example experiment above (in the :ref:`settings block <settings_blocks>` section), the water model is set by ``water`` in settings. You could access it using the following syntax:

1. ``settings['water']``
2. ``settings.water``
3. ``settings.get('water','tips3p')``
4. ``state['water']``
5. ``state.water``
6. ``state.q('water','tips3p')``

We prefer the last two methods. Use ``settings.get`` or ``state.q`` if you wish to set a default in case the parameter is absent. Requesting an absent parameter from ``settings`` will throw an exception, however, requesting an absent parameter from the ``state`` always returns ``None``. This means that you can write e.g. ``if state.add_proteins: ...`` to concisely control the execution of your simulation. 

.. _posterity:

Posterity
~~~~~~~~~

In the introduction to the documentation we described the :ref:`"supervised execution" <sec_supervised_execution>` of automacs codes. In short, this feature allows you to continue from the last command in a failed execution, but more importantly, it sends the ``state`` everywhere and saves it to ``state.json`` when the simulation is finished. 

Saving variables
""""""""""""""""

These features provide a simple way to create a sequence of simulation steps that depend on each other. These simulations are executed by :any:`make metarun <control.metarun>` --- sometimes we call this "chaining". Information can passed to the next step simply by saving it in the state. For example, you might want to make a small bilayer larger by using the ``multiply`` function (currently located in the ``extras`` module). After constructing a simple bilayer, the composition is stored in ``state.composition``. In the second step of the metarun, the ``multiply.py`` parent script can refer to ``state.before[-1]`` to access a dictionary that holds the previous state. This also includes the settings at ``state.before[-1]['settings']`` so that you don't need to repeat your settings in the following steps of the metarun. This scheme allows sequential steps to communicate important details about the outcome, geometry, or other features of a simulation.

GROMACS History
"""""""""""""""

In addition to saving the previous states, automacs also intercepts any calls to GROMACS commands and logs them in a special variable called ``history_gmx``. Users can call e.g. :any:`get_last_gmx_call('mdrun') <calls.get_last_gmx_call>` to retrieve the inputs and ouputs for the most recent call to any gromacs utility, typically ``mdrun``. This makes it easy to get the last checkpoint, run input file, or structure.

History
"""""""

A complete record of everything that automacs does is recorded in ``state.history``. Every time an automacs function is called, it is added to this list in a pythonic format, with explicit ``*args`` and ``**kwargs``. This feat is accomplished by the :any:`loud <states.loud>` function, which decorates every imported function, except for those named in the ``_acme_silence`` variable (so that you can silence functions with extremely long arguments). The history is also written to a log file in each step folder called e.g. ``s01-protein/s01-protein.log``.

.. _directory_structure:

Naming conventions
------------------

While the ``state`` and ``settings`` described above are explicit features of automacs that determine its execution, we also follow a number of more implicit rules about preparing the data. These are fairly general, and only serve to make it easy to keep track of all of your data.

Directories
~~~~~~~~~~~

In order to ensure that automacs procedures can be re-used in many different situations, we enforce a consistent directory structure. This makes it easy for users to write shorter codes which infer the location of previous files without elaborate control statements. The basic rule is that each procedure gets a separate folder, and that subsequent procedures can find input data from the previous procedure folder. 

We find it hard to imagine that users would chain more than 99 steps together, so we name each step with a common convention that includes the step number e.g. ``s01-bilayer`` and ``s02-large-bilayer`` etc. Many automacs functions rely on this naming structure. For example, the :meth:`upload <cli.upload>` function is designed to send only your latest checkpoint to a supercomputer to continue a simulation, and thereby avoid sending all of your data to a new system. The step folders also correspond to discrete states of the system, which are backed up to e.g. ``state_1.json`` when the step is complete. When chaining runs together as part of a :any:`metarun <three_modes>`, users can access previous states by using the :any:`history variables <posterity>` which record a history of what automacs has done so far.

The step name is always provided by the ``step`` variable in the settings block. To create the directory, each parent script typically calls :any:`make_step(settings.step) <automacs.make_step>` after its required :any:`initialization <automacs.init>`. You will see ``state.here`` used throughout the codes. It points to the current step directory.

.. _file_names:

Files
~~~~~

Within each procedure directory, we also enforce a file naming scheme that reflects much of the underlying GROMACS conventions. In particular, when simulations are extended across multiple executions, we follow the ``md.part0001.xtc`` numbering rules. Every time the ``mdrun`` integrator is invoked, automacs writes individual trajectory, input binary, and checkpoint files. Where possible, it also writes a configuration file at the conclusion of each run. 

When we construct new simulations, we also follow a looser set of rules that makes it easy to see how the simulations were built.

1. All GROMACS output to standard output and standard errors streams (that is, written to the terminal) is captured and stored in files prefixed with ``log-<gromacs_binary>``. In this case we label the log file with the gromacs utility function used to generate it. Since many of these functions are called several times, we also use a name for that part of the procedure. For example, during bilayer construction, the file ``s01-bilayer/log-grompp-solvate-steep`` holds the preprocessor output for the steepest descent minimization of the water-solvated structure. 
2. While output streams are routed to log files, the formal outputs from the GROMACS utilities are suffixed with a name that corresponds to their portion of the construction procedure. We use the prefix ``em`` to denote energy minimization and ``md`` to denote molecular dynamics. For example, minimizing a protein in vaccuum might output files such as ``em-vacuum.tpr`` while the NVT equilibration step might be labelled ``md-nvt.xtc``. 
3. Intermediate steps that do not involve minimization or dynamics are typically prefixed with a consistent name. For example, when adding water to a protein or a bilayer, automacs will generate several intermediate structures, all prefixed with the word "solvate" e.g. ``solvate-dense.gro``.

.. _retrieval:

Getting inputs
~~~~~~~~~~~~~~

A few protected keywords in the ``settings`` blocks will copy input files for you. The ``sources`` list should be a list of folders to copy into the current step, while ``files`` points to individual files. All paths should be relative to the root directory, however there is syntax sugar for :any:`pointing to extensions <extensions>`.

Simplicity
----------

In this section we have described how automacs organizes files. In general the file-naming rules are not absolute requirements for the simulations to complete. Instead, these "rules" have two purposes. First, if you use highly consistent and descriptive naming schemes, then you can easily re-use code in new situations. For example, many of the automacs procedures were developed for atomistic simulations. A few simple name changes along with some extra input files are oftentimes enough to port these procedures to coarse-grained systems or develop more complicated simulations.

The second purpose of our elaborate-yet-consistent naming scheme is to ensure that the data you produce are **durable**. Carefuly naming can ensure that future users who wish to study your data will not require an excessive amount of training to understand what it holds. An obvious naming scheme makes it easy to share data, find old simulations, and more importantly, parse the data with analysis programs once the dataset is complete. The `omnicalc <http://github.com/biophyscode/omnicalc>`_ analysis package is designed to process data prepared by automacs, and these file-naming rules and saved ``state.json`` files make it easy for these programs to be used together. 

This concludes the automacs walkthrough. Check out the `BioPhysCode <biophyscode.github.io>`_ project for extra calculation codes, that are designed to read and interpret simulations produced with automacs. Good luck!

