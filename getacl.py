#!/bin/env python
import sys
import os 
import logging
from argparse import ArgumentParser

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.ACL    import getACE, setACE, delACE, getRoleFromACE, ROLE_ACL
from utils.Common import getMyLogger, csvArgsToList

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/external/lib/python')
from prettytable import PrettyTable

## set default logger format
logging.basicConfig(format='[%(levelname)s:%(name)s] %(message)s')

def __update_db__(roles, lvl=0):
    ''' update project roles in the project database 
    '''
    logger = getMyLogger(lvl=lvl)
    logger.warning('this function not implemented yet.')

    ## TODO: make connection to MySQL, prepare and execute SQL statement

def __print_role_table__(roles):
    ''' display project roles in prettytable
    '''
    r_keys = ROLE_ACL.keys()

    t = PrettyTable()
    t.field_names = ['project'] + r_keys

    for p,r in roles.iteritems():
        data = []
        data.append(p)
        for k in r_keys:
            if r[k]:
                data.append(','.join(r[k]))
            else:
                data.append('N/A')
        t.add_row(data)

    t.sortby = 'project'
    print t

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
            for type,flag,principle,permission in aces[p]:
               
                ## exclude the default principles 
                u = principle.split('@')[0]
 
                if u not in ['GROUP','OWNER','EVERYONE'] and type in ['A']:
                    r = getRoleFromACE(permission, lvl=args.verbose)
                    roles[id][r].append(u)
                    logger.debug('user %s: permission %s, role %s' % (u, permission,r))

    ## printing or updating project DB database
    __print_role_table__(roles)

    if args.updatedb:
        __update_db__(roles)
