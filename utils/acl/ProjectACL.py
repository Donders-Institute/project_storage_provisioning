#!/usr/bin/env python
from utils.acl.Logger import getLogger


class ProjectACL:

    def __init__(self, project_root, lvl=0):
        """
        constructs the object
        :param project_root: the path to the top-level directory of the project
        :param lvl: logging level
        :return:
        """

        self.type = None
        self.project_root = project_root
        self.logger = getLogger(name=self.__class__.__name__, lvl=lvl)

    def setRoles(self, path='', users=[], contributors=[], admins=[], recursive=True, force=False, traverse=False):
        """
        sets users to the roles: user, contributor, administrator
        :param path: the file system path relative to the project_root
        :param users: a list of user ids to be set for user role
        :param contributors: a list of user ids to be set for contributor role
        :param admins: a list of user ids to be set for administrator role
        :param force: force to set roles even the users are already in the target role
        :param recursive: True if the role setting is applied recursivly, otherwise False
        :param traverse: True if ensuring the uid has proper right to traverse through parent directories
        :return: True in success, otherwise False
        """
        raise NotImplementedError

    def getRoles(self, path='', recursive=False):
        """
        gets user roles of the given path.
        :param path: the file system path relative to the project_root
        :param recursive: get roles recursively for all sub-paths
        :return: a list of RoleData objects
        """
        raise NotImplementedError

    def delUsers(self, path='', users=[], recursive=True, force=False):
        """
        deletes specified users from accessing to the given path
        :param path: the file system path relative to the project_root
        :param users: a list of user ids
        :param recursive: True if the user deletion is applied recursively, otherwiser False
        :param force: force to delete users even the users are not presented in any roles
        :return: True in success, otherwise False
        """
        raise NotImplementedError

    def mapRoleToACE(self, role):
        """
        maps the given role to a file-system specific ACE object
        :param role: the role
        :return: the ACE object
        """
        raise NotImplementedError

    def mapACEtoRole(self, ACE):
        """
        maps the given ACE object to a Role
        :param ACE: the file-system specific ACE object
        :return: the role
        """
        raise NotImplementedError