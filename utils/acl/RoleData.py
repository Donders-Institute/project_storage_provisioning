#!/usr/bin/env python
from utils.acl.UserRole import PROJECT_ROLES


class RoleData:
    """
    RoleData object that contains user roles associated with a file system path.
    """
    def __init__(self, **kwargs):
        self.path = ''
        self.__dict__.update(kwargs)

        for r in PROJECT_ROLES:
            self.__dict__[r] = []

    def addUserToRole(self, role, user):
        """
        adds user to a role
        :param role: the role
        :param user: the user id
        :return:
        """
        if role not in self.__dict__.keys():
            self.__dict__[role] = []

        if user not in self.__dict__[role]:
            self.__dict__[role].append(user)

    def removeUserFromRole(self, role, user):
        """
        removes user from a role
        :param role: the role
        :param user: the user id
        :return:
        """
        if role in self.__dict__.keys() and user in self.__dict__[role]:
            self.__dict__[role].remove(user)

    def __repr__(self):
        return repr(self.__dict__)