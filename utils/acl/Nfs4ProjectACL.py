#!/usr/bin/env python
import os
import pickle
import pwd
import datetime
import socket
import re
import time
from utils.acl.RoleData import RoleData
from utils.acl.ACE import ACE
from utils.acl.ProjectACL import ProjectACL
from utils.Shell import Shell
from utils.acl.UserRole import ROLE_ADMIN, ROLE_CONTRIBUTOR, ROLE_TRAVERSE, ROLE_USER

class Nfs4ProjectACL(ProjectACL):

    def __init__(self, project_root, lvl=0):
        ProjectACL.__init__(self, project_root, lvl)
        self.type = 'NFS4'

        self.ROLE_PERMISSION = {ROLE_ADMIN: 'RXWdDoy',
                                ROLE_CONTRIBUTOR: 'rwaDdxnNtTcy',
                                ROLE_USER: 'RXy',
                                ROLE_TRAVERSE: 'x'}

        self.all_permission = 'rwaDdxnNtTcCoy'

        self._alias_ = {'R': 'rntcy',
                        'W': 'watTNcCy',
                        'X': 'xtcy'}

        self.default_principles = ['GROUP', 'OWNER', 'EVERYONE']

    def getRoles(self, path='', recursive=False):

        path = os.path.join(self.project_root, path)

        def __fs_walk_error__(err):
            print 'cannot list file: %s' % err.filename

        # make system call to retrieve NFSV4 ACL
        acl = {}
        if recursive:
            # walk through all directories/files under the path
            for r, ds, fs in os.walk(path, onerror=__fs_walk_error__):
                # retrieve directory ACL
                acl[r] = self.__nfs4_getfacl__(r)

                # retrieve file ACL
                for f in map(lambda x: os.path.join(r, x), fs):
                    acl[f] = self.__nfs4_getfacl__(f)
        else:
            acl[path] = self.__nfs4_getfacl__(path)

        # convert NFSV4 ACL into roles
        roles = []
        for p, aces in acl.iteritems():

            rdata = RoleData(path=p)

            for ace in aces:
                # exclude the default principles
                u = ace.principle.split('@')[0]
                if u not in self.default_principles and ace.type in ['A']:
                    r = self.mapACEtoRole(ace)
                    rdata.addUserToRole(r, u)
                    self.logger.debug('user %s: permission %s, role %s' % (u, ace.mask, r))

            roles.append(rdata)

        return roles

    def mapRoleToACE(self, role):
        pass

    def setRoles(self, path='', users=[], contributors=[], admins=[], recursive=True, force=False, traverse=False,
                 logical=False):

        path = os.path.join(self.project_root, path)

        # stop role setting if the same user id appears in multiple user lists
        common = list( set(users) & set(contributors) & set(admins) )

        if common:
            for u in common:
                self.logger.error('user %s presents in multiple roles.' % u)
            return False

        ulist = {ROLE_ADMIN: admins,
                 ROLE_CONTRIBUTOR: contributors,
                 ROLE_USER: users,
                 ROLE_TRAVERSE: []}

        # get current ACEs on the path
        o_aces = self.__nfs4_getfacl__(path)

        if not force:
            # check user roles in existing ACL to avoid redundant operations
            for ace in o_aces:

                u = ace.principle.split('@')[0]

                if u not in self.default_principles and ace.type in ['A']:
                    r = self.mapACEtoRole(ace)
                    if u in ulist[r]:
                        self.logger.warning("skip redundant role setting: %s -> %s" % (u,r))
                        ulist[r].remove(u)

        # if the entire user list is empty, just return true
        _ulist_a = users + contributors + admins
        if not _ulist_a:
            self.logger.warning("I have nothing to do!")
            return True

        # set traverse on upper-level directories
        if traverse:
            # resolve the starting directory for traverse
            tpath = os.path.split(os.path.relpath(path, self.project_root))[0]
            if not self.__set_traverse_role__(tpath, _ulist_a):
                return False

        # compose new ACL based on the existing ACL
        n_aces = []
        for ace in o_aces:
            u = ace.principle.split('@')[0]
            if u not in _ulist_a:
                n_aces.append(ace)

        # prepending ACEs related to the given user list
        for k, v in ulist.iteritems():
            self.logger.info('setting %s permission ...' % k)
            _perm = self.__get_permission__(k)
            for u in v:
                n_aces.insert(0, ACE(type='A', flag='fd', principle='%s@dccn.nl' % u, mask='%s' % _perm['A']))

        # command-line options for nfs4_setfacl
        _opts = ['-s']
        if recursive:
            _opts.insert(0, '-R')

        if logical:
            _opts.insert(0, '-L')

        return self.__nfs4_setfacl__(path, n_aces, _opts)

    def delUsers(self, path='', users=[], recursive=True, force=False, logical=False):

        path = os.path.join(self.project_root, path)

        # get current ACEs on the path
        o_aces = self.__nfs4_getfacl__(path)

        if not force:
            # check users in existing ACL to avoid redundant operations
            _u_exist = []
            for ace in o_aces:
                u = ace.principle.split('@')[0]
                if u not in _u_exist + self.default_principles:
                    _u_exist.append(u)

            # resolve the users requiring actual removal of ACEs
            _u_remove = list( set(users) & set(_u_exist) )
            for u in users:
                if u not in _u_remove:
                    self.logger.warning('ignore user not presented in ACL: %s' % u)

            users = _u_remove

        # simply return with True if no user for ACE removal
        if not users:
            self.logger.warning("I have nothing to do!")
            return True

        # compose new ACL regarding the removal
        n_aces = []
        for ace in o_aces:
            u = ace.principle.split('@')[0]
            if u not in users:
                n_aces.append(ace)
            else:
                self.logger.info('deleting ACEs of user: %s' % u)

        # command-line options for nfs4_setfacl
        _opts = ['-s']
        if recursive:
            _opts.insert(0, '-R')

        if logical:
            _opts.insert(0, '-L')

        return self.__nfs4_setfacl__(path, n_aces, _opts)

    def mapACEtoRole(self, ace):
        diff = {}
        for r in self.ROLE_PERMISSION.keys():
            diff[r] = list(set(list(ace.mask)) ^ set(list(self.__get_permission__(r)['A'])))
            self.logger.debug('diff to role %s: %s' % (r, repr(diff[r])))

        # find the closest match, i.e. shortest string on the value of the diff dict
        return sorted(diff.items(), key=lambda x: len(x[1]))[0][0]

    # internal functions
    def __set_traverse_role__(self, path, users):
        """
        sets traverse role of given users on path and upwards to project_root.
        :param path: the file system path under project_root
        :param users: a list of user ids
        :return: True if success, otherwiser False
        """

        path = os.path.join(self.project_root, path)

        ick = True
        while path != os.path.split(self.project_root)[0]:

            self.logger.debug('setting traverse role on %s' % path)
            # get current ACEs on the path
            o_aces = self.__nfs4_getfacl__(path)
            n_aces = [] + o_aces

            # consider users that needs to be added to the ACL for traverse role
            # we assume the user has already the traverse permission if it is already in ACL
            for u in users:
                if u not in map(lambda x: x.principle.split('@')[0], o_aces):
                    self.logger.debug("adding user to traverse role: %s" % u)
                    _perm = self.__get_permission__(ROLE_TRAVERSE)
                    n_aces.insert(0, ACE(type='A', flag='fd', principle='%s@dccn.nl' % u, mask=_perm['A']))

            # apply n_aces
            _opts = ['-s']
            ick = self.__nfs4_setfacl__(path, n_aces, _opts)

            if not ick:
                self.logger.error('setting ACL for traverse role failed: %s' % path)
                break
            else:
                # go on level upward on the directory tree
                path = os.path.dirname(re.sub('/*$', '', path))

        return ick

    def __get_permission__(self, role):
        """
        gets ACE's permission mask for DENY and ALLOW types wrt the given role
        :param role: the role
        :return: an permission mask dictionary with keys 'A' and 'D' corresponding to the ALLOW and DENY types
        """

        ace = {}
        try:
            _ace_a = self.ROLE_PERMISSION[role]

            for k, v in self._alias_.iteritems():
                _ace_a = _ace_a.replace(k, v)

            _ace_a = ''.join(list(set(list(_ace_a))))
            _ace_d = ''.join(list(set(list(self.all_permission)) - set(list(_ace_a))))

            ace['A'] = _ace_a
            ace['D'] = _ace_d

        except KeyError, e:
            self.logger.error('No such role: %s' % role)

        return ace

    def __nfs4_getfacl__(self, path):

        self.logger.debug('get ACL of %s ...' % path)

        def __parseACL__(acl_str):
            """ parses ACL table into ACE objects
            """
            acl = []
            for ace in acl_str.split('\n'):
                if ace:
                    d = ace.split(':')
                    acl.append(ACE(type=d[0], flag=d[1], principle=d[2], mask=d[3]))
            return acl

        # workaround for NetApp for the path is actually the root of the volume
        if os.path.isdir(path) and path[-1] is not '/':
            path += '/'

        cmd = 'nfs4_getfacl %s' % path
        s = Shell()
        rc, output, m = s.cmd1(cmd, allowed_exit=[0, 255], timeout=None)
        if rc != 0:
            self.logger.error('%s failed' % cmd)
            return []
        else:
            return __parseACL__(output)

    def __userExist__(self, uid):
        """
        checks if given user id is existing as a valid system user id

        :param uid: the system user id
        :return: True if the uid is valid, otherwise False
        """

        ick = False
        try:
            pwd.getpwnam(uid)
            ick = True
        except KeyError, e:
            pass
        return ick

    def __curateACE__(self, aces):
        """
        curate given ACEs with the following things:
             - make the ACEs for USER, GROUP and EVERYONE always inherited, making Windows friendly
             - remove ACEs associated with an invalid system account
        :param aces: a list of ACE objects to be scan through
        :return: a list of curated ACE objects
        """

        n_aces = []
        for ace in aces:
            u = ace.principle.split('@')[0]
            if u in self.default_principles:
                # to make it general: remove 'f' and 'd' bits and re-prepend them again
                ace.flag = 'fd%s' % ace.flag.replace('f', '').replace('d', '')
                n_aces.append(ace)
            elif self.__userExist__(u):
                n_aces.append(ace)
            else:
                self.logger.warning('ignore ACE for invalid user: %s' % u)

        return n_aces

    def __nfs4_setfacl__(self, path, aces, options=None):
        """
        wrapper for calling nfs4_setfacl command.
        :param path: the path on which the given ACEs will be applied
        :param aces: a list of ACE objects
        :param options: command-line options for nfs4_setfacl command
        :return: True if the operation succeed, otherwiser False
        """

        aces = self.__curateACE__(aces)

        self.logger.debug('***** new ACL to set *****')
        for a in aces:
            self.logger.debug(a)

        if options:
            cmd = 'nfs4_setfacl %s ' % ' '.join(options)
        else:
            cmd = 'nfs4_setfacl '

        # workaround for NetApp for the path is actually the root of the volume
        if os.path.isdir(path) and path[-1] is not '/':
            path += '/'

        # check existance of the .setacl_lock file in the project's top directory
        lock_fpath = os.path.join(self.project_root, '.setacl_lock')
        if os.path.exists(lock_fpath):
            self.logger.error('cannot setacl as lock file \'%s\' has been acquired by other process' % lock_fpath)
            return False

        # serialize client information in to the .setacl_lock file
        f = open(lock_fpath, 'wb')
        pickle.dump({'time': datetime.datetime.now(),
                     'ip': socket.gethostbyname(socket.gethostname()),
                     'uid': os.getlogin(),
                     'aces': aces}, f)
        f.close()

        cmd += '"%s" %s' % (', '.join(map(lambda x: x.__str__(), aces)), path)

        s = Shell()
        rc, outfile, m = s.cmd(cmd, timeout=None, mention_outputfile_on_errors=True)
        if rc != 0:
            self.logger.error('%s failed' % cmd)
        else:
            os.unlink(outfile)

        # cleanup lock file regardless the result
        try:
            os.remove(lock_fpath)

            # backup the lock file for debug purpose
            #lock_fpath_bak = '%s.%s' % (lock_fpath, time.ctime())
            #os.rename(lock_fpath, lock_fpath_bak)
        except:
            pass

        return not rc

