#!/usr/bin/env python
import sys
import getpass
import pprint

from utils.Common import getMyLogger
from utils.acl.UserRole import PROJECT_ROLES


class ProjectRoleSettingAction:
    '''object containing attribute for the project access control setup action'''
    def __init__(self, **kwargs):
        self.uid    = None
        self.pid    = None
        self.role   = None
        self.action = None
        self.ctime  = None
        self.atime  = None
        self.pquota = None
        self.__dict__.update(kwargs)

    def __str__(self):
        return pprint.pformat(self.__dict__)

    def __repr__(self):
        return repr(self.__dict__)

    def __cmp__(self,other):
        '''compare actions by creation time'''
        if not isinstance(other, ProjectRoleSettingAction):
            raise NotImplementedError
        return cmp(self.ctime, other.ctime)

    def __eq__(self, other):
        '''action is considered identical if matching uid and pid
           when identical action is found, confliction is resolved
           by taking into account the action with later creation time.
        '''
        if not isinstance(other, ProjectRoleSettingAction):
            raise NotImplementedError
        return self.uid == other.uid and self.pid == other.pid

## loading MySQL library for updating the project database
try:
    ## using pure python MySQL client
    import MySQLdb as mdb
except Exception, e:
    ## trying mysql.connector that requires MySQL client library 
    import mysql.connector as mdb
    from mysql.connector import errorcode

def getDBConnectInfo(cfg):
    '''common function to get database connection information
    '''
  
    ## project database connection information
    db_host   = cfg.get('PPS','PDB_HOST') 
    db_uid    = cfg.get('PPS','PDB_USER') 
    db_name   = cfg.get('PPS','PDB_DATABASE')
    db_pass   = cfg.get('PPS','PDB_PASSWORD')

    if not db_pass:
        ## try ask for password from the interactive shell
        if sys.stdin.isatty(): ## for interactive password typing
            db_pass = getpass.getpass('Project DB password: ')
        else: ## for pipeing-in password
            print 'Project DB password: '
            db_pass = sys.stdin.readline().rstrip()

    return (db_host, db_uid, db_name, db_pass)

def setProjectRoleConfigActions(db_host, db_uid, db_pass, db_name, actions=[], lvl=0):
    '''set configuration actions in the project database as activated
    '''
    logger = getMyLogger(lvl=lvl)
 
    if not mdb:
        logger.error('No MySQL library available.  Function disabled.')
    else:
        ## TODO: make connection to MySQL, prepare and execute SQL statement
        cnx = __getMySQLConnector__(db_host, db_uid, db_pass, db_name, lvl=lvl)
        if not cnx:
            logger.error('Project DB connection failed')
            return
        else:
            crs = None

            try:
                ## in this case, we are using MySQLdb 
                ##  - disable autocommit that is by default enabled in MySQLdb package
                cnx.autocommit(False)
            except Exception:
                ## in this case, we are using mysql.connector
                ##  - the mysql.connector doesn't have the autocommit function;
                ##    but the transaction is enabled by default, and autocommit set to False.
                ##  - we set autocommit to False anyway.
                cnx.autocommit = False

            try:
                ## get the db cursor
                crs = cnx.cursor()
            
                ## select actions that are not activted 
                qry = 'UPDATE projectmembers SET activated=\'yes\',updated=%s WHERE project_id=%s AND user_id=%s AND created<=%s'
                data = []

                for a in actions:
                    data.append( (a.atime,a.pid,a.uid,a.ctime) )

                ## execute queries via the db cursor, transaction *shoud be* enabled by default
                if data:
                    for d in data:
                        logger.debug(qry % d)
                    crs.executemany(qry, data)

                ## commit the transaction if everything is fine
                cnx.commit()

            except Exception, e:
                logger.exception('Project DB update failed')
                try:
                    cnx.rollback()
                except Exception, e:
                    logger.exception('Project DB rollback failed')
            else:
                ## everything is fine
                logger.info('Project DB update succeeded')
            finally:
                ## close db cursor
                try:
                    crs.close()
                except Exception, e:
                    pass

                ## close db connection
                try:
                    cnx.close()
                except Exception, e:
                    pass

def getProjectRoleConfigActions(db_host, db_uid, db_pass, db_name, lvl=0):
    '''retrieve pending configuration actions in the project database
    '''

    logger = getMyLogger(lvl=lvl)
 
    actions=[]

    if not mdb:
        logger.error('No MySQL library available.  Function disabled.')
    else:
        ## TODO: make connection to MySQL, prepare and execute SQL statement
        cnx = __getMySQLConnector__(db_host, db_uid, db_pass, db_name, lvl=lvl)
        if not cnx:
            logger.error('Project DB connection failed')
            return
        else:
            crs = None

            try:
                ## in this case, we are using MySQLdb 
                ##  - disable autocommit that is by default enabled in MySQLdb package
                cnx.autocommit(False)
            except Exception:
                ## in this case, we are using mysql.connector
                ##  - the mysql.connector doesn't have the autocommit function;
                ##    but the transaction is enabled by default, and autocommit set to False.
                ##  - we set autocommit to False anyway.
                cnx.autocommit = False

            try:
                ## get the db cursor
                crs = cnx.cursor()
            
                ## select actions that are not activted 
                qry = 'SELECT a.user_id,a.project_id,a.role,a.created,a.action,b.calculatedProjectSpace FROM projectmembers as a, projects as b WHERE a.activated=\'no\' AND b.calculatedProjectSpace > 0 AND a.project_id=b.id'

                crs.execute(qry)

                for (uid,pid,role,created,action,pquota) in crs:
                    _a_new = ProjectRoleSettingAction( uid=uid, pid=pid, role=role, action=action, ctime=created, pquota=pquota )
                    if actions.count(_a_new) > 0:
                        ## when an action on same uid,pid is found,
                        ## check the action's ctime and take the latest created one
                        idx = actions.index(_a_new) 
                        if _a_new.ctime > actions[ idx ].ctime:
                             actions[ idx ] = _a_new
                    else:
                        ## else, add the action to the list
                        actions.append(_a_new)

            except Exception, e:
                logger.exception('Project DB select failed')
            else:
                ## everything is fine
                logger.info('Project DB select succeeded')
            finally:
                ## close db cursor
                try:
                    crs.close()
                except Exception, e:
                    pass

                ## close db connection
                try:
                    cnx.close()
                except Exception, e:
                    pass

    ## showing all actions to be executed
    for a in actions:
        logger.debug('pid:{} uid:{} role:{} action:{} ctime:{:%Y-%m-%d %H:%M:%S} prj_space:{} GB'.format(a.uid,a.pid,a.role,a.action,a.ctime,a.pquota))

    return actions

def updateProjectDatabase(roles, db_host, db_uid, db_pass, db_name, lvl=0):
    ''' update project roles in the project database 
    '''
    logger = getMyLogger(lvl=lvl)

    if not mdb:
        logger.error('No MySQL library available.  Function disabled.')
    else:
        ## TODO: make connection to MySQL, prepare and execute SQL statement
        cnx = __getMySQLConnector__(db_host, db_uid, db_pass, db_name, lvl=lvl)
        if not cnx:
            logger.error('Project DB connection failed')
            return
        else:
            crs = None

            try:
                ## in this case, we are using MySQLdb 
                ##  - disable autocommit that is by default enabled in MySQLdb package
                cnx.autocommit(False)
            except Exception:
                ## in this case, we are using mysql.connector
                ##  - the mysql.connector doesn't have the autocommit function;
                ##    but the transaction is enabled by default, and autocommit set to False.
                ##  - we set autocommit to False anyway.
                cnx.autocommit = False

            try:
                ## get the db cursor
                crs = cnx.cursor()
            
                ## delete project users first followed by inserting new users and roles
                qry1  = 'DELETE FROM acls WHERE project=%s'
                data1 = []
                qry2  = 'INSERT INTO acls (project, user, projectRole) VALUES (%s, %s, %s)'
                data2 = []

                for p, rd_list in roles.iteritems():
                    for rd in rd_list:
                        for k in PROJECT_ROLES:
                            for u in rd[k]:
                                data1.append((p,))
                                data2.append((p, u, k))

                ## remove duplication
                data1 = list(set(data1))

                ## execute queries via the db cursor, transaction *shoud be* enabled by default
                if data1:
                    for d in data1:
                        logger.debug(qry1 % d)
                    crs.executemany(qry1, data1)

                if data2:
                    for d in data2:
                        logger.debug(qry2 % d)
                    crs.executemany(qry2, data2)

                ## commit the transaction if everything is fine
                cnx.commit()

            except Exception, e:
                logger.exception('Project DB update failed')
                ## something wrong, rollback the queries
                try:
                    cnx.rollback()
                except Exception, e:
                    logger.exception('Project DB rollback failed')
            else:
                ## everything is fine
                logger.info('Project DB update succeeded')
            finally:
                ## close db cursor
                try:
                    crs.close()
                except Exception, e:
                    pass

                ## close db connection
                try:
                    cnx.close()
                except Exception, e:
                    pass

## internal functions
def __getMySQLConnector__(host,uid,passwd,db,lvl=0):
    ''' establishes MySQL connector
    '''

    logger = getMyLogger(lvl=lvl)
    cnx    = None
    config = None 

    if mdb.__name__ == 'MySQLdb':
        ### use MySQLdb library
        config = {'user'   : uid,
                  'passwd' : passwd,
                  'db'     : db,
                  'host'   : host }
        try:
            cnx = mdb.connect(**config)
        except mdb.Error, e:
            logger.error('db query error %d: %s' % (e.args[0],e.args[1]))

            if cnx: cnx.close()
    else:
        ### use mysql-connector library
        config = {'user'             : uid,
                  'password'         : passwd,
                  'database'         : db,
                  'host'             : host,
                  'raise_on_warnings': True }
        try:
            cnx = mdb.connect(**config)
        except mdb.Error, err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                logger.error("something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                logger.error("database does not exists")
            else:
                logger.error(err)

            if cnx: cnx.close()

    return cnx

