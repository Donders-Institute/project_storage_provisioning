#!/usr/bin/env python
import sys
import os 
from argparse import ArgumentParser

## adding PYTHONPATH for access to utility modules and 3rd-party libraries
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/external/lib/python')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.ACL    import getACE, setACE, delACE
from utils.Common import getConfig, getMyLogger, csvArgsToList

## execute the main program
if __name__ == "__main__":

    ## load configuration file
    cfg  = getConfig( os.path.dirname(os.path.abspath(__file__)) + '/etc/config.ini' )

    parg = ArgumentParser(description='sets/adds access rights to project storage', version="0.1")

    ## positional arguments
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
                      help    = 'set one of the following verbosity levels. 0|default:WARNING, 1:ERROR, 2:INFO, 3:DEBUG')

    parg.add_argument('-u','--user',
                      action  = 'store',
                      dest    = 'users',
                      default = '',
                      help    = 'set list of system uids separated by "," for the user role')

    parg.add_argument('-c','--contributor',
                      action  = 'store',
                      dest    = 'contributors',
                      default = '',
                      help    = 'set list of system uids separated by "," for the contributor role')

    parg.add_argument('-a','--admin',
                      action  = 'store',
                      dest    = 'admins',
                      default = '',
                      help    = 'set list of system uids separated by "," for the admin role')

    parg.add_argument('-f','--force',
                      action  = 'store_true',
                      dest    = 'force',
                      default = False,
                      help    = 'force updating the ACL even the user is already in the given role, useful for fixing ACL table')

    parg.add_argument('-d','--basedir',
                      action  = 'store',
                      dest    = 'basedir',
                      default = cfg.get('PPS','PROJECT_BASEDIR'),
                      help    = 'set the basedir in which the project storages are located')

#    parg.add_argument('-n','--new',
#                      action  = 'store_true',
#                      dest    = 'do_create',
#                      default = False,
#                      help    = 'create new project directory if it does not exist')

    args = parg.parse_args()

    logger = getMyLogger(name=__file__, lvl=args.verbose)

    args.admins        = args.admins.strip()
    args.users         = args.users.strip()
    args.contributors  = args.contributors.strip()

    _l_admin    = csvArgsToList(args.admins) 
    _l_user     = csvArgsToList(args.users) 
    _l_contrib  = csvArgsToList(args.contributors) 

    ## there is no reason to set yourself for admin, user, contributor
    ## since the you should have been the admin to run this program
    ## and admin has all the rights.
    ##  
    ## if there is a need to change (downgrade) your permission, use
    ## the super user via sudo to run this program.
    me = os.environ['LOGNAME']
    try:
        _l_admin.remove( me )
    except ValueError, e:
        pass

    try:
        _l_user.remove( me )
    except ValueError, e:
        pass

    try:
        _l_contrib.remove( me )
    except ValueError, e:
        pass

    for id in args.pid:

        p = os.path.join(args.basedir, id)

#        if not os.path.exists(p) and args.do_create:
#            os.mkdir(p)
#            ## TODO: set project folder to proper ownership, e.g. project:project_g

        if os.path.exists(p):
            logger.info('setting file or directory: %s' % p)
            setACE(p, admins=_l_admin, users=_l_user, contributors=_l_contrib, force=args.force, lvl=args.verbose)
        else:
            logger.error('file or directory not found: %s' % p)
