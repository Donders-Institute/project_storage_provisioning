#!/usr/bin/env python
import logging
import pickle
from utils.Shell  import *
from utils.Common import getMyLogger, getClientInfo

ROLE_ADMIN       = 'admin'
ROLE_CONTRIBUTOR = 'contributor'
ROLE_USER        = 'user'

ROLE_ACL         = { ROLE_ADMIN       : 'RXWdDoy',
                     ROLE_CONTRIBUTOR : 'rwaDdxnNtTcy',
                     ROLE_USER        : 'RXy' }
   
def get_permission(role):
    ''' gets permission bits for DENY and ALLOW, given the role
    '''
    all_permission = 'rwaDdxnNtTcCoy'

    _alias_ = { 'R': 'rntcy',
                'W': 'watTNcCy',
                'X': 'xtcy' }
 
    acl = {} 
    try:
        _acl_a = ROLE_ACL[role]

        for k,v in _alias_.iteritems():
            _acl_a = _acl_a.replace(k, v)

        _acl_a = ''.join( list( set(list(_acl_a)) ) )
        _acl_d = ''.join( list( set(list(all_permission)) - set(list(_acl_a)) ) )

        acl['A'] = _acl_a
        acl['D'] = _acl_d

    except KeyError,e:
        logger.error('No such role: %s' % role)

    return acl

def getRoleFromACE(ace, lvl=0):
    ''' converts ACE permission into the defined roles: admin, user, contributor
    '''

    logger = getMyLogger(lvl=lvl)

    diff = {}
    for r in [ROLE_ADMIN, ROLE_CONTRIBUTOR, ROLE_USER]:
        diff[r] = list( set(list(ace)) ^ set(list( get_permission(r)['A']  )) )
        logger.debug('diff to role %s: %s' % (r, repr(diff[r])))

    ## find the closest match, i.e. shortest string on the value of the diff dict
    return sorted(diff.items(), key=lambda x:len(x[1]))[0][0]

def delACE(path, users, force=False, lvl=0):
    ''' deletes all ACEs related to the given list of users.
         - force: update the ACL anyway even the given user is not in ACL. 
    '''

    logger = getMyLogger(lvl=lvl)

    ## get the existing ACL
    o_aces = getACE(path, recursive=False, lvl=lvl)[path]

    if not force:
        ## check users in existing ACL to avoid redundant operations
        _u_exist = []
        for tp,flag,principle,permission in o_aces:
            u = principle.split('@')[0]
            if u not in _u_exist + ['GROUP','OWNER','EVERYONE']:
                _u_exist.append(u)

        ## resolve the users requiring actual removal of ACEs
        _u_remove = list( set(users) & set(_u_exist) )
        for u in users:
            if u not in _u_remove:
                logger.warning('user not presented in ACL: %s' % u)

        users = _u_remove

    ## simply return with True if no user for ACE removal
    if not users:
        logger.warning("I have nothing to do!")
        return True
            
    ## compose new ACL regarding the removal
    n_aces = []
    for a in o_aces:
        u = a[2].split('@')[0]
        if u not in users:
            n_aces.append(':'.join(a))
        else:
            logger.info('deleting ACEs of user: %s' % u)

    _opts = ['-R','-s']

    return __nfs4_setfacl__(path, n_aces, _opts, lvl=lvl)

def getACE(path, user=None, recursive=False, lvl=0):
    ''' gets ACEs for given user or for all ACEs if user is not given. 
    '''

    logger = getMyLogger(lvl=lvl)

    def __nfs4_getfacl__(fpath):

        logger.debug('get ACL of %s ...' % fpath)

        ## workaround for NetApp for the path is actually the root of the volume
        if fpath[-1] is not '/':
            fpath += '/'

        cmd = 'nfs4_getfacl %s' % fpath 
        rc, output, m = s.cmd1(cmd, allowed_exit=[0,255], timeout=None)
        if rc != 0:
            logger.error('%s failed' % cmd)
            return None
        else:
            return __parseACLStr__(output)
        
    acl = {}
    s   = Shell()
    if recursive:
        ## walk through all directories/files under the path
        for r,ds,fs in os.walk(path,onerror=__fs_walk_error__):
            ## retrieve directory ACL
            acl[r] = __nfs4_getfacl__(r)
 
            ## retrieve file ACL
            for f in map(lambda x:os.path.join(r,x), fs):
                acl[f] = __nfs4_getfacl__(f)
    else:
        acl[path] = __nfs4_getfacl__(path)

    return acl

def setDefaultPrincipleACE(path, lvl=0):
    ''' sets initial / default ACEs for default principles: USER, GROUP and EVERYONE
    '''
    logger = getMyLogger(lvl=lvl)

    ## get the existing ACL
    aces = getACE(path, recursive=False, lvl=lvl)[path]

    ## compose new ACL based on the existing ACL
    n_aces = []
    for a in aces:
        u = a[2].split('@')[0]
        if u in ['GROUP','OWNER','EVERYONE']:
            ## to make it general: remove 'f' and 'd' bits and re-prepend them again
            a[1] = 'fd%s' % a[1].replace('f','').replace('d','')

        n_aces.append(':'.join(a))

    opts  = ['-R', '-s']
    return __nfs4_setfacl__(path, n_aces, opts, lvl=lvl)

def setACE(path, users=[], contributors=[], admins=[], force=False, lvl=0):
    ''' adds/sets ACEs for user, contributor and admin roles.
         - force: update the ACL anyway even the given user is already in the role. 
    '''

    logger = getMyLogger(lvl=lvl)

    ## stop role setting if the same user id appears in multiple user lists
    common = list( set(users) & set(contributors) & set(admins) )

    if common:
        for u in common:
            logger.error('user %s presents in multiple roles.' % u)
        return False

    ulist = {ROLE_ADMIN      : admins,
             ROLE_CONTRIBUTOR: contributors,
             ROLE_USER       : users} 

    ## get the existing ACL
    o_aces = getACE(path, recursive=False, lvl=lvl)[path]

    if not force:
        ## check user roles in existing ACL to avoid redundant operations 
        for tp,flag,principle,permission in o_aces:
 
            u = principle.split('@')[0]
 
            if u not in ['GROUP','OWNER','EVERYONE'] and tp in ['A']:
                r = getRoleFromACE(permission, lvl=lvl)
                if u in ulist[r]:
                    logger.warning("skip redundant role setting: %s -> %s" % (u,r))
                    ulist[r].remove(u)

    ## if the entire user list is empty, just return true
    _ulist_a = users + contributors + admins
    if not _ulist_a:
        logger.warning("I have nothing to do!")
        return True
            
    ## compose new ACL based on the existing ACL 
    n_aces = []
    for a in o_aces:
        u = a[2].split('@')[0]
        if u not in _ulist_a:
            n_aces.append(':'.join(a))

    ## prepending ACEs related to the given user list
    opts  = ['-R', '-s']
    for k,v in ulist.iteritems():
        logger.info('setting %s permission ...' % k)
        _perm = get_permission(k)
        for u in v:
            n_aces.insert(0, 'A:fd:%s@dccn.nl:%s' % (u, _perm['A']))
            ## Do not need to set the DENY ACE's
            #n_aces.insert(0, 'D:fd:%s@dccn.nl:%s' % (u, _perm['D']))

    return __nfs4_setfacl__(path, n_aces, opts, lvl=lvl)

## internal functions
def __forceDefaultPrincipleACE__(aces):
    ''' return enforced ACEs for default principles, i.e. USER, GROUP and EVERYONE
         - make the ACEs always inherited, making Windows friendly
    '''

    ## compose new ACL based on the existing ACL
    n_aces = []
    for ace in aces:
        a = ace.split(':')
        u = a[2].split('@')[0]
        if u in ['GROUP','OWNER','EVERYONE']:
            ## to make it general: remove 'f' and 'd' bits and re-prepend them again
            a[1] = 'fd%s' % a[1].replace('f','').replace('d','')
        n_aces.append(':'.join(a))

    return n_aces

def __nfs4_setfacl__(fpath, aces, options=None, lvl=0):
    ''' wrapper for calling nfs4_setfacl command.
         - fpath  : the path the ACEs will be applied
         - aces   : the ACEs in a list of strings
         - options: the command-line options in a list of strings 
    '''
    logger = getMyLogger(lvl=lvl)

    aces = __forceDefaultPrincipleACE__(aces)

    logger.debug('***** new ACL to set *****')
    for a in aces:
        logger.debug(a)

    if options:
        cmd = 'nfs4_setfacl %s ' % ' '.join(options)
    else:
        cmd = 'nfs4_setfacl '

    ## workaround for NetApp for the path is actually the root of the volume
    if fpath[-1] is not '/':
        fpath += '/'

    ## check existance of the .setacl_lock file within the fpath
    lock_fpath = os.path.join( fpath, '.setacl_lock' )
    if os.path.exists( lock_fpath ):
        logger.error('cannot setacl as lock file \'%s\' has been acquired by other process' % lock_fpath)
        return False

    ## serialize client information in to the .setacl_lock file
    (time,ip,uid) = getClientInfo()
    f = open( lock_fpath, 'wb' )
    pickle.dump({'time':time,'ip':ip,'uid':uid,'aces':aces}, f)
    f.close()

    cmd += '"%s" %s' % ( ', '.join(aces), fpath )

    s   = Shell()
    rc, output, m = s.cmd1(cmd, allowed_exit=[0,255], timeout=None)
    if rc != 0:
        logger.error('%s failed' % cmd)

    ## cleanup lock file regardless the result
    try:
        os.remove(lock_fpath)
    except:
        pass

    return not rc
   
def __fs_walk_error__(err):
    ''' handles error if not able to perform listdir on a file.
    '''
    print 'cannot list file: %s' % err.filename

def __parseACLStr__(acl_str):
    ''' splits ACL into ACEs and parse each ACEs into a tuple of (type,flag,principle,permission) 
    '''
    acl = [] 
    for ace in acl_str.split('\n'):
        if ace:
            acl.append(ace.split(':'))

    return acl
