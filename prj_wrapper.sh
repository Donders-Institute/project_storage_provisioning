#!/bin/bash

## This wrapper script makes sure Environment module is loaded,
## and lanuch a corresponding python executable in the directory
## in which the wrapper is located.

me=`basename $0`

module list > /dev/null 2>&1

if [ $? != 0 ]; then
    source /opt/_module/setup.sh
    module load cluster
    module load python
fi

myexec=$(echo $me | sed 's/prj_//').py

## run the executable passing command-line arguments
$myexec $@
