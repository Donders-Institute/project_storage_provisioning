#!/usr/bin/env python
import os
import pickle
import pwd
import datetime
import socket
import re
import inspect
import grp 
from tempfile import NamedTemporaryFile
from utils.acl.RoleData import RoleData
from utils.acl.ACE import ACE
from utils.acl.Nfs4NetApp import Nfs4NetApp
from utils.Shell import Shell
from utils.acl.UserRole import ROLE_ADMIN, ROLE_CONTRIBUTOR, ROLE_TRAVERSE, ROLE_USER

class Nfs4FreeNAS(Nfs4NetApp):

    def __init__(self, project_root, lvl=0):
        Nfs4NetApp.__init__(self, project_root, lvl)

    def setRoles(self, path='', users=[], contributors=[], admins=[], recursive=False, force=False, traverse=False,
                 logical=False, batch=False):

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

                    # indicate group principle, except the the default GROUP@ identity 
                    if ace.flag.lower().find('g') >= 0:
                        u = 'g:%s' % u

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
        n_aces_grp = []
        for ace in o_aces:
            u = ace.principle.split('@')[0]

            # indicate group principle, except the the default GROUP@ identity
            if ace.flag.lower().find('g') >= 0 and u not in self.default_principles:
                u = 'g:%s' % u
                if u not in _ulist_a:
                    n_aces_grp.append(ace)
            else:
                if u not in _ulist_a:
                    n_aces.append(ace)

        # prepending ACEs related to the given user list
        for k, v in ulist.iteritems():
            self.logger.info('setting %s permission ...' % k)
            _perm = self.__get_permission__(k)
            for u in v:
                if u.find('g:') == 0: 
                    n_aces_grp.insert(0, ACE(type='A', flag='dg', principle='%s@dccn.nl' % re.sub(r'^g:', '', u), mask='%s' % _perm['A']))
                    n_aces_grp.insert(0, ACE(type='A', flag='fg', principle='%s@dccn.nl' % re.sub(r'^g:', '', u), mask='%s' % _perm['A'].replace('x','')))
                else:
                    n_aces.insert(0, ACE(type='A', flag='d', principle='%s@dccn.nl' % u, mask='%s' % _perm['A']))
                    n_aces.insert(0, ACE(type='A', flag='f', principle='%s@dccn.nl' % u, mask='%s' % _perm['A'].replace('x','')))

        # merge user and group ACEs (Group ACEs are on top of user ACEs)
        n_aces = n_aces_grp + n_aces

        # command-line options for nfs4_setfacl
        _opts = ['-s']
        if recursive:
            _opts.insert(0, '-R')

        if logical:
            _opts.insert(0, '-L')

        if batch:
            return self.__nfs4_setfacl_qsub__(path, n_aces, _opts)
        else:
            return self.__nfs4_setfacl__(path, n_aces, _opts)

    def delUsers(self, path='', users=[], recursive=False, force=False, logical=False, batch=False):

        path = os.path.join(self.project_root, path)

        # get current ACEs on the path
        o_aces = self.__nfs4_getfacl__(path)

        if not force:
            # check users in existing ACL to avoid redundant operations
            _u_exist = []
            for ace in o_aces:
                u = 'g:%s' % ace.principle.split('@')[0] if ace.flag.lower().find('g') >= 0 else ace.principle.split('@')[0]
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
            u = 'g:%s' % ace.principle.split('@')[0] if ace.flag.lower().find('g') >= 0 else ace.principle.split('@')[0]
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

        if batch:
            return self.__nfs4_setfacl_qsub__(path, n_aces, _opts)
        else:
            return self.__nfs4_setfacl__(path, n_aces, _opts)

    # internal functions
    def __curateACE__(self, aces):
        """
        curate given ACEs with the following things:
             - make the ACEs for USER, GROUP and EVERYONE not inherited
             - remove ACEs associated with an invalid system account
        :param aces: a list of ACE objects to be scan through
        :return: a list of curated ACE objects
        """

        n_aces = []
        for ace in aces:
            u = ace.principle.split('@')[0]
            if u in self.default_principles:
                # to make it general: remove 'f' and 'd' bits and re-prepend them again
                ace.flag = '%s' % ace.flag.replace('f', '').replace('d', '')
                n_aces.append(ace)
            elif self.__userExist__(u):
                n_aces.append(ace)
            elif ace.flag.lower().find('g') >= 0 and self.__groupExist__(u):
                n_aces.append(ace)
            else:
                self.logger.warning('ignore ACE for invalid user: %s' % u)

        return n_aces
    def __nfs4_setfacl_qsub__(self, path, aces, options=None, queue='batch'):
        raise NotImplementedError

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

        recursive = False

        if options:
            if '-R' in options:
                recursive = True
                options.remove('-R')
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
        try:
            f = open(lock_fpath, 'wb')
        except IOError as e:
            self.logger.error('cannot create lock file %s: %s' % (lock_fpath, repr(e)))
            return False

        pickle.dump({'time': datetime.datetime.now(),
                     'ip': socket.gethostbyname(socket.gethostname()),
                     'uid': os.getlogin(),
                     'aces': aces}, f)
        f.close()

        s = Shell()

        rc = 0
        if recursive and os.path.isdir(path):

            # compose setacl command for directory ACEs
            cmd_d = '%s "%s" ' % (cmd, ','.join(map(lambda x: x.__str__(), aces)))
            # compose setacl command for file ACEs
            # get ACEs with principle domain @dccn.nl; but without 'd' inherit flag
            aces_f = filter( lambda x: not x.isDefaultPrinciple() and not x.isDirectoryInherited(), aces )

            # execute multiple nfs4_setfacl command, iteratively
            for (dirPath, dirNames, fileNames) in os.walk(path):
                # on dir
                _cmd = '%s "%s"' % (cmd_d, dirPath)
                rc, outfile, m = s.cmd(_cmd, timeout=None, mention_outputfile_on_errors=True)
                if rc != 0:
                    self.logger.error('%s failed' % _cmd)
                    break
                else:
                    os.unlink(outfile)

                # on files
                ick = True
                for f in fileNames:
                    fpath = os.path.join(dirPath, f)
                    # combine the existing default ACEs (i.e. ACEs without pricinple domain)
                    aces_d = filter( lambda x:x.isDefaultPrinciple(), self.__nfs4_getfacl__(fpath))
                    _cmd = '%s "%s" "%s"' % (cmd, ','.join(map(lambda x: x.__str_no_inheritance__(), aces_f + aces_d)), fpath)
                    rc, outfile, m = s.cmd(_cmd, timeout=None, mention_outputfile_on_errors=True)
                    if rc != 0:
                        self.logger.error('%s failed' % _cmd)
                        ick = False
                        break
                    else:
                        os.unlink(outfile)

                # leave the main loop if something goes wrong
                if not ick:
                    break
        else:
            # execute single nfs4_setfacl command
            if os.path.isdir(path):
                cmd += '"%s" "%s"' % (','.join(map(lambda x: x.__str__(), aces)), path)
            else:
                cmd += '"%s" "%s"' % (','.join(map(lambda x: x.__str_no_inherit__(), aces)), path)

            rc, outfile, m = s.cmd(cmd, timeout=None, mention_outputfile_on_errors=True)
            if rc != 0:
                self.logger.error('%s failed' % cmd)
            else:
                os.unlink(outfile)
         
        # cleanup lock file regardless the result
        try:
            os.remove(lock_fpath)
        except:
            pass

        return not rc
