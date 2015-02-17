#!/bin/env python
import sys
import os
import glob
from argparse import ArgumentParser

## adding PYTHONPATH for access to utility modules and 3rd-party libraries
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/external/lib/python')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.ACL    import getACE, getRoleFromACE, ROLE_PERMISSION
from utils.Common import getConfig, getMyLogger
from utils.Report import printRoleTableMultipath

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

    parg.add_argument('-p','--path',
                      action  = 'store',
                      dest    = 'subdir',
                      default = '',
                      help    = 'specify the relative/absolute path to a sub-directory from which the user role is retrieved')

    args = parg.parse_args()

    logger = getMyLogger(name=os.path.basename(__file__), lvl=args.verbose)

    if not args.pid:
        args.pid = os.listdir(args.basedir)

    roles = {}
    for id in args.pid:
        p = os.path.join(args.basedir, id)

        plist = []

        if args.subdir:
            # if args.basedir has leading ppath, substitute it with empty string
            # also accpet shell-style wildcard specification
            wc = os.path.join(p, re.sub(r'^%s/' % p, '', args.subdir))
            for pp in glob.glob(wc):
                plist.append(pp)

            if not plist:
                logger.error('path not found: %s' % wc)
                continue
        else:
            plist.append(p)

        # if not os.path.exists(p):
        #     # if path not found, throw an error and continue with the next project
        #     logger.error('path not found: %s' % p)
        #     continue

        ## create empty role dict for the project
        roles[id] = []

        for pp in plist:
            r_data = {'path': pp}

            for r in ROLE_PERMISSION.keys():
                r_data[r] = []

            ## get ACL
            aces = getACE(pp, recursive=False, lvl=args.verbose)

            if aces[pp]:
                for tp,flag,principle,permission in aces[pp]:

                    ## exclude the default principles
                    u = principle.split('@')[0]

                    if u not in ['GROUP','OWNER','EVERYONE'] and tp in ['A']:
                        r = getRoleFromACE(permission, lvl=args.verbose)
                        r_data[r].append(u)
                        logger.debug('user %s: permission %s, role %s' % (u, permission,r))
            roles[id].append(r_data)

    ## printing or updating project DB database
    printRoleTableMultipath(roles)
