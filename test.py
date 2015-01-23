#!/bin/env python
import sys
import os 
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/external/lib/python')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.Common import getConfig, getMyLogger, csvArgsToList
from utils.IStorage import StorageType,createProjectDirectory

## load configuration file
cfg  = getConfig( os.path.dirname(os.path.abspath(__file__)) + '/etc/config.ini' )

fpath = '/project/0000000.03'
quota = '1GB'
stype = 'fs_dir'

rc = createProjectDirectory(fpath, quota, StorageType[stype], cfg, lvl=3)
