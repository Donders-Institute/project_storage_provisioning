#!/bin/bash

source /mnt/software/_modules/setup.sh
module load cluster
module load python/2.7.8

${CLUSTER_UTIL_DIR}/external/project_acl/sbin/activate-project-role.py

