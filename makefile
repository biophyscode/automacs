### makeface (MAKEfile interFACE)
### a crude but convenient way of making CLI's for python
### this file requires makeface.py (see the documentation there)

# connect to runner
makeface = runner/makeface.py

# script and checkfile force the execution
checkfile = .pipeline_up_to_date
protected_targets=
# pass debug flag for automatic debugging
PYTHON_DEBUG = "$(shell echo $$PYTHON_DEBUG)"
python_flags = "-B"

# filter and evaluate
MAKEFLAGS += -s
RUN_ARGS_UNFILTER := $(wordlist 1,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
RUN_ARGS := $(filter-out $(protected_targets),$(RUN_ARGS_UNFILTER))
$(eval $(RUN_ARGS):;@:)

# valid function names from the python script
TARGETS := $(shell python $(python_flags) $(makeface) | \
	perl -ne 'print $$1 . "\n" if /.+\:(.*?)\n/')

# make without arguments first
default: $(checkfile)
# make with arguments
$(TARGETS): $(checkfile)

# exit if target not found
controller_function = $(word 1,$(RUN_ARGS))
ifneq ($(controller_function),)
ifeq ($(filter $(controller_function),$(TARGETS)),)
    $(info [ERROR] "$(controller_function)" is not a valid make target)
    $(info [ERROR] see the makefile documentation for instructions)
    $(info [ERROR] make targets="$(TARGETS)"")
    $(error [ERROR] exiting)
endif
endif

# route the make command to makeface every time
touchup:
	@touch $(checkfile)
$(checkfile): touchup
	@/bin/echo "[STATUS] calling controller: python $(python_flags) \
	$(makeface) ${RUN_ARGS} ${MAKEFLAGS}"
	@env PYTHON_DEBUG=$(PYTHON_DEBUG) python $(python_flags) \
	$(makeface) ${RUN_ARGS} ${MAKEFLAGS} && \
	echo "[STATUS] done" || { echo "[STATUS] fail"; exit 1; }
