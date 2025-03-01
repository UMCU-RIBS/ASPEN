"""
"""
from logging import getLogger
from getpass import getpass

from PyQt5.QtSql import (
    QSqlDatabase,
    )

from .tables import parse_all_tables, parse_subtables, LEVELS, EXPECTED_TABLES


lg = getLogger(__name__)


def access_database(db_name, username, hostname='localhost', password=None):
    if password is None:
        password = getpass(f'Enter Password for user `{username}` to `{db_name}` (hostname: `{hostname}`):')

    db = open_database(db_name, username=username, password=password, hostname=hostname, connectionName='xelo2_database')
    info_schema = open_database('information_schema', username=username, password=password, hostname=hostname, connectionName='info')

    all_tables = parse_all_tables(info_schema, db)

    subtables = []
    for table in LEVELS:
        subtables.extend(parse_subtables(info_schema, db, table))

    expected_tables = EXPECTED_TABLES + [x['subtable'] for x in subtables]

    remaining_tables = set(all_tables) - set(expected_tables)
    if len(remaining_tables) > 0:
        lg.warning('These tables were not parsed by python API: ' + ', '.join(remaining_tables))

    out = {
        'db': db,
        'info': info_schema,
        'tables': all_tables,
        'subtables': subtables,
        }
    return out


def open_database(db_name, username=None, password=None, hostname=None, connectionName='xelo2_database'):
    """Open the default database using Qt framework

    Parameters
    ----------
    db_name : str
        database name (QMYSQL)
    username : str
        user name to open database
    password : str
        password to open database

    Returns
    -------
    QSqlDatabase
        default database
    """
    db = QSqlDatabase.addDatabase('QMYSQL', connectionName)
    assert db.isValid()

    db.setHostName(hostname)
    db.setUserName(username)
    if password is not None:
        db.setPassword(password)

    db.setDatabaseName(str(db_name))
    db.open()

    if not db.isOpen():
        raise ValueError('Could not open database')

    return db


def close_database(db):
    db['db'].close()
    QSqlDatabase.removeDatabase(db['db'].connectionName())
    db['info'].close()
    QSqlDatabase.removeDatabase(db['info'].connectionName())
