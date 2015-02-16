#!/usr/bin/env python
import pickle
import pprint

from utils.Shell  import *
from utils.Common import getMyLogger, getClientInfo


ROLE_ADMIN       = 'admin'
ROLE_CONTRIBUTOR = 'contributor'
ROLE_USER        = 'user'

ROLE_PERMISSION  = { ROLE_ADMIN       : 'RXWdDoy',
                     ROLE_CONTRIBUTOR : 'rwaDdxnNtTcy',
                     ROLE_USER        : 'RXy' }

class ProjectRole:
    '''object for project role'''
    def __init__(self, **kwargs):
        self.uid    = None
        self.pid    = None
        self.role   = None
        self.__dict__.update(kwargs)

    def getACE(self):
        '''convert role into ACE string for accepted filesystem operations.
        '''
        all_permission = 'rwaDdxnNtTcCoy'

        _alias_ = { 'R': 'rntcy',
                    'W': 'watTNcCy',
                    'X': 'xtcy' }

        ace = {}
        try:
            _ace_a = ROLE_PERMISSION[self.role]

            for k,v in _alias_.iteritems():
                _ace_a = _ace_a.replace(k, v)

            _ace_a = ''.join( list( set(list(_ace_a)) ) )
            _ace_d = ''.join( list( set(list(all_permission)) - set(list(_ace_a)) ) )

            ace['A'] = _ace_a
            ace['D'] = _ace_d

        except KeyError,e:
            logger.error('No such role: %s' % self.role)

        return ace

    def __str__(self):
        return pprint.pformat(self.__dict__)

    def __repr__(self):
        return repr(self.__dict__)

    def __eq__(self, other):
        '''action is considered identical if matching uid and pid
           when identical action is found, conflict is resolved
           by taking into account the action with later creation time.
        '''
        if not isinstance(other, ProjectRole):
            raise NotImplementedError
        return self.uid == other.uid and self.pid == other.pid
   
def get_permission(role):
    ''' gets permission bits for DENY and ALLOW, given the role
    '''
    all_permission = 'rwaDdxnNtTcCoy'

    _alias_ = { 'R': 'rntcy',
                'W': 'watTNcCy',
                'X': 'xtcy' }
 
    ace = {}
    try:
        _ace_a = ROLE_PERMISSION[role]

        for k,v in _alias_.iteritems():
            _ace_a = _ace_a.replace(k, v)

        _ace_a = ''.join( list( set(list(_ace_a)) ) )
        _ace_d = ''.join( list( set(list(all_permission)) - set(list(_ace_a)) ) )

        ace['A'] = _ace_a
        ace['D'] = _ace_d

    except KeyError,e:
        logger.error('No such role: %s' % role)

    return ace

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

def delACE(fpath, ppath, users, force=False, lvl=0):
    ''' deletes all ACEs related to the given list of users.
         - force: update the ACL anyway even the given user is not in ACL.
    '''

    logger = getMyLogger(lvl=lvl)

    ## get the existing ACL
    o_aces = getACE(fpath, recursive=False, lvl=lvl)[fpath]

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

    return __nfs4_setfacl__(fpath, ppath, n_aces, _opts, lvl=lvl)

def getACE(path, user=None, recursive=False, lvl=0):
    ''' gets ACEs for given user or for all ACEs if user is not given. 
    '''

    logger = getMyLogger(lvl=lvl)

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

# def setDefaultPrincipleACE(path, lvl=0):
#     ''' sets initial / default ACEs for default principles: USER, GROUP and EVERYONE
#     '''
#     logger = getMyLogger(lvl=lvl)
#
#     ## get the existing ACL
#     aces = getACE(path, recursive=False, lvl=lvl)[path]
#
#     ## compose new ACL based on the existing ACL
#     n_aces = []
#     for a in aces:
#         u = a[2].split('@')[0]
#         if u in ['GROUP','OWNER','EVERYONE']:
#             ## to make it general: remove 'f' and 'd' bits and re-prepend them again
#             a[1] = 'fd%s' % a[1].replace('f','').replace('d','')
#
#         n_aces.append(':'.join(a))
#
#     opts  = ['-R', '-s']
#     return __nfs4_setfacl__(path, '', n_aces, opts, lvl=lvl)

def setACE(fpath, ppath, users=[], contributors=[], admins=[], force=False, lvl=0):
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
    o_aces = getACE(fpath, recursive=False, lvl=lvl)[fpath]

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

    return __nfs4_setfacl__(fpath, ppath, n_aces, opts, lvl=lvl)

## internal functions
def __curateACE__(aces, lvl=0):
    ''' curate given ACEs with the following things:
         - make the ACEs for USER,GROUP and EVERYONE always inherited, making Windows friendly
         - remove ACEs associated with an invalid system account
    '''

    logger = getMyLogger(lvl=lvl)

    ## compose new ACL based on the existing ACL
    n_aces = []
    for ace in aces:
        a = ace.split(':')
        u = a[2].split('@')[0]
        if u in ['GROUP','OWNER','EVERYONE']:
            ## to make it general: remove 'f' and 'd' bits and re-prepend them again
            a[1] = 'fd%s' % a[1].replace('f','').replace('d','')
            n_aces.append(':'.join(a))
        elif userExist(u):
            n_aces.append(':'.join(a))
        else:
            logger.warning('ignore ACE for invalid user: %s' % u)

    return n_aces

def __nfs4_setfacl__(fpath, ppath, aces, options=None, lvl=0):
    ''' wrapper for calling nfs4_setfacl command.
         - fpath  : the path the ACEs will be applied
         - ppath  : the path of the project's top-level directory
         - aces   : the ACEs in a list of strings
         - options: the command-line options in a list of strings
    '''
    logger = getMyLogger(lvl=lvl)

    aces = __curateACE__(aces, lvl=lvl)

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

    # check existance of the .setacl_lock file within the ppath
    # The lock should always be in the project's top directory
    lock_fpath = os.path.join( ppath, '.setacl_lock' )
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
