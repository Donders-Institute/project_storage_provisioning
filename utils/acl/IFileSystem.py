#!/usr/bin/env python

class IFileSystem:

    def __init__(self):

        self.type = None

    def setRoles(self, path, users=[], contributors=[], administrators=[], recursive=False):
        '''
        sets users to the roles: user, contributor, administrator
        :param path: the file system path
        :param users: a list of user ids to be set for user role
        :param contributors: a list of user ids to be set for contributor role
        :param administrators: a list of user ids to be set for administrator role
        :param recursive: True if the role setting is applied recursivly, otherwise False
        :return: True in success, otherwise False
        '''
        raise NotImplementedError

    def getRoles(self, path, recursive=False):
        '''
        gets user roles of the given path.
        :param recursive: get roles recursively for all sub-paths
        :param path: the file system path
        :return: a dictionary with keys referring to the three roles: user, contributor, administrator
        '''
        raise NotImplementedError

    def delUser(self, path, uids):
        '''
        deletes specified users from accessing to the given path
        :param path: the file system path
        :param uids: a list of user ids
        :return: True in success, otherwise False
        '''
        raise NotImplementedError

    def mapRoleToACE(self, role):
        '''
        maps the given role to a file-system specific ACE object
        :param role: the role
        :return: the ACE object
        '''
        raise NotImplementedError

    def mapACEtoRole(self, ACE):
        '''
        maps the given ACE object to a Role
        :param ACE: the file-system specific ACE object
        :return: the role
        '''
        raise NotImplementedError