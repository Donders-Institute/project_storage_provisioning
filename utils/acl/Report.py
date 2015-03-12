#!/usr/bin/env python
import sys
import os

## loading PrettyTable for table output
from utils.acl.UserRole import PROJECT_ROLES
from prettytable import PrettyTable

def printRoleTable(roles):
    ''' display project roles in prettytable
    '''

    t = PrettyTable()
    t.field_names = ['project', 'path'] + PROJECT_ROLES

    for pid, rd_list in roles.iteritems():
        for rd in rd_list:
            data = [pid, rd.path]
            for k in PROJECT_ROLES:
                if rd[k]:
                    data.append(','.join(rd[k]))
                else:
                    data.append('N/A')
            t.add_row(data)

    t.sortby = 'project'
    print t
