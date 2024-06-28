from logging import getLogger
from datetime import datetime
from PyQt5.QtSql import QSqlQuery
from PyQt5.QtCore import QVariant
import sip

from numpy import (
    dtype,
    )


lg = getLogger(__name__)


def collect_columns(db, t=None, obj=None):
    """For each attribute, this function looks up in which table the information
    is stored.

    Parameters
    ----------
    db : dict
        information about all the tables
    t : str
        name of the table (subject, session, run, etc)
    obj : instance of Subject, Session, Protocol, Run, Recording
        actual object (subject, session, run, etc)

    Returns
    -------
    dict
        where the key is the attribute and the value is the table
    """
    if obj is not None:
        table = obj.t + 's'
    elif t is not None:
        table = t + 's'
    else:
        raise ValueError('You need to specify either t (level name) or obj (actual object)')

    # main table
    attr_tables = {k: table for k in list(db['tables'][table])}

    # look up attributes in subtables
    subtables = []
    for subt in db['subtables']:
        if subt['parent'] != table:
            continue
        if obj is None or getattr(obj, subt['parameter']) in subt['values']:
            subtables.append(subt['subtable'])

    for subt in subtables:
        attr_tables.update(
            {k: subt for k in list(db['tables'][subt])}
            )

    return attr_tables


def find_subject_id(db, code):
    """Look up subject id based on the ID

    Parameters
    ----------
    db : dict
        information about the database
    code : str
        code of the subject

    Returns
    -------
    int
        index of the subject
    """
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
        elif v['type'] == 'QString':
            dtypes.append((k, 'U4096'))
        elif v['type'] == 'double':
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
        return datetime(1900, 1, 1, 0, 0, 0)
    else:
        return obj.start_time


# XEL-60 in addition for bci-sessions to be sorted on data-created field
def sort_data_created(obj):
    if obj.data_created is None:
        return datetime(1900, 1, 1, 0, 0, 0)
    else:
        return obj.data_created


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
        SELECT DISTINCT recordings_ephys.{name}_group_id FROM recordings_ephys
        JOIN recordings ON recordings_ephys.recording_id = recordings.id
        JOIN runs ON runs.id = recordings.run_id
        WHERE recordings.modality IN ('ieeg', 'meg', 'eeg')
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
    query.prepare(f"SELECT {group}_group_id FROM recordings_ephys WHERE recording_id = :recording_id")
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
    query.prepare(f"UPDATE recordings_ephys SET `{group}_group_id` = :group_id WHERE `recording_id` = :recording_id")
    query.bindValue(':group_id', group_id)
    query.bindValue(':recording_id', recording_id)

    if not query.exec():
        raise ValueError(query.lastError().text())
