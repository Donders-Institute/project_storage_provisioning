#!/bin/env python
import sys
import os 
from argparse import ArgumentParser

## adding PYTHONPATH for access to utility modules and 3rd-party libraries
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

    args = parg.parse_args()

    _l_user = csvArgsToList(args.ulist[0].strip())

    ## It does not make sense to remove myself from project ...
    me = os.environ['LOGNAME']
    try:
        _l_user.remove( me )
    except ValueError, e:
        pass

    logger = getMyLogger(name=__file__, lvl=args.verbose)

    for id in args.pid:
        p = os.path.join(args.basedir, id)
        if os.path.exists(p):
            if not delACE(p, _l_user, force=args.force, lvl=args.verbose):
                logger.error('fail to remove %s from project %s.' % (','.join(_l_user), id))
