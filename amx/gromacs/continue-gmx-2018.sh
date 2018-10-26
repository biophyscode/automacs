#!/bin/bash

echo "[STATUS] continue script"

# settings
MODE="extend"
EXTEND=1000000
UNTIL=1000000
MDRUN="gmx mdrun"
MAXWARN=0
MAXHOURS=24.0
GROMPP="gmx grompp"
TPBCONV="gmx convert-tpr"

# injected settings go here

# arguments (override) for extend flag
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

# formulate the extend flag
echo "[STATUS] mode = ${MODE}"
echo "[STATUS] extend = ${EXTEND}"
echo "[STATUS] until = ${UNTIL}"
if [ "$MODE" = "extend" ]; then EXTEND_FLAG="-extend $EXTEND";
elif [ "$MODE" = "until" ]; then EXTEND_FLAG="-until $UNTIL";
else EXTEND_FLAG="-nsteps -1"; fi
echo "[STATUS] extending via: ${EXTEND_FLAG}"

# find last CPT
PRUN=0
for file in md.part*.cpt
do
if [ $(echo ${file:7:4} | sed 's/^0*//') -gt $PRUN ]; 
then PRUN=$(echo ${file:7:4} | sed 's/^0*//')
fi
done
NRUN=$(($PRUN+1))

# log to standard log
step=$(pwd | sed -r 's/.+\/(.+)//')
metalog="../continuation.log"
echo "[STATUS] continuing simulation from part $PRUN in $step"
echo "[STATUS] logging to $metalog"
echo "[STATUS] running ... "

# extend TPR
log=$(printf tpbconv-%04d $NRUN)
cmd="$TPBCONV $EXTEND_FLAG -s $(printf md.part%04d.tpr $PRUN) -o $(printf md.part%04d.tpr $NRUN)"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec

# continue simulation
log=$(printf mdrun-%04d $NRUN)
cmd="$MDRUN -noappend -deffnm  md -s $(printf md.part%04d.tpr $NRUN) -cpi $(printf md.part%04d.cpt $PRUN) -cpo $(printf md.part%04d.cpt $NRUN) -maxh $MAXHOURS"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec
echo "[STATUS] done continuation stage"
