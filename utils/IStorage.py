#!/usr/bin/env python
import sys
import getpass
import os
import stat
import pwd
import grp 
import re 
import operator 
from utils.Common import getMyLogger
from utils.Shell  import *

StorageType = {'fs_dir':0, 'netapp_volume':1}

ProjectDirOwnerUser  = 'project'
ProjectDirOwnerGroup = 'project_g'

def makeProjectDirectoryFS(fpath, lvl=0):
    '''create a project directory directly on the file system'''

    logger = getMyLogger(lvl=lvl)
    rc     = True

    if os.path.exists(fpath):
        logger.warn('directory already exists: %s ... skip creation' % fpath)
    else:
        try:
            os.mkdir(fpath,0550)
            os.chown(fpath, pwd.getpwnam(ProjectDirOwnerUser).pw_uid, grp.getgrnam(ProjectDirOwnerGroup).gr_gid)
        except OSError, e:
            logger.error('cannot create new directory: %s' % fpath)
            rc = False

    return rc

def makeProjectDirectoryNetApp(fpath, quota, admin_login='admin', mgmt_server='filer-a-mi', lvl=0):
    '''create a project directory directly on the NetApp filer running Data ONTAP'''

    logger = getMyLogger(lvl=lvl)

    quotaTB = __getSizeInTB__(quota)

    if os.path.exists(fpath):
        logger.warn('directory already exists: %s ... skip creation' % fpath)
        return True
    else:
        s = Shell()

        ## 1. finding up aggregate information
        cmd = 'ssh %s@%s "storage aggregate show -fields availsize,volcount -stat online"' % (admin_login, mgmt_server)

        logger.debug('cmd listing aggregates: %s' % cmd)

        rc, output, m = s.cmd1(cmd, allowed_exit=[0,255], timeout=120)
        if rc != 0:
            logger.error('%s failed' % cmd)
            return False

        ## parsing the line similar to the following one: 
        ## aggr1a_fc   1.73TB 23
        ##
        ##  - field 1: aggregate name
        ##  - field 3: free space
        ##  - field 6: number of volumes on the same aggregate
        re_aggr_info = re.compile('^(aggr\S+)\s+(\S+[P,T,G,M,K]B)\s+([0-9]+)$')

        aggrs = [] 
        for l in output.split('\n'):
            m = re_aggr_info.match(l.strip())
            if m:
                aggrs.append({'name': m.group(1), 'availsize': __getSizeInTB__(m.group(2)), 'volcount': int(m.group(3))})
            else:
                pass

        g_aggr = sorted(aggrs, key=operator.itemgetter('availsize'), reverse=True)[0]

        if g_aggr['availsize'] <= quotaTB:
            logger.warn('aggreate with largest available size smaller the project quota: %f < %f' % (g_aggr['availsize'],quotaTB))
        logger.info('selected aggregate: %s' % repr(g_aggr))

        ## 2. create volume
        vol_name = 'project_%s' % fpath.split('/')[-1].replace('.','_')
   
        cmd = 'ssh %s@%s "volume create -vserver atreides -volume %s -aggregate %s -size %s -user %s -group %s -junction-path %s -autosize false -foreground true"' % (admin_login, mgmt_server, vol_name, g_aggr['name'], quota, ProjectDirOwnerUser, ProjectDirOwnerGroup, fpath)

        logger.debug('cmd creating volume: %s' % cmd)

        rc, output, m = s.cmd1(cmd, allowed_exit=[0,255], timeout=300)
        if rc != 0:
            logger.error('%s failed' % cmd)
            logger.error('%s' % output)
            return False

        ## 3. check if the path is presented
        if os.path.exists(fpath):
            os.chmod(fpath, stat.S_IRUSR ^ stat.S_IXUSR ^ stat.S_IRGRP ^ stat.S_IXGRP)
            return True
        else:
            logger.error('directory not found: %s, check volume creation in the filer' % fpath)
            return False
  
### private functions
def __getSizeInTB__(size):
    '''convert size string to numerical size in TB'''

    s = 0

    if size.find('PB') != -1:
        s = float(size.replace('PB','')) * 1024

    elif size.find('TB') != -1:
        s = float(size.replace('TB',''))

    elif size.find('GB') != -1:
        s = float(size.replace('GB','')) / 1024

    elif size.find('MB') != -1:
        s = float(size.replace('MB','')) / (1024**2)
        
    elif size.find('KB') != -1:
        s = float(size.replace('MB','')) / (1024**3)

    elif size.find('B') != -1:
        s = float(size.replace('B','')) / (1024**4)

    else:
        s = 1.0 * size

    return s
