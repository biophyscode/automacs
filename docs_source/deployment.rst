Deployment
----------

Currently ``ortho`` is demonstrated in a standalone form by `skunkworks <https://github.com/bradleyrp/skunkworks>`_. You can add ``ortho`` to an existing git repository (with no working tree modifications) with the following commands.

.. code-block:: bash

	# add the remote
	git remote add ortho-up https://github.com/bradleyrp/ortho
	# add the subtree
	git subtree add --prefix=ortho ortho-up master
	# pull
	git subtree --prefix=ortho pull ortho-up master --squash

Note that you can also expose the ``makefile`` by running ``ln -s ortho/makefile.bak makefile`` after which point ``make`` will show the stock functions and generate a ``config.json`` for the first time.
