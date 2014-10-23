#!/usr/bin/env python
import sys
import os
from utils.ACL    import ROLE_ACL
from utils.Common import getMyLogger

## loading PrettyTable for table output 
from prettytable import PrettyTable

## loading MySQL library for updating the project database
try:
    ## using pure python MySQL client
    import MySQLdb as mdb
except Exception, e:
    ## trying mysql.connector that requires MySQL client library 
    import mysql.connector as mdb
    from mysql.connector import errorcode

def updateProjectDatabase(roles, lvl=0):
    ''' update project roles in the project database 
    '''
    logger = getMyLogger(lvl=lvl)

    if not mdb:
        logger.error('No MySQL library available.  Function disabled.')
    else:
        ## TODO: make connection to MySQL, prepare and execute SQL statement
        pass

def printRoleTable(roles):
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

## internal functions
def __getMySQLConnector__(uid,passwd,db,lvl=0):
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
                  'host'   : 'localhost'}
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
                  'host'             : 'localhost',
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
