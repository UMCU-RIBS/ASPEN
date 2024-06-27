from logging import getLogger
from PyQt5.QtSql import QSqlQuery
from numpy import (
    array,
    )

from .backend import Table_with_files, NumpyTable
from .utils import (
    find_subject_id,
    get_dtypes,
    out_datetime,
    list_channels_electrodes,
    recording_attach,
    recording_get,
    sort_starttime,
    sort_subjects_alphabetical,
    sort_subjects_date,
    )

lg = getLogger(__name__)


def list_subjects(db, alphabetical=False, reverse=False):
    """List of the subjects in the currently open database, sorted based on
    the date of their first run.

    Parameters
    ----------
    alphabetical : bool
        False -> sort by date of first run
        True -> sort alphabetically

    reverse : bool
        False -> oldest to newest, True -> newest to oldest
        False -> A to Z, True -> Z to A

    Returns
    -------
    list of instances of Subject
        list of subjects in the database
    """
    query = QSqlQuery(db['db'])
    query.exec('SELECT id FROM subjects')

    list_of_subjects = []
    while query.next():
        list_of_subjects.append(Subject(db, id=query.value('id')))

    if alphabetical:
        _sort_subjects = sort_subjects_alphabetical
    else:
        _sort_subjects = sort_subjects_date

    return sorted(list_of_subjects, key=_sort_subjects, reverse=reverse)


class Subject(Table_with_files):
    t = 'subject'

    def __init__(self, db, code=None, id=None):
        if code is not None:
            id = find_subject_id(db, code)
            if id is None:
                raise ValueError(f'There is no "{code}" in "subject_codes" table')

        super().__init__(db, id)

    def __str__(self):
        codes = self.codes
        if len(codes) == 0:
            return '(subject without code)'
        elif len(codes) == 1:
            return codes[0]
        else:
            return ', '.join(codes)

    @classmethod
    def add(cls, db, code=None):
        """You can create an empty subject, with no code, but it's a bad idea
        """
        if code is not None:
            id = find_subject_id(db, code)
            if id is not None:
                raise ValueError(f'Subject "{code}" already exists')

        # add empty value to get new id
        query = QSqlQuery(db['db'])
        query.prepare("INSERT INTO subjects () VALUES () ")
        if query.exec():
            id = query.lastInsertId()
        else:
            raise ValueError(query.lastError().text())

        if code is not None:
            query = QSqlQuery(db['db'])
            query.prepare("INSERT INTO subject_codes (`subject_id`, `code`) VALUES (:subject_id, :code)")
            query.bindValue(':subject_id', id)
            query.bindValue(':code', code)
            if not query.exec():
                raise SyntaxError(query.lastError().text())

        return Subject(db, id=id)

    @property
    def codes(self):
        """Get the codes associated with this subjects"""
        query = QSqlQuery(self.db['db'])
        query.prepare("SELECT code FROM subject_codes WHERE subject_codes.subject_id = :id")
        query.bindValue(':id', self.id)
        if not query.exec():
            lg.warning(query.lastError().text())

        list_of_codes = []
        while query.next():
            list_of_codes.append(query.value('code'))

        # put RESP at the end
        list_of_codes.sort()
        list_of_codes.sort(key=lambda s: s.startswith('RESP'))
        return list_of_codes

    @codes.setter
    def codes(self, codes):

        query = QSqlQuery(self.db['db'])
        query.prepare('DELETE FROM subject_codes WHERE subject_id = :id')
        query.bindValue(':id', self.id)
        if not query.exec():
            lg.warning(query.lastError().text())

        query = QSqlQuery(self.db['db'])
        query.prepare("INSERT INTO subject_codes (`subject_id`, `code`) VALUES (:id, :code)")
        query.bindValue(':id', self.id)
        for code in set(codes):
            query.bindValue(':code', code)
            if not query.exec():
                raise SyntaxError(query.lastError().text())

    def add_session(self, name):

        query = QSqlQuery(self.db['db'])
        query.prepare("INSERT INTO sessions (`subject_id`, `name`) VALUES (:id, :name)")
        query.bindValue(':id', self.id)
        query.bindValue(':name', name)
        if not query.exec():
            raise ValueError(query.lastError().text())

        session_id = query.lastInsertId()
        if session_id is None:
            raise SyntaxError(query.lastError().text())

        return Session(self.db, session_id, subject=self)

    def list_sessions(self):
        query = QSqlQuery(self.db['db'])
        query.prepare("SELECT sessions.id, name FROM sessions WHERE sessions.subject_id = :id")
        query.bindValue(':id', self.id)
        assert query.exec()

        list_of_sessions = []
        while query.next():
            list_of_sessions.append(
                Session(self.db, id=query.value('id'), subject=self))
        return sorted(list_of_sessions, key=sort_starttime)

    def add_protocol(self, METC):

        query = QSqlQuery(self.db['db'])
        query.prepare("INSERT INTO protocols (`subject_id`, `metc`) VALUES (:id, :metc)")
        query.bindValue(':id', self.id)
        query.bindValue(':metc', METC)

        if not query.exec():
            raise ValueError(query.lastError().text())

        protocol_id = query.lastInsertId()
        return Protocol(self.db, protocol_id, subject=self)

    def list_protocols(self):
        query = QSqlQuery(self.db['db'])
        query.prepare("SELECT id FROM protocols WHERE subject_id = :id")
        query.bindValue(':id', self.id)

        if not query.exec():
            raise SyntaxError(query.lastError().text())

        list_of_protocols = []
        while query.next():
            list_of_protocols.append(
                Protocol(self.db, id=query.value('id'), subject=self))

        return sorted(list_of_protocols, key=lambda obj: obj.metc)


class Protocol(Table_with_files):
    t = 'protocol'

    def __init__(self, db, id, subject=None):
        super().__init__(db, id)
        self.subject = subject


class Session(Table_with_files):
    t = 'session'
    subject = None

    def __init__(self, db, id, subject=None):
        super().__init__(db, id)
        self.subject = subject

    def __str__(self):
        return f'<{self.t} {self.name} (#{self.id})>'

    @property
    def start_time(self):
        query = QSqlQuery(self.db['db'])
        query.prepare("SELECT MIN(runs.start_time) FROM runs WHERE runs.session_id = :id")
        query.bindValue(':id', self.id)
        assert query.exec()

        if query.next():
            return out_datetime(self.db['db'].driverName(), query.value(0))

    def list_runs(self):
        """List runs which were acquired during session"""

        query = QSqlQuery(self.db['db'])
        query.prepare("SELECT runs.id FROM runs WHERE runs.session_id = :id")
        query.bindValue(':id', self.id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())

        list_of_runs = []
        while query.next():
            list_of_runs.append(
                Run(self.db, id=query.value('id'), session=self))
        return sorted(list_of_runs, key=sort_starttime)

    def list_channels(self):

        chan_ids = list_channels_electrodes(self.db, self.id, name='channel')
        return [Channels(self.db, id=id_) for id_ in chan_ids]

    def list_electrodes(self):

        elec_ids = list_channels_electrodes(self.db, self.id, name='electrode')
        return [Electrodes(self.db, id=id_) for id_ in elec_ids]

    def add_run(self, task_name):

        query = QSqlQuery(self.db['db'])
        query.prepare("INSERT INTO runs (`session_id`, `task_name`) VALUES (:id, :task_name)")
        query.bindValue(':id', self.id)
        query.bindValue(':task_name', task_name)
        if not query.exec():
            raise ValueError(query.lastError().text())

        run_id = query.lastInsertId()
        return Run(self.db, run_id, session=self)


class Run(Table_with_files):
    t = 'run'
    session = None

    def __init__(self, db, id, session=None):
        self.session = session
        super().__init__(db, id)

    def __str__(self):
        return f'<{self.t} (#{self.id})>'

    def list_recordings(self):

        query = QSqlQuery(self.db['db'])
        query.prepare("SELECT recordings.id FROM recordings WHERE recordings.run_id = :id")
        query.bindValue(':id', self.id)

        if not query.exec():
            raise SyntaxError(query.lastError().text())

        list_of_recordings = []
        while query.next():
            list_of_recordings.append(
                Recording(self.db, id=query.value('id'), run=self))
        return sorted(list_of_recordings, key=lambda obj: obj.modality)

    def add_recording(self, modality):

        query = QSqlQuery(self.db['db'])
        query.prepare("INSERT INTO recordings (`run_id`, `modality`) VALUES (:id, :modality)")
        query.bindValue(':id', self.id)
        query.bindValue(':modality', modality)

        if not query.exec():
            raise ValueError(query.lastError().text())

        recording_id = query.lastInsertId()
        recording = Recording(self.db, recording_id, run=self)
        return recording

    @property
    def events(self):
        dtypes = get_dtypes(self.db['tables']['events'])

        query_str = ', '.join(f"`{x}`" for x in dtypes.names)
        query = QSqlQuery(self.db['db'])
        query.prepare(f"SELECT {query_str} FROM events WHERE run_id = :id")
        query.bindValue(':id', self.id)

        if not query.exec():
            raise SyntaxError(query.lastError().text())

        values = []
        while query.next():
            values.append(
                tuple(query.value(name) for name in dtypes.names)
                )
        return array(values, dtype=dtypes)

    @events.setter
    def events(self, values):
        """If values is None, it deletes all the events.
        """
        query = QSqlQuery(self.db['db'])
        query.prepare('DELETE FROM events WHERE run_id = :id')
        query.bindValue(':id', self.id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())

        if values is None:
            return

        query_str = ', '.join(f"`{x}`" for x in values.dtype.names)

        for row in values:
            values_str = ', '.join([f"'{x}'" for x in row])
            query = QSqlQuery(self.db['db'])
            sql_cmd = f"""\
                INSERT INTO events (`run_id`, {query_str})
                VALUES ('{self.id}', {values_str})
                """
            if not query.exec(sql_cmd):
                raise SyntaxError(query.lastError().text())

    @property
    def experimenters(self):
        query = QSqlQuery(self.db['db'])
        query.prepare("SELECT name FROM experimenters JOIN runs_experimenters ON experimenters.id = runs_experimenters.experimenter_id WHERE run_id = :id")
        query.bindValue(':id', self.id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())

        list_of_experimenters = []
        while query.next():
            list_of_experimenters.append(query.value('name'))
        return sorted(list_of_experimenters)

    @experimenters.setter
    def experimenters(self, experimenters):

        query = QSqlQuery(self.db['db'])
        query.prepare('DELETE FROM runs_experimenters WHERE run_id = :id')
        query.bindValue(':id', self.id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())

        query_select = QSqlQuery(self.db['db'])
        query_select.prepare("SELECT id FROM experimenters WHERE name = :experimenter")

        query = QSqlQuery(self.db['db'])
        query.prepare("INSERT INTO runs_experimenters (`run_id`, `experimenter_id`) VALUES (:id, :exp_id)")
        query.bindValue(':id', self.id)

        for exp in experimenters:
            query_select.bindValue(':experimenter', exp)
            if not query_select.exec():
                raise SyntaxError(query_select.lastError().text())

            if query_select.next():
                exp_id = query_select.value('id')
                query.bindValue(':exp_id', exp_id)
                if not query.exec():
                    raise SyntaxError(query.lastError().text())

            else:
                lg.warning(f'Could not find Experimenter called "{exp}". You should add it to "Experimenters" table')

    @property
    def intendedfor(self):
        query = QSqlQuery(self.db['db'])
        query.prepare("SELECT target FROM intended_for WHERE run_id = :id")
        query.bindValue(':id', self.id)

        if not query.exec():
            raise SyntaxError(query.lastError().text())

        list_of_intendedfor = []
        while query.next():
            list_of_intendedfor.append(
                Run(self.db, query.value('target')))
        return list_of_intendedfor

    @intendedfor.setter
    def intendedfor(self, runs):
        query = QSqlQuery(self.db['db'])
        query.prepare('DELETE FROM intended_for WHERE run_id = :id')
        query.bindValue(':id', self.id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())

        query = QSqlQuery(self.db['db'])
        query.prepare("INSERT INTO intended_for (`run_id`, `target`) VALUES (:id, :target_id)")
        query.bindValue(':id', self.id)

        for one_run in runs:
            query.bindValue(':target_id', one_run.id)
            if not query.exec():
                raise SyntaxError(query.lastError().text())

    def attach_protocol(self, protocol):
        query = QSqlQuery(self.db['db'])
        query.prepare("INSERT INTO runs_protocols (`run_id`, `protocol_id`) VALUES (:id, :protocol_id)")
        query.bindValue(':id', self.id)
        query.bindValue(':protocol_id', protocol.id)

        if not query.exec():
            raise ValueError(query.lastError().text())

    def detach_protocol(self, protocol):
        query = QSqlQuery(self.db['db'])
        query.prepare("DELETE FROM runs_protocols WHERE run_id = :id AND protocol_id = :protocol_id")
        query.bindValue(':id', self.id)
        query.bindValue(':protocol_id', protocol.id)

        if not query.exec():
            raise SyntaxError(query.lastError().text())

    def list_protocols(self):
        query = QSqlQuery(self.db['db'])
        query.prepare("SELECT protocol_id FROM runs_protocols WHERE run_id = :id")
        query.bindValue(':id', self.id)

        if not query.exec():
            raise SyntaxError(query.lastError().text())

        list_of_protocols = []
        while query.next():
            list_of_protocols.append(
                Protocol(self.db, query.value('protocol_id')))
        return list_of_protocols


class Recording(Table_with_files):
    t = 'recording'
    run = None

    def __init__(self, db, id, run=None):
        self.run = run
        super().__init__(db, id)

    @property
    def electrodes(self):
        electrode_id = recording_get(self.db, 'electrode', self.id)
        if electrode_id is None:
            return None
        return Electrodes(self.db, id=electrode_id)

    @property
    def channels(self):
        channel_id = recording_get(self.db, 'channel', self.id)
        if channel_id is None:
            return None
        return Channels(self.db, id=channel_id)

    def attach_electrodes(self, electrodes):
        """Only recording_ephys"""
        recording_attach(self.db, 'electrode', self.id, group_id=electrodes.id)

    def attach_channels(self, channels):
        """Only recording_ephys"""
        recording_attach(self.db, 'channel', self.id, group_id=channels.id)

    def detach_electrodes(self):
        """Only recording_ephys"""
        recording_attach(self.db, 'electrode', self.id, group_id=None)

    def detach_channels(self):
        """Only recording_ephys"""
        recording_attach(self.db, 'channel', self.id, group_id=None)


class Channels(NumpyTable):
    t = 'channel_group'  # for Table.__getattr__

    @classmethod
    def add(cls, db):
        # add empty value to get new id
        query = QSqlQuery(db['db'])
        query.prepare("INSERT INTO channel_groups (`Reference`) VALUES (NULL) ")
        if query.exec():
            id = query.lastInsertId()
        else:
            raise SyntaxError(query.lastError().text())

        return cls(db, id)


class Electrodes(NumpyTable):
    t = 'electrode_group'  # for Table.__getattr__

    @classmethod
    def add(cls, db):
        """Use ID if provided, otherwise create a new electrode_group with
        reasonable parameters"""
        query = QSqlQuery(db['db'])
        query.prepare("INSERT INTO electrode_groups (`CoordinateSystem`, `CoordinateUnits`) VALUES ('ACPC', 'mm')")
        if query.exec():
            id = query.lastInsertId()
        else:
            raise SyntaxError(query.lastError().text())

        return cls(db, id)


def list_experimenters(db):
    query = QSqlQuery(db['db'])
    query.prepare("SELECT name FROM experimenters ORDER BY name")

    if not query.exec():
        raise SyntaxError(query.lastError().text())

    out = []
    while query.next():
        out.append(query.value('name'))

    # XEL-69 only return active experimenters without deleting the list
    set_all_experimenters = set(out)
    set_active_experimenters = {'Anouck', 'Simon', 'Erik', 'Mariana', 'Julia'}
    get_active_from_all = set_all_experimenters & set_active_experimenters
    active_experimenters_list = list(get_active_from_all)

    return active_experimenters_list
