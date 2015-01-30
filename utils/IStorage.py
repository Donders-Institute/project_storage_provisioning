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

    def __exec_filer_cmd_ssh__(filer_admin, filer_mgmt_server, cmd, timeout=300, shell=None, lvl=0):
        '''private function for executing filer command via SSH interface'''
        if not shell:
            shell = Shell()
        return shell.cmd1('ssh %s@%s "%s"' % (filer_admin, filer_mgmt_server, cmd), allowed_exit=[0,255], timeout=timeout)

    quotaGB = __getSizeInGB__(quota)

    if os.path.exists(fpath):
        logger.warn('directory already exists: %s ... skip creation' % fpath)
        return True
    else:
        s = Shell()

        ## 1. finding a proper aggregate for allocating storage space for the volume
        cmd = 'storage aggregate show -fields availsize,volcount -stat online'
        logger.debug('cmd listing aggregates: %s' % cmd)
        rc, output, m = __exec_filer_cmd_ssh__(filer_admin, filer_mgmt_server, cmd, timeout=120, shell=s, lvl=lvl)
        if rc != 0:
            logger.error('%s failed' % cmd)
            logger.error(output)
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
   
        cmd  = 'volume create -vserver atreides -volume %s -aggregate %s -size %s -user %s -group %s -junction-path %s' % (vol_name, g_aggr['name'], quota, ouid, ogid, fpath)
        cmd += ' -security-style unix -unix-permissions 0550 -state online -autosize false -foreground true'
        cmd += ' -policy dccn-nfs -space-guarantee none -snapshot-policy none -type RW -antivirus-on-access-policy default'
        cmd += ' -percent-snapshot-space 0'

        logger.debug('cmd creating volume: %s' % cmd)

        rc,output,m = __exec_filer_cmd_ssh__(filer_admin, filer_mgmt_server, cmd, shell=s, lvl=lvl)
        if rc != 0:
            logger.error('%s failed' % cmd)
            logger.error('%s' % output)
            return False

        ## 3. enable volume efficiency
        cmd = 'volume efficiency on -vserver atreides -volume %s' % vol_name
        logger.debug('cmd enabling volume efficiency: %s' % cmd)
        rc,output,m = __exec_filer_cmd_ssh__(filer_admin, filer_mgmt_server, cmd, shell=s, lvl=lvl)
        if rc != 0:
            logger.error('%s failed' % cmd)
            logger.error('%s' % output)
            return False

        ## 4. modify volume efficiency
        cmd = 'volume efficiency modify -schedule auto -vserver atreides -volume %s' % vol_name
        logger.debug('cmd setting volume efficiency: %s' % cmd)
        rc,output,m = __exec_filer_cmd_ssh__(filer_admin, filer_mgmt_server, cmd, shell=s, lvl=lvl)
        if rc != 0:
            logger.error('%s failed' % cmd)
            logger.error('%s' % output)
            return False

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
