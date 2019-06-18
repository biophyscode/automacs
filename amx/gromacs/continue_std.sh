#!/bin/bash

<<doc
Continuation script for GROMACS simulations.
This naming scheme uses "md.part%04d" as the prefix.
doc

# default time limits
MODE="extend"
EXTEND=1000
UNTIL=1000000

# custom time limits from arguments
cmd_incoming=$@
while [ "$#" -gt 0 ]; do
  case "$1" in
    -m) MODE="$2"; shift 2;;
    -e) EXTEND="$2"; shift 2;;
    -u) UNTIL="$2"; shift 2;;
    --mode=*) MODE="${1#*=}"; shift 1;;
    --extend=*) EXTEND="${1#*=}"; shift 1;;
    --until=*) UNTIL="${1#*=}"; shift 1;;
    --mode|--extend|--until) echo "$1 requires an argument" >&2; exit 1;;
    -*) echo "unknown option: $1" >&2; exit 1;;
	*) die "unrecognized argument: $1"; shift 1;;
  esac
done
echo "[STATUS] mode = ${MODE}"
echo "[STATUS] extend = ${EXTEND}"
echo "[STATUS] until = ${UNTIL}"
if [ -z $MODE ] && [ ! -z $UNTIL ] && [ ! -z $EXTEND ]; then
    echo "[STATUS] use mode to choose either etend or until"
    echo "[STATUS] command was: $0 $cmd_incoming"
fi
if [ "$MODE" = "extend" ]; then EXTEND_FLAG="-extend $EXTEND";
elif [ "$MODE" = "until" ]; then EXTEND_FLAG="-until $UNTIL";
else EXTEND_FLAG="-nsteps -1"; fi
echo "[STATUS] extending via: ${EXTEND_FLAG}"

recent () {
	# check for the latest file with a suffix
	PRUN=0
	for file in md.part*.$1; do
	if [ $(echo ${file:7:4} | sed 's/^0*//') -gt $PRUN ]; then
		PRUN=$(echo ${file:7:4} | sed 's/^0*//')
	fi
	done
	echo "$PRUN"
}

last_cpt=$(recent "cpt")
last_tpr=$(recent "tpr")

if [ ! "$last_cpt" == "$last_tpr" ]; then
	echo "[ERROR] latest CPT/TPR do not match: $last_tpr, $last_cpt"
	exit 1
fi

base_name=$(printf "md.part%04d" $(($last_cpt+1)))
prev_name=$(printf "md.part%04d" $last_cpt)
name_ints=$(printf "%04d" $last_cpt)
echo "[STATUS] simulations will continue at: $base_name"

gmx convert-tpr \
-s $prev_name.tpr -o $base_name.tpr ${EXTEND_FLAG} \
> log-mdrun-$name_ints 1>&2

gmx mdrun \
-cpi $prev_name.cpt -s $base_name.tpr \
-deffnm $base_name -noappend \
> log-mdrun-$name_ints 1>&2
