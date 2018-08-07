#!/bin/bash

flock=/tmp/.activate-project-role.lock

if [ -f $flock ]; then
    echo "previous process still running ... existing"
    exit 0
fi

touch $flock

source /mnt/software/_modules/setup.sh
module load cluster
#module load python/2.7.8

${CLUSTER_UTIL_ROOT}/external/project_acl/sbin/activate-project-role.py $*

rm -f $flock
