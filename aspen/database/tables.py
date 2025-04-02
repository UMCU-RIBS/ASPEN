from re import search

from PyQt5.QtSql import QSqlQuery
from PyQt5.QtCore import QMetaType
from PyQt5.Qt import QByteArray


LEVELS = [
    'subjects',
    'sessions',
    'protocols',
    'runs',
    'recordings',
    ]

METATABLES = [
    'allowed_values',
    'intended_for',
    'files',
    'subject_codes',
    'events',
    'experimenters',
    'runs_experimenters',
    'runs_protocols',
    ]

ELEC_CHAN = [
    'channel',
    'electrode',
    ]

EXPECTED_TABLES = (
    METATABLES
    + LEVELS
    + [x + '_files' for x in LEVELS]
    + [x + 's' for x in ELEC_CHAN]
    + [x + '_groups' for x in ELEC_CHAN]
    )


def parse_all_tables(info_schema, db):
    TABLES = {}
    for table in sorted(db.tables()):

        indices = lookup_indexes(info_schema, db, table)
        comments = lookup_comments(info_schema, db, table)

        driver = db.driver()
        rec = driver.record(table)

        table_d = {}
        for i in range(rec.count()):
            field = rec.field(i)
            name = field.name()
            d = {}
            d['type'] = QMetaType.typeName(field.type())
            d['values'] = lookup_allowed_values(db, table, name)
            d['index'] = indices.get(name, False)
            doc = comments.get(name, None)
            if doc is None:
                d['alias'] = name
                d['doc'] = None
            elif ': ' in doc:
                d['alias'], d['doc'] = doc.split(': ')
            else:
                d['alias'] = doc.strip()
                d['doc'] = None

            table_d[name] = d

        TABLES[table] = table_d

    return TABLES


def lookup_allowed_values(db, table, column):
    """Look up allowed values from the table

    Parameters
    ----------
    db : instance of QSqlDatabase

    table : str
        name of the table
    column : str
        name of the column

    Returns
    -------
    list of str
        list of allowed values (it is empty when all the values are allowed)
    """
    query = QSqlQuery(db)
    query.prepare('SELECT allowed_value FROM allowed_values WHERE `table_name` = :table and `column_name` = :column')
    query.bindValue(':table', table)
    query.bindValue(':column', column)
    if not query.exec():
        raise SyntaxError(query.lastError().text())

    values = []
    while query.next():
        values.append(query.value('allowed_value'))

    return values


def lookup_indexes(info_schema, db, table):
    """Look up which columns are indices

    Parameters
    ----------
    info_schema : instance of QSqlDatabase
        this should be the `information_schema` database
    db : instance of QSqlDatabase
        the database with the actual data
    table : str
        name of the table

    Returns
    -------
    dict
        key is the name of the column. 'PRIMARY' for primary indices and
        for foreign keys, it's table_name (column_name)
    """
    if not info_schema.databaseName() == 'information_schema':
        raise ValueError('The first argument should be the `information_schema` database, not the database with the data')

    query = QSqlQuery(info_schema)
    query.prepare("""SELECT `column_name`, `referenced_table_name`, `referenced_column_name` FROM `key_column_usage`
        WHERE `table_schema` = :schema AND `table_name` = :table""")
    query.bindValue(':schema', db.databaseName())
    query.bindValue(':table', table)

    if not query.exec():
        raise SyntaxError(query.lastError().text())

    values = {}
    while query.next():
        k = query.value('column_name')
        t = query.value('referenced_table_name')
        c = query.value('referenced_column_name')
        if t == '':
            values[k] = None
        else:
            values[k] = f'{t} ({c})'

    return values


def lookup_comments(info_schema, db, table):
    """Look up which columns have comments

    Parameters
    ----------
    info_schema : instance of QSqlDatabase
        this should be the `information_schema` database
    db : instance of QSqlDatabase
        the database with the actual data
    table : str
        name of the table

    Returns
    -------
    dict
        key is the name of the column.
    """
    if not info_schema.databaseName() == 'information_schema':
        raise ValueError('The first argument should be the `information_schema` database, not the database with the data')

    query = QSqlQuery(info_schema)
    query.prepare("""SELECT `column_name`, `column_comment` FROM `columns`
        WHERE `table_schema` = :schema AND `table_name` = :table""")
    query.bindValue(':schema', db.databaseName())
    query.bindValue(':table', table)

    if not query.exec():
        raise SyntaxError(query.lastError().text())

    values = {}
    while query.next():
        k = query.value('column_name')
        c = query.value('column_comment')
        if len(c) > 0:
            if isinstance(c, QByteArray):
                c = c.data().decode()
            values[k] = c

    return values


def parse_subtables(info_schema, db, table):
    statements = lookup_statements(info_schema, db, table)

    SUBTABLES = []
    for statement in statements:

        sub = parse_trigger_statements(statement)
        sub['parent'] = table
        if sub is not None:
            SUBTABLES.append(sub)

    return SUBTABLES


def lookup_statements(info_schema, db, table):
    if not info_schema.databaseName() == 'information_schema':
        raise ValueError('The first argument should be the `information_schema` database, not the database with the data')

    query = QSqlQuery(info_schema)
    query.prepare("""SELECT `action_statement` FROM `triggers`
        WHERE `event_object_schema` = :schema AND `event_object_table` = :table AND `event_manipulation` = 'INSERT' AND `action_timing` = 'AFTER'""")
    query.bindValue(':schema', db.databaseName())
    query.bindValue(':table', table)

    if not query.exec():
        raise SyntaxError(query.lastError().text())

    statements = []
    while query.next():
        c = query.value('action_statement')
        if isinstance(c, QByteArray):
            c = c.data().decode()
        statements.append(c)

    return statements


def parse_trigger_statements(statement):

    cond_str = search(r"IF NEW.([a-z_]+) = '(.+?)'", statement)
    if cond_str is None:
        cond_str = search(r"IF NEW.([a-z_]+) IN \((.+?)\)", statement)

        if cond_str is None:
            print('Could not parse trigger condition')
            return

        else:
            parameter = cond_str.group(1)
            values = [x.strip("' ") for x in cond_str.group(2).split(',')]
    else:
        parameter = cond_str.group(1)
        values = [cond_str.group(2), ]

    subtable_str = search(r"INSERT INTO ([a-z_]+)", statement)
    if cond_str is None:
        print('Could not parse subtable')
        return
    else:
        subtable = subtable_str.group(1)

    return {
        'subtable': subtable,
        'parameter': parameter,
        'values': values,
        }
