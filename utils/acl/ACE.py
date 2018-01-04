#!/usr/bin/env python

class ACE:
    '''object of the Access Control Entry, the main structure is inspired by NFSv4 ACE'''
    def __init__(self, **kwargs):
        self.type = ''
        self.flag = ''
        self.principle = ''
        self.mask = ''
        self.__dict__.update(kwargs)

    def __str__(self):
        return ':'.join([self.type, self.flag, self.principle, self.mask])

    def __str_no_inherit__(self):
        return ':'.join([self.type, self.flag.replace('f','').replace('d',''), self.principle, self.mask])

    def __repr__(self):
        return repr(self.__dict__)
