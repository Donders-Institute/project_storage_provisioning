#!/usr/bin/env python
import re

class ACE:
    '''object of the Access Control Entry, the main structure is inspired by NFSv4 ACE'''
    def __init__(self, **kwargs):
        self.type = ''
        self.flag = ''
        self.principle = ''
        self.mask = ''
        self.__dict__.update(kwargs)

    def isDefaultPrinciple(self):
        return re.match('^(OWNER|GROUP|EVERYONE)@', self.principle)

    def isFileInherited(self):
        return self.flag.find('f') >= 0

    def isDirectoryInherited(self):
        return self.flag.find('d') >= 0

    def __str__(self):
        return ':'.join([self.type, self.flag, self.principle, self.mask])

    def __str_no_inheritance__(self):
        return ':'.join([self.type, self.flag.replace('f','').replace('d',''), self.principle, self.mask])

    def __repr__(self):
        return repr(self.__dict__)
