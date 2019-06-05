#!/bin/bash
# run in a screen with specific log file
tmp_screen_rc=$(mktemp)
echo "[CLUSTER] temporary screenrc at $tmp_screen_rc"
cat <<EOF> $tmp_screen_rc
logfile ${SCREEN_LOG_QUEUE:-log-task-queue}
EOF
if [ -z "$STY" ]; then 
exec screen -c $tmp_screen_rc -Ldm -S factory /bin/bash "$0"
rm $tmp_screen_rc 
fi

: << "END"
LOCKNESS
The lockness.sh component is locked and starts a screen command.
This script must be locking and it calls a remote (usually a screen)
which then also has a trap to clear the lock.
To run something:
	echo "echo start && sleep 10 && echo done" > queue_pipe
To close the queue:
	echo "quit" > queue_pipe
END

: << "END"
For flock on MACOS
https://github.com/discoteq/flock
INSTALL VIA
FLOCK_VERSION=0.2.3
wget https://github.com/discoteq/flock/releases/download/\
v${FLOCK_VERSION}/flock-${FLOCK_VERSION}.tar.xz
xz -dc flock-${FLOCK_VERSION}.tar.xz | tar -x
cd flock-${FLOCK_VERSION}
./configure
make
make install
END

# set FLOCK_CMD manually after compiling on macos
FLOCK_CMD=${flock:-$FLOCK_CMD}

### LOCKER begins here 
echo "[CLUSTER] checking locks"
set -e
scriptname=$(basename $0)
lock=${LOCK_FILE:-"LOCK.${scriptname}"}
pipe_name=TASK_QUEUE
trap "rm -f $lock $pipe_name" EXIT
exec 200>$lock
$FLOCK_CMD -n 200 || exit 1
pid=$$
echo "# lock file for PID $pid" 1>&200
echo "# run this script to kill" 1>&200
echo "echo quit > $pipe_name" 1>&200

### LISTENER BEGINS HERE
echo "[CLUSTER] beginning to listen"
set -o errexit
set -o nounset
# create a named pipe
if [[ ! -e $pipe_name ]]; then 
	mkfifo $pipe_name 
	exec 3<> $pipe_name
fi
# read whatever from the named pipe.
while read job < $pipe_name
do
  jobstamp=${JOB_NAME:-$(date +%Y%m%d%H%M)}
  if [[ $job = 'quit' ]]; then
    echo "[CLUSTER] complete $jobstamp"
    exit
  fi
  echo "[CLUSTER] start job $jobstamp"
  echo "[CLUSTER] job command is \"$job\""
  (eval "$job")
  echo "[CLUSTER] end job $jobstamp"
done
