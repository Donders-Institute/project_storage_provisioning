#!/bin/bash

## This wrapper script makes sure Environment module is loaded,
## and lanuch a corresponding python executable.

me=`basename $0`

## checking whether the environment module is loaded
module list > /dev/null 2>&1
if [ $? != 0 ]; then
    source /opt/_module/setup.sh
    module load cluster
fi

## loading module for python 2.7+
module unload python > /dev/null 2>&1
module load python/2.7.8

myexec=$(echo $me | sed 's/prj_//').py

## run the executable passing command-line arguments
$myexec $@
