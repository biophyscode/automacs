.. _customize_experiments:

Customizing your experiments
===========================

Experiments are stored in special files consisting solely of a single Python dictionary literal.

.. literalinclude :: ../../../inputs/proteins/protein_expts.py

There are three kinds of experiments: (1) standard experiments (2) sequences of experiments called a "metarun", and (3) quick scripts. These categories are outline when you run ``make prep?`` to list the available experiments. Each type has specific requirements outlined in the acme section, but all three types make use of a large block of text named ``settings``.

Two other key variables are important to the experiments: a ``params`` file which contains input specifications for gromacs and processed by :any:`write_mdp() <automacs.write_mdp>`, and the relative path to the procedure script.

Settings
--------

Settings are written in a custom format loosely based on the `YAML <http://yaml.org/>`_ format. In short, settings are specified by key-value pairs delimited by a colon. Python will try to evaluate the following text using its ``eval`` statement, otherwise the result is stored as a string. Multiline texts use a blasé colon-pipe ``:|`` operator which reads indented text. Any tab sequence is allowed, and the parser stops reading the text where the indentation ends. 

Automacs makes all of the settings available in the shared namespace by using either standard dictionary notation (``state['water_thickness']``) or a more concise attribute notation (``state.water_thickness``). For this reason, all settings keys have spaces replaced by the underscore character. The settings are not actually loaded into ``state``, which checks ``settings`` for keys that cannot be found inside of it. The ``state.q('key','default')`` function works like the dictionary ``get`` function in python, allowing you to provide a default value of the key also cannot be found in the settings block.

Many automacs functions refer to the settings to guide the construction of the simulation.

Extensions
----------

Extensions can be specified using wildcards so you can import the entire ``inputs/extras`` package by including ``inputs/extras/*.py`` in the ``extensions`` list in an experiment. Extensions are automatically imported by automacs whenever it is imported. This saves users the trouble of managing the imports: *any function in any extension is elevated to the automacs namespace*. Users can still use standard, pythonic imports from these extensions (see an example in the acme section), however the experiment's extensions list manages everything that goes into the namespace.

The extensions list also overrides core automacs functionality, which means that you can easily tune or change these functions however you like, in new extensions. Your extensions can also make use of any third-party or entirely generic code modules (read: those codes not affiliated with automacs).