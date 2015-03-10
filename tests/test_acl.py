#!/usr/bin/env python
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../external/lib/python')
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'../')
from utils.acl.INFS4 import INFS4

fs = INFS4

# get roles
path = '/project/3010000.01'
roles = fs.getRoles(path)
print roles[path]
