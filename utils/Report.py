#!/usr/bin/env python
import sys
import os
from utils.ACL    import ROLE_PERMISSION

## loading PrettyTable for table output 
from prettytable import PrettyTable

def printRoleTable(roles):
    ''' display project roles in prettytable
    '''
    r_keys = ROLE_PERMISSION.keys()

    t = PrettyTable()
    t.field_names = ['project', 'subdir'] + r_keys

    for p,r in roles.iteritems():
        data = []
        data.append(p)
        data.append(r['subdir'])
        for k in r_keys:
            if r[k]:
                data.append(','.join(r[k]))
            else:
                data.append('N/A')
        t.add_row(data)

    t.sortby = 'project'
    print t
