#!/usr/bin/env python
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../external/lib/python')
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
from utils.acl.Nfs4ProjectACL import Nfs4ProjectACL


project_root = '/project/3010000.01'
lvl = 3
fs = Nfs4ProjectACL(project_root, lvl)

# get roles
roles = fs.getRoles()
for p, r in roles.iteritems():
    print 'path: %s' % p, r

# set roles
ick = fs.setRoles(users=['rendbru'])
ick = fs.setRoles(path='subject_001', contributors=['rendbru'])

# get roles for all sub-paths
roles = fs.getRoles(recursive=True)
for p, r in roles.iteritems():
    print 'path: %s' % p, r

# delete users
