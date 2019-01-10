#!/bin/env python
import sys
import traceback 
import os
from argparse import ArgumentParser

# adding PYTHONPATH for access to utility modules and 3rd-party libraries

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../external/lib/python')
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/..')
from utils.Common import getConfig, getMyLogger
from utils.IMailer import SMTPMailer
from utils.IProjectDB import getDBConnectInfo,updateProjectDatabase
from utils.acl.Nfs4NetApp import Nfs4NetApp

# execute the main program
if __name__ == "__main__":

    # load configuration file
    cfg  = getConfig( os.path.dirname(os.path.abspath(__file__)) + '/../etc/config.ini' )

    parg = ArgumentParser(description='gets access rights of project storages', version="0.1")

    # positional arguments
    parg.add_argument('pid',
                      metavar = 'pid',
                      nargs   = '*',
                      help    = 'the project id')

    # optional arguments
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

    args = parg.parse_args()

    logger = getMyLogger(name=os.path.basename(__file__), lvl=args.verbose)

    if not args.pid:
        args.pid = os.listdir(args.basedir)

    roles = {}
    fs = Nfs4NetApp('', lvl=args.verbose)
    for id in args.pid:
        fs.project_root = os.path.join(args.basedir, id)
        roles[id] = fs.getRoles(recursive=False)

    # updating database
    (db_host, db_uid, db_name, db_pass) = getDBConnectInfo(cfg)

    try:
        updateProjectDatabase(roles, db_host, db_uid, db_pass, db_name, lvl=args.verbose)
    except Exception, e:

        exc_type, exc_value, exc_traceback = sys.exc_info()

        smtp_host = cfg.get('MAILER','SMTP_HOST')
        smtp_port = cfg.get('MAILER','SMTP_PORT')
        smtp_user = cfg.get('MAILER','SMTP_USERNAME')
        smtp_pass = cfg.get('MAILER','SMTP_PASSWORD')

        smtp_credential = None
        if smtp_user and smtp_pass:
            smtp_credential = {'username': smtp_user, 'password': smtp_pass}

        mailer = SMTPMailer(host=smtp_host, port=smtp_port, credential=smtp_credential, lvl=args.verbose)

        subject = 'Fail updating project storage ACL to project database'
        toAddress = cfg.get('MAILER','EMAIL_ADMIN_ADDRESSES')

        # content of the email
        _parts = {'plain': 'System error:\n\n' + ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))}

        # send email
        mailer.sendMultipartEmail(subject=subject, fromAddress=cfg.get('MAILER','EMAIL_FROM_ADDRESS'), toAddress=toAddress, parts=_parts)
