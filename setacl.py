#!/usr/bin/env python
import sys
import os 
from argparse import ArgumentParser

## adding PYTHONPATH for access to utility modules and 3rd-party libraries
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/external/lib/python')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.Common import getConfig, getMyLogger, csvArgsToList
from utils.acl.Nfs4ProjectACL import Nfs4ProjectACL

## execute the main program
if __name__ == "__main__":

    ## load configuration file
    cfg  = getConfig( os.path.dirname(os.path.abspath(__file__)) + '/etc/config.ini' )

    parg = ArgumentParser(description='sets/adds access rights to project storage', version="0.1")

    ## positional arguments
    parg.add_argument('prj_id',
                      metavar = 'prj_id',
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

    parg.add_argument('-u','--viewer',
                      action  = 'store',
                      dest    = 'viewers',
                      default = '',
                      help    = 'set list of system uids separated by "," for the user role')

    parg.add_argument('-c','--contributor',
                      action  = 'store',
                      dest    = 'contributors',
                      default = '',
                      help    = 'set list of system uids separated by "," for the contributor role')

    parg.add_argument('-m','--manager',
                      action  = 'store',
                      dest    = 'managers',
                      default = '',
                      help    = 'set list of system uids separated by "," for the admin role')

    parg.add_argument('-f','--force',
                      action  = 'store_true',
                      dest    = 'force',
                      default = False,
                      help    = 'force updating the ACL even the user is already in the given role, useful for fixing ACL table')

    parg.add_argument('-b','--batch',
                      action  = 'store_true',
                      dest    = 'batch',
                      default = False,
                      help    = 'updating the ACL in batch mode, using a cluster job')

    parg.add_argument('-L','--logical',
                      action  = 'store_true',
                      dest    = 'logical',
                      default = False,
                      help    = 'follow logical (symbolic) links')

    parg.add_argument('-d','--basedir',
                      action  = 'store',
                      dest    = 'basedir',
                      default = cfg.get('PPS','PROJECT_BASEDIR'),
                      help    = 'set the basedir in which the project storages are located')

    parg.add_argument('-p','--path',
                      action  = 'store',
                      dest    = 'subdir',
                      default = '',
                      help    = 'specify the relative/absolute path to a sub-directory to which the role setting is applied')

    parg.add_argument('-t','--traverse',
                      action  = 'store_true',
                      dest    = 'traverse',
                      default = False,
                      help    = 'set upper level directories traverse-able for the users in question, up to the project\'s root directory')

#    parg.add_argument('-n','--new',
#                      action  = 'store_true',
#                      dest    = 'do_create',
#                      default = False,
#                      help    = 'create new project directory if it does not exist')

    args = parg.parse_args()

    logger = getMyLogger(name=os.path.basename(__file__), lvl=args.verbose)

    # check if setting ACL on subdirectories is supported for the projects in question
    if args.subdir:
        subdir_enabled = cfg.get('PPS', 'PRJ_SUBDIR_ENABLED').split(',')
        for id in args.prj_id:
            if id not in subdir_enabled:
                logger.error('Setting ACL on subdirecty not allowed: %s' % id)
                # TODO: consolidate the exit codes
                sys.exit(1)

    _l_admin    = csvArgsToList(args.managers.strip())
    _l_user     = csvArgsToList(args.viewers.strip())
    _l_contrib  = csvArgsToList(args.contributors.strip())

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

    fs = Nfs4ProjectACL('', lvl=args.verbose)

    for id in args.prj_id:

        p = os.path.join(args.basedir, id)
        fs.project_root = p

        if args.subdir:
            # if args.basedir has leading ppath, substitute it with empty string
            p = os.path.join(fs.project_root, re.sub(r'^%s/' % fs.project_root, '', args.subdir))

        if os.path.exists(p):
            logger.info('setting file or directory: %s' % p)

            out = fs.setRoles(re.sub(r'^%s/' % fs.project_root, '', args.subdir), users=_l_user, contributors=_l_contrib,
                              admins=_l_admin, force=args.force, traverse=args.traverse, logical=args.logical, batch=args.batch)

            if args.batch and out:
                print('batch job for setting ACL submitted: %s' % out)
        else:
            logger.error('file or directory not found: %s' % p)
