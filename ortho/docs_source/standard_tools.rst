.. _standard-tools:

Standard tools
--------------

The following functions are elevated to the global namespace of the `ortho` module and are available directly via ``import ortho`` or ``from ortho import *``. The remaining functions are enumerated in the :ref:`submodules <submodules>` list.

Terminal
~~~~~~~~

:py:meth:`ortho.bash <ortho.bash.bash>`

Makefile interface
~~~~~~~~~~~~~~~~~~

:py:meth:`ortho.get_targets <ortho.cli.get_targets>`

:py:meth:`ortho.run_program <ortho.cli.run_program>`

Configuration
~~~~~~~~~~~~~

:py:meth:`ortho.read_config <ortho.config.read_config>`

:py:meth:`ortho.write_config <ortho.config.write_config>`

:py:meth:`make set_list <ortho.config.set_list>`

:py:meth:`make set_dict <ortho.config.set_dict>`

:py:meth:`make unset <ortho.config.unset>`

Dictionary
~~~~~~~~~~

:py:meth:`ortho.DotDict <ortho.dictionary.DotDict>`

:py:meth:`ortho.MultiDict <ortho.dictionary.MultiDict>`

Docs
~~~~

Build the docs with:

:py:meth:`make build_docs <ortho.docs.build_docs>`

Environments
~~~~~~~~~~~~

:py:meth:`make env <ortho.environments.environ>`

Imports
~~~~~~~

:py:meth:`ortho.importer <ortho.imports.importer>`

Miscellaneous
~~~~~~~~~~~~~

:py:meth:`ortho.treeview <ortho.misc.treeview>`
:py:meth:`ortho.str_types <ortho.misc.str_types>`
:py:meth:`ortho.say <ortho.misc.say>`

Execution
~~~~~~~~~

:py:meth:`make interact <ortho.reexec.interact>`
:py:meth:`ortho.iteratively_execute <ortho.reexec.iteratively_execute>`

Unit-tester
~~~~~~~~~~~

:py:meth:`make unit_tester <ortho.unit_tester.unit_tester>`

