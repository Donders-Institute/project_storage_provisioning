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

def createProjectDirectory(fpath, quota, type, cfg, lvl=0):
    '''general function for callers to make project directory'''

    logger = getMyLogger(lvl=lvl)

    ouid = cfg.get('PPS','PROJECT_DIR_OUID')
    ogid = cfg.get('PPS','PROJECT_DIR_OGID')

    rc = True

    if type == StorageType['fs_dir']:
        rc = __makeProjectDirectoryFS__(fpath, quota, ouid, ogid, lvl)
    elif type == StorageType['netapp_volume']:
        filer_admin       = cfg.get('PPS','FILER_ADMIN')
        filer_mgmt_server = cfg.get('PPS','FILER_MGMT_SERVER')
        rc = __makeProjectDirectoryNetApp__(fpath, quota, ouid, ogid, filer_admin, filer_mgmt_server, lvl)
    else:
        logger.error('unknown storage type: %s' % type)   

    return rc

### internal functions
def __makeProjectDirectoryFS__(fpath, quota, ouid, ogid, lvl):
    '''create a project directory directly on the file system'''

    logger = getMyLogger(lvl=lvl)
    rc     = True

    if os.path.exists(fpath):
        logger.warn('directory already exists: %s ... skip creation' % fpath)
    else:
        try:
            os.mkdir(fpath,0550)
            os.chown(fpath, pwd.getpwnam(ouid).pw_uid, grp.getgrnam(ogid).gr_gid)
        except OSError, e:
            logger.error('cannot create new directory: %s' % fpath)
            rc = False

    return rc

def __makeProjectDirectoryNetApp__(fpath, quota, ouid, ogid, filer_admin, filer_mgmt_server, lvl):
    '''create a project directory directly on the NetApp filer running Data ONTAP'''

    logger = getMyLogger(lvl=lvl)

    quotaGB = __getSizeInGB__(quota)

    if os.path.exists(fpath):
        logger.warn('directory already exists: %s ... skip creation' % fpath)
        return True
    else:
        s = Shell()

        ## 1. finding up aggregate information
        cmd = 'ssh %s@%s "storage aggregate show -fields availsize,volcount -stat online"' % (filer_admin, filer_mgmt_server)

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
                aggrs.append({'name': m.group(1), 'availsize': __getSizeInGB__(m.group(2)), 'volcount': int(m.group(3))})
            else:
                pass

        g_aggr = sorted(aggrs, key=operator.itemgetter('availsize'), reverse=True)[0]

        if g_aggr['availsize'] <= quotaGB:
            logger.error('aggreate with largest available size smaller the project quota: %f < %f' % (g_aggr['availsize'],quotaGB))
            return False

        logger.info('selected aggregate: %s' % repr(g_aggr))

        ## 2. create volume
        vol_name = 'project_%s' % fpath.split('/')[-1].replace('.','_')
   
        cmd = 'ssh %s@%s "volume create -vserver atreides -volume %s -aggregate %s -size %s -user %s -group %s -junction-path %s -security-style unix -unix-permissions 0550 -autosize false -foreground true"' % (filer_admin, filer_mgmt_server, vol_name, g_aggr['name'], quota, ouid, ogid, fpath)

        logger.debug('cmd creating volume: %s' % cmd)

        rc, output, m = s.cmd1(cmd, allowed_exit=[0,255], timeout=300)
        if rc != 0:
            logger.error('%s failed' % cmd)
            logger.error('%s' % output)
            return False
        else:
            return True
  
def __getSizeInGB__(size):
    '''convert size string to numerical size in GB'''

    logger = getMyLogger()

    s = 0

    if size.find('PB') != -1:
        s = float(size.replace('PB','')) * (1024**2)

    elif size.find('TB') != -1:
        s = float(size.replace('TB','')) * 1024

    elif size.find('GB') != -1:
        s = float(size.replace('GB',''))

    elif size.find('MB') != -1:
        s = float(size.replace('MB','')) / (1024)
        
    elif size.find('KB') != -1:
        s = float(size.replace('MB','')) / (1024**2)

    elif size.find('B') != -1:
        s = float(size.replace('B','')) / (1024**3)

    else:
        ## assuming unit of byte if input argument contains only numerical characters
        try:
            s = float(size) / (1024**3)
        except:
            logger.error('cannot convert size to bytes: %s' % s)
            raise

    return s
