from logging import getLogger
from datetime import datetime
from PyQt5.QtSql import QSqlQuery
from PyQt5.QtCore import QVariant
import sip

from numpy import (
    dtype,
    )


lg = getLogger(__name__)


def get_attributes(obj):
    """For each main object (Subject, Session etc), it returns the name of the
    attribute, the information about that attribute (type, full name), and the
    actual value.

    Parameters
    ----------
    obj  : instance of Subject, Session, Run, Protocol, Recording
        one of the main objects

    Yields
    ------
    str
        name of the attribute
    dict
        information about the dictionary, such as "name" (full name, with spaces),
        "type" (SQL type), "values" (optional, acceptable values)
    value
        actual value of the attribute for that object
    """
    for column, table in obj.columns.items():
        condition = TABLES[table].get('when', None)
        if condition is not None:  # if subtable
            if getattr(obj, condition['parameter']) not in condition['value']:
                continue  # does not match the WHEN condition
        col_info = TABLES[table][column]
        value = getattr(obj, column)
        yield column, col_info, value


def collect_columns(t):
    """For each attribute, this function looks up in which table the information
    is stored.

    Parameters
    ----------
    t : str
        name of the table (subject, session, run, etc)

    Returns
    -------
    dict
        where the key is the attribute and the value is the table
    """
    table = t + 's'
    attr_tables = {}
    for k, v in TABLES.items():
        if k == table or v.get('when', {}).get('parent', '') == table:
            for k0, v0 in v.items():
                if v0 is None or k0 == 'when':
                    continue
                attr_tables[k0] = k

    return attr_tables


def find_subject_id(db, code):
    query = QSqlQuery(db['db'])
    query.prepare('SELECT subject_id FROM subject_codes WHERE subject_codes.code = :code')
    query.bindValue(':code', code)

    if query.exec():
        if query.next():
            return query.value('subject_id')
        else:
            return None

    else:
        lg.warning(query.lastError().text())


def get_dtypes(table):
    """The columns can only be index, strings or double, but nothing else (no int, no dates)
    """
    dtypes = []
    for k, v in table.items():
        if not (v['index'] is False):   # index is False when it's not an index
            continue
        elif v['type'] == 'TEXT' or v['type'] == 'QString':  # the second is the new format
            dtypes.append((k, 'U4096'))
        elif v['type'] == 'FLOAT' or v['type'] == 'double':  # the second is the new format
            dtypes.append((k, 'float'))
        else:
            assert False
    return dtype(dtypes)


def sort_subjects_alphabetical(subj):
    return str(subj)


def sort_subjects_date(subj):
    sessions = subj.list_sessions()
    if len(sessions) == 0 or sessions[0].start_time is None:
        return datetime(1900, 1, 1, 0, 0, 0)
    else:
        return sessions[0].start_time


def sort_starttime(obj):
    if obj.start_time is None:
        return datetime.now()
    else:
        return obj.start_time


def out_date(driver, out):
    if driver == 'QSQLITE':
        if out == '':
            return None
        else:
            return datetime.strptime(out, '%Y-%m-%d').date()
    else:
        if out.isValid():
            return out.toPyDate()
        else:
            return None


def out_datetime(driver, out):
    if driver == 'QSQLITE':
        if out == '':
            return None
        else:
            return datetime.strptime(out, '%Y-%m-%dT%H:%M:%S')
    else:
        if out.isValid():
            return out.toPyDateTime()
        else:
            return None


def list_channels_electrodes(db, session_id, name='channel'):

    query = QSqlQuery(db['db'])
    query.prepare(f"""\
        SELECT DISTINCT recordings_ieeg.{name}_group_id FROM recordings_ieeg
        JOIN recordings ON recordings_ieeg.recording_id = recordings.id
        JOIN runs ON runs.id = recordings.run_id
        WHERE recordings.modality = 'ieeg'
        AND runs.session_id = :session_id
        ORDER BY runs.start_time""")
    query.bindValue(':session_id', session_id)
    if not query.exec():
        lg.warning(query.lastError().text())

    autoconversion = sip.enableautoconversion(QVariant, False)
    list_of_items = []
    while query.next():
        val = query.value(0)
        if val.isNull():
            continue
        list_of_items.append(int(val.value()))

    sip.enableautoconversion(QVariant, autoconversion)
    return list_of_items


def recording_get(db, group, recording_id):
    query = QSqlQuery(db['db'])
    query.prepare(f"SELECT {group}_group_id FROM recordings_ieeg WHERE recording_id = :recording_id")
    query.bindValue(':recording_id', recording_id)
    if not query.exec():
        lg.warning(query.lastError().text())

    autoconversion = sip.enableautoconversion(QVariant, False)
    out_value = None
    if query.next():
        out = query.value(f'{group}_group_id')
        if not out.isNull():
            out_value = out.value()
    sip.enableautoconversion(QVariant, autoconversion)
    return out_value


def recording_attach(db, group, recording_id, group_id=None):
    """
    Parameters
    ----------
    db : instance of QSqlDatabase
        database
    group : str
        'channel' or 'electrode'
    recording_id : int
        index of the recording
    group_id : int or None
        index of the channel_group or electrode_group. If None, it deletes
        the entry
    """
    query = QSqlQuery(db['db'])
    query.prepare(f"UPDATE recordings_ieeg SET `{group}_group_id` = :group_id WHERE `recording_id` = :recording_id")
    query.bindValue(':group_id', group_id)
    query.bindValue(':recording_id', recording_id)

    if not query.exec():
        raise ValueError(query.lastError().text())
