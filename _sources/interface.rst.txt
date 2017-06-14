.. interface:

Interface
=========

Automacs execution is controlled almost entirely by text files which hold :ref:`experiments <customize_experiments>`. There are a few commands that run the experiments which are executed by a very peculiar, overloaded ``Makefile`` which routes user commands to the appropriate python codes using the :any:`makeface <makeface>` functions. We use this scheme because `make <https://www.gnu.org/software/make/>`_ is ubiquitous on many computer systems, it often includes automatic completion, and it's easy to remember. The interface is extremely generic: *almost any python function can be exposed to the interface*. To see which ``make`` sub-commands are available, simply run ``make`` without arguments. 

.. code-block :: bash

	make targets
	│
	├──back
	├──clean
	├──cluster
	├──config
	├──docs
	├──download
	├──flag_search
	├──gitcheck
	├──gitpull
	├──go
	├──gromacs_config
	├──layout
	├──locate
	├──look
	├──metarun
	├──notebook
	├──prep
	├──prep?
	├──qsub
	├──quick
	├──run
	├──set
	├──setup
	├──upload
	└──watch

Commands
--------

As we discused in the :ref:`procedures section <concept_procedures>`, users can run experiments using :any:`make go <control.go>`. To see which experiments are available, use :any:`make prep <control.prep>` which lists them. These are the two most important commands. The :any:`make go <control.go>` command will run :any:`make clean sure <control.clean>` if you send it the ``reset`` flag, (this will clear any old data from the directory, so be careful) and then immediately run one of the execution commands, depending on the type of experiment, using :any:`make run <control.run>`, :any:`make metarun <control.metarun>`, or :any:`make quick <control.quick>`. 

Additions
---------

In the :any:`configuration <running_commands>` section we mentioned that the ``commands`` key in ``config.py`` tells automacs where to find new functions. Any paths set in the ``commands`` list are scanned by the :any:`makeface <makeface>` module for python functions. These function names become sub-commands for ``make``. 

Arguments are passed from the ``makefile`` to the python code according to a few simple rules. The functions cannot use ``*args`` or ``**kwargs`` because the interface code performs introspection to send arguments to the function. You can use ``key="value"`` pairs to specify both arguments and keyword arguments. Sending a single flag (e.g. ``sure`` in :any:`make clean sure <control.clean>`) will send ``sure=True`` as a boolean to the function. Order only matters if you are passing arguments (for obvious reasons). The safest bet is to use keyword arguments to avoid mistakes, however functions are straightforward because they only take one argument e.g. :any:`make go <control.go>`.

Most of the automacs utility functions are found in the :any:`command-line interface <cli>` module and the :any:`control <control>` module.

Tricks
------

The :ref:`experiment files <experiments>` provide execution instructions to automacs depending on their format. These formats are specified in the :any:`controlspec code <controlspec>`, which determines the control flow for the execution. The remainder of the interface functions are really just helper functions that make some tasks easier. The following lists covers a few useful functions.

1. :any:`make back <control.back>` will help you run simulations in the background.
2. :any:`make watch <cli.watch>` will monitor the newest log file in your simulation.
3. :any:`make locate <cli.locate>` will help you find a specific function.
4. :any:`make upload <cli.upload>` will upload files to a cluster.
5. :any:`make download <cli.download>` will download your files from the same cluster.
6. :any:`make notebook <cli.download>` will generate a `Jupyter <http://jupyter.org/>`_ notebook from an experiment.
