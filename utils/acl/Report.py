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

    for pid, rdata in roles.iteritems():
        for p, r in rdata.iteritems():
            data = [pid, p]
            for k in PROJECT_ROLES:
                if r[k]:
                    data.append(','.join(r[k]))
                else:
                    data.append('N/A')
            t.add_row(data)

    t.sortby = 'project'
    print t
