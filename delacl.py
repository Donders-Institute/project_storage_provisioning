#!/bin/env python
import sys
import os 
from argparse import ArgumentParser

## adding PYTHONPATH for access to utility modules and 3rd-party libraries
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/external/lib/python')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.ACL    import getACE, setACE, delACE, getRoleFromACE, ROLE_PERMISSION
from utils.Common import getConfig, getMyLogger, csvArgsToList

## execute the main program
if __name__ == "__main__":

    ## load configuration file
    cfg  = getConfig( os.path.dirname(os.path.abspath(__file__)) + '/etc/config.ini' )

    parg = ArgumentParser(description='delete user\'s access right to project storage', version="0.1")

    ## positional arguments
    parg.add_argument('ulist',
                      metavar = 'ulist',
                      nargs   = 1,
                      help    = 'a list of the system user id separated by ","')

    parg.add_argument('pid',
                      metavar = 'pid',
                      nargs   = '+',
                      help    = 'the project id')

    ## optional arguments
    parg.add_argument('-l','--loglevel',
                      action  = 'store',
                      dest    = 'verbose',
                      type    = int,
                      choices = [0, 1, 2, 3],
                      default = 0,
                      help    = 'set the verbosity level, 0:WARNING, 1:ERROR, 2:INFO, 3:DEBUG (default: %(default)s)')

    parg.add_argument('-f','--force',
                      action  = 'store_true',
                      dest    = 'force',
                      default = False,
                      help    = 'force deleting user from ACL even there is no ACE related to the user, useful for fixing ACL table')

    parg.add_argument('-d','--basedir',
                      action  = 'store',
                      dest    = 'basedir',
                      default = cfg.get('PPS','PROJECT_BASEDIR'),
                      help    = 'set the basedir in which the project storages are located (default: %(default)s)')

    parg.add_argument('-p','--subdir',
                      action  = 'store',
                      dest    = 'subdir',
                      default = '',
                      help    = 'specify the sub-directory in the project to which the role setting is applied')

    args = parg.parse_args()

    logger = getMyLogger(name=__file__, lvl=args.verbose)

    # check if setting ACL on subdirectories is supported for the projects in question
    if args.subdir:
        subdir_enabled = cfg.get('PPS', 'PRJ_SUBDIR_ENABLED').split(',')
        for id in args.pid:
            if id not in subdir_enabled:
                logger.error('Setting ACL on subdirecty not allowed: %s' % id)
                # TODO: consolidate the exit codes
                sys.exit(1)

    _l_user = csvArgsToList(args.ulist[0].strip())

    ## It does not make sense to remove myself from project ...
    me = os.environ['LOGNAME']
    try:
        _l_user.remove( me )
    except ValueError, e:
        pass

    for id in args.pid:
        ppath = os.path.join(args.basedir, id)
        fpath = ppath

        if args.subdir:
            # if args.basedir has leading ppath, substitute it with empty string
            fpath = os.path.join(ppath, re.sub(r'^%s/' % ppath, '', args.subdir))

        if os.path.exists(fpath):
            if not delACE(fpath, '', _l_user, force=args.force, lvl=args.verbose):
                logger.error('fail to remove %s from project %s.' % (','.join(_l_user), id))
