#!/usr/bin/env python
import sys
import getpass 
import os
from utils.ACL    import ROLE_ACL
from utils.Common import getMyLogger

class Action:
    '''object containing attribute for the project access control setup action'''
    def __init__(self, **kwargs):
        self.uid    = None
        self.pid    = None
        self.role   = None
        self.action = None
        self.ctime  = None
        self.atime  = None
        self.__dict__.update(kwargs)

    def __str__(self):
        return pprint.pformat(self.__dict__)

    def __repr__(self):
        return repr(self.__dict__)

    def __eq__(self, other):
        if not isinstance(other, Job):
            raise NotImplementedError
        return self.uid == other.uid and self.pid == other.pid and self.role == other.role and self.action == other.action and self.ctime == other.ctime

## loading MySQL library for updating the project database
try:
    ## using pure python MySQL client
    import MySQLdb as mdb
except Exception, e:
    ## trying mysql.connector that requires MySQL client library 
    import mysql.connector as mdb
    from mysql.connector import errorcode

def getDBConnectInfo():
    '''common function to get database connection information
    '''
  
    ## TODO: get information from configuration file

    ## project database connection information
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
                qry = 'UPDATE projectmembers SET activated=\'yes\',updated=%s WHERE project_id=%s AND user_id=%s AND role=%s AND action=%s AND created=%s'
                data = []

                for a in actions:
                    data.append( (a.atime,a.pid,a.uid,a.role,a.action,a.ctime) )

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
                qry = 'SELECT user_id,project_id,role,created,action FROM projectmembers WHERE activated=\'no\''

                crs.execute(qry)

                for (uid,pid,role,created,action) in crs:
                    actions.append(Action( uid=uid, pid=pid, role=role, action=action, ctime=created ))
                    logger.debug('pid:{} uid:{} role:{} action:{} ctime:{:%Y-%m-%d %H:%M:%S}'.format(uid,pid,role,action,created))

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

                for p,r in roles.iteritems():
                    for k,v in r.iteritems():
                        for u in v:
                            data1.append( (p,) )
                            data2.append( (p, u, k) )

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

