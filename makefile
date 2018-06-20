
### makeface (MAKEfile interFACE)
### by Ryan Bradley, distributed under copyleft
### a crude but convenient way of making CLIs for python
### this file requires a minimal makeface.py and the ortho library

# set the shell (sh lacks source)
SHELL:=/bin/bash
# unbuffered output is best. exclude bytecode
# add the "-tt" flag here for python3 errors
python_flags = "-ttuB"
# remove protected standalone args
protected_targets=
# you can set the python executable before or after make
python?=python

# write makeface backend
define MAKEFACE_BACKEND
#!/bin/bash
"exec" "python" "-B" "$0" "$@"
from __future__ import print_function
import ortho
ortho.run_program()
endef
# to shell to python
export MAKEFACE_BACKEND

# unpack
MAKEFLAGS+=-s
RUN_ARGS_UNFILTER:=$(wordlist 1,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
RUN_ARGS:=$(filter-out $(protected_targets),$(RUN_ARGS_UNFILTER))

# request targets from python
#! getting targets requires one full loop with imports
#? speed things up by using a header of some kind, or ast?
SHELL_CHECK_TARGETS:=ORTHO_GET_TARGETS=True $(python) $(python_flags) -c "import ortho;ortho.get_targets()"
TARGETS:=$(shell ${SHELL_CHECK_TARGETS} | \
	perl -ne 'print $$1 if /^.*?make targets\:\s*(.+)/')
ENV_EXCLUDES:=set unset

# request env from config
SHELL_CHECK_ENV:=(ENV_PROBE=True $(python) $(python_flags) -c "import ortho")
ENV_CMD:=$(shell ${SHELL_CHECK_ENV} | \
	perl -ne 'print $$1 if /^.*?environment\:\s*(.+)/')

# single target is the intersection of available targets and the first argument
TARGET:=$(filter $(TARGETS), $(word 1,$(RUN_ARGS)))

# exit if target not found
controller_function = $(word 1,$(RUN_ARGS))
ifneq ($(controller_function),)
ifeq ($(filter $(controller_function),$(TARGETS)),)
    $(info invalid make target `$(controller_function)`)
    $(info see the makefile documentation for instructions)
    $(info make targets="$(TARGETS)")
    $(error missing target)
endif
endif

# dummy file for always executing
checkfile=.pipeline_up_to_date
touchup:
ifeq ($(RUN_ARGS),)
	@echo "[STATUS] makefile targets: \"$(TARGETS)\""
	@touch $(checkfile)
endif
$(checkfile): touchup

# make without arguments
default: $(checkfile)

# route to targets
$(TARGET): $(checkfile)
# if the target is in a special exclude list then we skip the environment and run directly
ifneq ($(filter $(TARGET),$(ENV_EXCLUDES)),)
	@/bin/echo "[STATUS] executing special function $(TARGET) without environment"
	@env $(python) $(python_flags) -c "$$MAKEFACE_BACKEND" ${RUN_ARGS} ${MAKEFLAGS}
else
# or if we have no environment we run directly
ifeq ($(ENV_CMD),)
	@/bin/echo "[STATUS] executing without environment"
	@env $(python) $(python_flags) -c "$$MAKEFACE_BACKEND" ${RUN_ARGS} ${MAKEFLAGS}
else
	@/bin/echo "[STATUS] environment: \"source $(ENV_CMD)\""
	( source $(ENV_CMD) && ENV_CMD="$(ENV_CMD)" env $(python) \
	$(python_flags) -c "$$MAKEFACE_BACKEND" ${RUN_ARGS} ${MAKEFLAGS} )
endif
endif
# ignore run arguments
$(RUN_ARGS): 
