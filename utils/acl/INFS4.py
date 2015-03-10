#!/usr/bin/env python
import os
from utils.acl.ACE import ACE
from utils.acl.IFileSystem import IFileSystem
from utils.Shell import Shell
from utils.acl.UserRole import ROLE_ADMIN, ROLE_CONTRIBUTOR, ROLE_TRAVERSE, ROLE_USER
from utils.acl.Logger import getLogger


class INFS4(IFileSystem):

    def __init__(self):
        super(INFS4, self).__init__()
        self.type = 'NFS4'
        self.logger = getLogger()

        self.ROLE_PERMISSION = {ROLE_ADMIN: 'RXWdDoy',
                                ROLE_CONTRIBUTOR: 'rwaDdxnNtTcy',
                                ROLE_USER: 'RXy',
                                ROLE_TRAVERSE: 'x'}

        self.all_permission = 'rwaDdxnNtTcCoy'

        self._alias_ = {'R': 'rntcy',
                        'W': 'watTNcCy',
                        'X': 'xtcy'}

    def getRoles(self, path, recursive=False):

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
        roles = {}
        for p, aces in acl.iteritems():

            # initialize role_data for the path 'p'
            r_data = {}
            for r in self.ROLE_PERMISSION.keys():
                r_data[r] = []

            for ace in aces:
                # exclude the default principles
                u = ace.principle.split('@')[0]
                if u not in ['GROUP', 'OWNER', 'EVERYONE'] and ace.type in ['A']:
                    r = self.mapACEtoRole(ace)
                    r_data[r].append(u)
                    self.logger.debug('user %s: permission %s, role %s' % (u, ace.mask, r))

            roles[p] = r_data

        return roles

    def mapRoleToACE(self, role):
        pass

    def setRoles(self, path, users=[], contributors=[], administrators=[], recursive=False):
        pass

    def delUser(self, path, uids):
        pass

    def mapACEtoRole(self, ace):
        diff = {}
        for r in [ROLE_ADMIN, ROLE_CONTRIBUTOR, ROLE_USER, ROLE_TRAVERSE]:
            diff[r] = list(set(list(ace.mask)) ^ set(list(self.__get_permission__(r)['A'])))
            self.logger.debug('diff to role %s: %s' % (r, repr(diff[r])))

        # find the closest match, i.e. shortest string on the value of the diff dict
        return sorted(diff.items(), key=lambda x: len(x[1]))[0][0]

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

    def __nfs4_getfacl__(self, fpath):

        self.logger.debug('get ACL of %s ...' % fpath)

        def __parseACLStr__(acl_str):
            """ splits ACL into ACEs and parse each ACEs into a tuple of (type,flag,principle,permission)
            """
            acl = []
            for ace in acl_str.split('\n'):
                if ace:
                    d = ace.split(':')
                    acl.append(ACE(type=d[0], flag=d[1], principle=d[2], mask=d[3]))
            return acl

        # workaround for NetApp for the path is actually the root of the volume
        if os.path.isdir(fpath) and fpath[-1] is not '/':
            fpath += '/'

        cmd = 'nfs4_getfacl %s' % fpath
        s = Shell()
        rc, output, m = s.cmd1(cmd, allowed_exit=[0, 255], timeout=None)
        if rc != 0:
            self.logger.error('%s failed' % cmd)
            return None
        else:
            return __parseACLStr__(output)