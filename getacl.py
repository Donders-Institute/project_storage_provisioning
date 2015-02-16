#!/bin/env python
import sys
import os 
from argparse import ArgumentParser

## adding PYTHONPATH for access to utility modules and 3rd-party libraries
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/external/lib/python')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.ACL    import getACE, getRoleFromACE, ROLE_PERMISSION
from utils.Common import getConfig, getMyLogger
from utils.Report import printRoleTable
from utils.IProjectDB import getDBConnectInfo,updateProjectDatabase

## execute the main program
if __name__ == "__main__":

    ## load configuration file
    cfg  = getConfig( os.path.dirname(os.path.abspath(__file__)) + '/etc/config.ini' )

    parg = ArgumentParser(description='gets access rights of project storages', version="0.1")

    ## positional arguments
    parg.add_argument('pid',
                      metavar = 'pid',
                      nargs   = '*',
                      help    = 'the project id')

    ## optional arguments
    parg.add_argument('-l','--loglevel',
                      action  = 'store',
                      dest    = 'verbose',
                      type    = int,
                      choices = [0, 1, 2, 3],
                      default = 0,
                      help    = 'set one of the following verbosity levels. 0|default:WARNING, 1:ERROR, 2:INFO, 3:DEBUG')

    parg.add_argument('-d','--basedir',
                      action  = 'store',
                      dest    = 'basedir',
                      default = cfg.get('PPS','PROJECT_BASEDIR'),
                      help    = 'set the basedir in which the project storages are located')

    parg.add_argument('-p','--subdir',
                      action  = 'store',
                      dest    = 'subdir',
                      default = '',
                      help    = 'specify the sub-directory in the project from which the role setting is retrieved')

    args = parg.parse_args()

    logger = getMyLogger(name=__file__, lvl=args.verbose)

    if not args.pid:
        args.pid = os.listdir(args.basedir)

    roles = {}
    for id in args.pid:
        p = os.path.join(args.basedir, id)

        if args.subdir:
            # if args.basedir has leading ppath, substitute it with empty string
            p = os.path.join(p, re.sub(r'^%s/' % p, '', args.subdir))

        ## create empty role dict for the project
        roles[id] = {}
        for r in ROLE_PERMISSION.keys():
            roles[id][r] = []

        ## get ACL
        aces = getACE(p, recursive=False, lvl=args.verbose)

        if aces[p]:
            for tp,flag,principle,permission in aces[p]:

                ## exclude the default principles 
                u = principle.split('@')[0]
 
                if u not in ['GROUP','OWNER','EVERYONE'] and tp in ['A']:
                    r = getRoleFromACE(permission, lvl=args.verbose)
                    roles[id][r].append(u)
                    logger.debug('user %s: permission %s, role %s' % (u, permission,r))

    ## printing or updating project DB database
    printRoleTable(roles)
