#!/bin/bash

flock=/tmp/.report-project-role.lock

if [ -f $flock ]; then
    echo "previous process is still running ... existing"
    exit 0
fi

touch $flock

source /mnt/software/_modules/setup.sh
module load cluster
#module load python/2.7.8

${CLUSTER_UTIL_ROOT}/external/project_acl/sbin/report-project-role.py $*

rm -f $flock
