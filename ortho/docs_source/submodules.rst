.. _submodules:

Submodules
----------

To use ``ortho`` you can access the :ref:`standard tools <standard-tools>` directly using e.g. ``ortho.bash``. Functions which are not available at the global namespace (even though they are contained in a submodule) must be imported using the submodule name. For example, the ``DotDict`` class is not available at the top level, and must be accessed by its submodule name using e.g. ``from ortho.dictionary import DotDict``.


.. toctree::
   :maxdepth: 2

   ortho.cli
   ortho.bash
   ortho.config
   ortho.misc
   ortho.reexec
   ortho.imports
   ortho.environments
   ortho.documentation
   ortho.dictionary
   