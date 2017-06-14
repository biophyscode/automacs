Concept
=======

Automacs is a set of python codes which prepares molecular simulations using common tools orbiting the popular `GROMACS <http://www.gromacs.org/>`_ integrator. The purpose of this project is to ensure that simulations are prepared according to a standard method which also bundles simulation data with careful documentation. Automacs (hopefully) makes it possible to generate large simulation datasets with a minimum of description and so-called "manual" labor which invites mistakes and wastes time. Automacs codes are meant to be cloned once for each simulation rather than installed in a central location. This means that each simulation has a copy of the code used to create it. The codes are extremely modular, and users can share novel experiments using `git <https://git-scm.com/>`_ and the automacs :ref:`configuration <code_config>`.

"Overloaded Python"
-------------------

High-level programming languages often rely on functions which can accept many different kinds of input while producing a consistent result that matches our intuition. This is called `overloading <https://en.wikipedia.org/wiki/Function_overloading>`_. The automacs codes are overloaded in two ways. First, simulation data files and directories for different procedures are organized in a uniform way. These file-naming conventions are described in the :ref:`framework <framework>`. Users who follow these rules can benefit from generic functions that apply to many different simulation types. For example, performing restarts or ensemble changes in GROMACS uses a single generic procedure, regardless of whether you are doing atomistic or coarse-grained simulations. Second, the procedure codes are organized to reflect the consistent naming conventions so that they can be used in as many situations as possible. The simulation-specific settings are separated from the generic, modular steps required to build a simulation so that users can simulate a variety of different systems without rewriting any code. In the next section, we will describe how this separation happens.

.. it would be useful to explain how to do restarts in the documentation and link to it above

.. _concept_procedures:

Procedures
----------

Automacs executes code in an extremely straightforward way: users first request an experiment, and then they run it. After you clone automacs, you can run a simulation with a single `make <https://www.gnu.org/software/make/>`_ command --- the automacs interface consists only of ``make`` commands and a set of customizations written to simple text files which we will :ref:`explain shortly <finding_experiments>`. In the following example, we choose to run the ``protein`` experiment.

.. code-block :: bash
  
  make go protein clean

The :any:`make go <control.go>` command does three things: it clears the data, prepares a new script, and then runs it. We always start by cleaning up the data from a previous run --- all useful data should be archived in a completed copy of automacs. Passing the ``clean`` flag to :any:`make go <control.go>` cleans up any old data by calling :any:`make clean sure <control.clean>` for you. The :any:`make prep <control.prep>` command lists all of the available experiments, which are detected according to instructions in the :ref:`configuration <finding_experiments>`. When you :any:`add extra modules <code_config>` to automacs, they typically come with new experiments, which means that :any:`make prep <control.prep>` returns a long list.

.. literalinclude :: ../code_examples/prep.txt

An experiment identifies the script you wish to run (we sometimes call them "procedures" or alternately "parent scripts"), and how the simulation should be customized. In the example above, we choose the ``protein`` experiment which serves as a demonstration of a simple protein-in-water simulation and requires very few extra codes. The :any:`make go <control.go>` command above calls :any:`make prep protein <control.prep>`, which finds the right procedure script and copies it to ``script.py`` in the root folder. It also collects the customizations and writes them to an experiment file called ``expt.json``, which will be discussed in the next section. The menu of experiments shown above indicates that ``protein`` is a "run". This is the standard experiment style, however we can also construct a "metarun", which is a sequence of standard procedures, or a "quick" script, which is a very short piece of code. These will be outlined in the :any:`experiments section <three_modes>`.

New users who wish to see how automacs works can run e.g. ``make clean && make go protein`` or ``make go protein clean`` (the latter does not ask for confirmation before deleting data). While this runs, you can take a look at :ref:`script.py <protein_script>` to see what the experiment looks like. These scripts always call on the customizations found in individual experiments (like ``protein``). These can be viewed in three places. The experiment file ``amx/proteins/protein_expts.py`` is the source which generates the ``expt.json`` with a few extra parameters. You can view this file from the terminal, but it is also :doc:`included in this documentation <amx-proteins/experiments>` along with the other :any:`components section <components>`. You can also run :any:`make look <control.look>` which starts a python terminal with the ``state`` variable, which you can read directly (it's a dictionary, but you can use the dot operator like a class to look at e.g. ``state.step``). Of these three options, the experiment file is the only place you should change the parameters. We have combined everything into one step using :any:`make go <control.go>` to simplify things, however automacs has a fairly minimal interface, and users can run the automacs scripts with only an ``expt.json`` file and the associated python modules. Everything else is `syntactic sugar <https://en.wikipedia.org/wiki/Syntactic_sugar>`_.

.. give a quickstart for the protein simulation by telling the user to make a new experiment. possibly consider automating this. is the exposition above too much?

If you wanted to skip the sugar and run the codes directly, you can use :any:`make prep protein <control.prep>` to prepare the ``expt.json`` and ``script.py`` files and then simply run ``python script.py``. If everything is in order, the simulation would run to completion. In this basic use-case, automacs has simply organized and executed some code for you. In practice, only the most mature codes run perfectly the first time. To make development easier, and to save a record of everything automacs does, we use :any:`make run <control.run>` to supervise the exection of ``script.py``. We will explain this in detail in the section :ref:`supervised execution <sec_supervised_execution>` below.

Using automacs is as simple as choosing an experiment, customizing it, and then running it with :any:`make go <control.go>`. The best practice is to always *copy and rename* the :any:`experiments <experiments>` to change them so that you don't lose track of which experiments work, and which ones still need some fine tuning.

Procedure scripts
~~~~~~~~~~~~~~~~~

Procedure scripts (sometimes we call these "parent scripts") are standard python scripts which must only import a single package into the global namespace.

.. code-block :: python

  from amx import *

Using ``import *`` may be somewhat un-Pythonic, however it allows our scripts to read like an entry in a lab notebook for running a computational experiment, and it generally makes them much more concise. The automacs import scheme does a lot of bookkeeping work for you behind the scenes. It reads the experiment, imports required modules that are attached to your local copy of automacs, and also ensures that all of your codes (functions, classes, etc.) have access to a namespace variable called ``state``. This dictionary variable (along with its partners ``expt`` and ``settings`` discussed :any:`later <settings_blocks>`), effectively solves the problem of passing information between functions. Any function can read or write to the state, which is carefully passed to new codes and written to disk when the simulation is completed.

.. _protein_script:

The most typical script is called ``protein.py`` and generates an atomistic protein-in-water simulation.

.. we hard-code the protein.py here because it might end up in a different location depending on your module paths

.. literalinclude :: ../code_examples/protein.py
  :tab-width: 4

As long as your procedure script leads off with ``from amx import *`` or alternately ``import amx``, then the import magic will import the core automacs functions (which also loads GROMACS), any extension modules you request, and distribute the ``state`` to all of them. The remainder of the script is just a sequence of functions that generate new configurations, run inputs, and all the assorted paraphernalia for a typical simulation.

Functions
~~~~~~~~~

The individual functions in an automacs-style procedure typically perform a single, specific task that a user might otherwise perform at the terminal. Some functions can be used to copy files, write topologies, or execute the GROMACS integrator. 

.. note that minimize is hard-coded. it might also be useful to hardcode the protein.py above

One of the most useful functions is called :any:`minimize() <automacs.minimize>`, which automates the process of performing energy minimization in GROMACS by taking a configuration file (and its topology), generating run inputs and executing the GROMACS integrator via `mdrun <http://manual.gromacs.org/programs/gmx-mdrun.html>`_. 

.. code-block :: python

  def minimize(name,method='steep',top=None):
    """
    Energy minimization procedure.

    Minimize a structure found at `name.gro` with topology 
    specified by the keyword argument `top` (otherwise `name.top`) 
    according to inputs found in input-<method>-in.mdp and ideally 
    prepared with :meth:`write_mdp <amx.automacs.write_mdp>`. 
    Writes output files to `em-<name>-<method>` and writes a 
    final structure to `<name>-minimized.gro`
    """
    gmx('grompp',base='em-%s-%s'%(name,method),
      top=name if not top else re.sub('^(.+)\.top$',r'\1',top),
      structure=name,log='grompp-%s-%s'%(name,method),
      mdp='input-em-%s-in'%method,skip=True)
    tpr = state.here+'em-%s-%s.tpr'%(name,method)
    if not os.path.isfile(tpr):
      raise Exception('cannot find %s'%tpr)
    gmx('mdrun',
      base='em-%s-%s'%(name,method),
      log='mdrun-%s-%s'%(name,method))
    shutil.copyfile(
      state.here+'em-'+'%s-%s.gro'%(name,method),
      state.here+'%s-minimized.gro'%name)

The minimize function has straightforward inputs and outputs, but it also makes use of ``state.here``, which holds the path to the current step (a folder) for this simulation. Note that most simulations only require a single step, whereas multi-step procedures might use a handful of steps. It also expects to find an ``mdp`` file with the appropriate name, and hence implicitly relies on another function called :any:`write_mdp <automacs.write_mdp>` to prepare these files. Most functions work this way, so that they can be easily used in many situations. Ideally, their docstrings, which are collected in the :ref:`documentation index <genindex>` should explain the correct inputs and outputs.

.. _sec_supervised_execution:

Supervised execution
~~~~~~~~~~~~~~~~~~~~

Robust simulation procedures can always be run with ``python script.py`` once they are prepared, however automacs includes a useful "supervision" feature that provides two advantages that are particularly useful for developing code.

1. The shared namespace called ``state`` is saved to a file called ``state.json`` when the job is complete. All functions that are imported by automacs are `decorated <https://www.python.org/dev/peps/pep-0318/>`_ with a function that logs its exeuction to the ``state.history`` variable.
2. Errors are logged to special variables inside of the ``state`` so that user-developers can correct errors and *continue the experiment from the last successful step*. The code makes use of Python's `internal syntax parser <https://docs.python.org/2/library/ast.html>`_ in order to find the earliest change in your code. This can be particularly useful when you are adding steps to a procedure which is still under development because it means that you don't have to repeat the earlier steps. Even if the procedure script located at ``script.py`` doesn't change, automacs still knows where to continue execution without repeating itself.
3. In the event that users wish to "chain" together a sequence of multiple discrete simulation steps, automacs can look back to completed steps (with states saved to e.g. ``state_1.json``) in order to access important details about the simulation, including its geometry and composition. Chaining multiple steps requires a "metarun" procedure and uses the alternate :any:`make metarun <control.metarun>` command instead of :any:`make run <control.run>`, but otherwise the execution is the same. The no-repetition feature described above in item two also works when chaining steps together as part of a :any:`"metarun" <three_modes>`.

Since the second feature above (which we call "iterative reexecution") is aimed at developers, it is hidden from the user and happens automatically when you repeat a failed simulation. That is, simulations will automatically continue from a failed state when you run :any:`make run <control.run>` after an error. 

The more important function of the shared namespace is that all parameters are automatically available to all imported functions via ``state`` dictionary. This saves users from writing interfaces between functions, and also provides a snapshot of your simulation in ``state.json`` when it is completed. This is explained further in the :any:`settings blocks <settings_blocks>` documentation below.

The remainder of the documentation covers the GROMACS- and automacs-specific :any:`configuration`, the :any:`command-line interface <interface>`, and the general :any:`framework` for organizing the data. The last part of the documentation, titled :ref:`components <components>` also provides a :ref:`"live" snapshot of the documentation <live_documentation>` for extension modules.
