#!/bin/env python
import sys
import os 
import getpass 
from argparse import ArgumentParser

## adding PYTHONPATH for access to utility modules and 3rd-party libraries
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/external/lib/python')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.ACL    import getACE, setACE, delACE, getRoleFromACE, ROLE_ACL
from utils.Common import getMyLogger, csvArgsToList
from utils.Report import printRoleTable, updateProjectDatabase

## execute the main program
if __name__ == "__main__":

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
                      default = '/project',
                      help    = 'set the basedir in which the project storages are located')

    parg.add_argument('-u','--updatedb',
                      action  = 'store_true',
                      dest    = 'updatedb',
                      default = False,
                      help    = 'update project database')

    args = parg.parse_args()

    logger = getMyLogger(name=__file__, lvl=args.verbose)

    if not args.pid:
        args.pid = os.listdir(args.basedir)

    roles = {}
    for id in args.pid:
        p = os.path.join(args.basedir, id)

        ## create empty role dict for the project
        roles[id] = {}
        for r in ROLE_ACL.keys():
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

    if args.updatedb:

        db_host   = 'dccn-l004.fcdonders.nl'
        db_uid    = 'acl'
        db_name   = 'fcdc'

        ## read database connection password from stdin
        db_pass   = None

        if sys.stdin.isatty(): ## for interactive password typing
            db_pass = getpass.getpass('Project DB password: ')
        else: ## for pipeing-in password
            print 'Project DB password: '
            db_pass = sys.stdin.readline().rstrip()

        updateProjectDatabase(roles, db_host, db_uid, db_pass, db_name, lvl=args.verbose)
