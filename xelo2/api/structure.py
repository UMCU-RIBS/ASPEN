from logging import getLogger
from datetime import datetime
from pathlib import Path

from numpy import array, dtype
from PyQt5.QtSql import QSqlQuery

from ..database import TABLES

lg = getLogger(__name__)


def list_subjects():
    query = QSqlQuery(f"SELECT id FROM subjects")

    list_of_subjects = []
    while query.next():
        list_of_subjects.append(Subject(id=query.value('id')))
    return sorted(list_of_subjects)


class Table():
    t = ''
    columns = []
    subtables = {}

    def __init__(self, id):
        self.id = id
        self.columns = columns(self.t)
        self.subtables = construct_subtables(self.t)

    def __str__(self):
        return f'<{self.t} (#{self.id})>'

    def __repr__(self):
        return f'{self.t.capitalize()}(id={self.id})'

    def __eq__(self, other):
        """So that we can compare instances very easily with set"""
        return self.t == other.t and self.id == other.id

    def __hash__(self):
        """So that we can compare instances very easily with set"""
        return hash(self.__str__())

    def delete(self):
        QSqlQuery(f"""\
            DELETE FROM {self.t}s WHERE id == {self.id}
            """)
        self.id = None

    def __getattr__(self, key):

        if key in self.subtables:
            table_name = self.subtables[key]
            id_name = f'{self.t}_id'

        else:
            table_name = f'{self.t}s'
            id_name = 'id'

        query = QSqlQuery(f"SELECT {key} FROM {table_name} WHERE {id_name} == {self.id}")
        if query.next():
            out = query.value(0)

            if key.startswith('date_of_'):  # TODO: it should look TABLES up
                return _date_out(out)

            elif key.endswith('_time'):  # TODO: it should look TABLES up
                return _datetime_out(out)

            else:
                return out

    def __setattr__(self, key, value):

        BUILTINS = (
            'id',
            't',
            'code',
            'columns',
            'subtables',
            'experimenters',
            'subject',
            'session',
            'run',
            'events',
            'data',
            '_tb_data',
            '__class__',
            )

        if key in BUILTINS:
            """__setattr__ comes first: https://stackoverflow.com/a/15751159"""
            super().__setattr__(key, value)
            return

        if key in self.subtables:
            table_name = self.subtables[key]
            id_name = f'{self.t}_id'

        else:
            table_name = f'{self.t}s'
            id_name = 'id'

        if key.startswith('date_of_'):  # TODO: it should look TABLES up
            value = _date(value)
        elif key.endswith('time'):  # TODO: it should look TABLES up
            value = _datetime(value)
        else:
            value = _null(value)

        # insert row in tables, if it doesn't exist
        # we don't care if it works or if it fails, so we don't check output
        query = QSqlQuery(f"""\
            INSERT INTO {table_name} ("{id_name}")
            VALUES ("{self.id}")
            """)

        query = QSqlQuery(f"""\
            UPDATE {table_name}
            SET "{key}"={value}
            WHERE {id_name} == "{self.id}"
            """)

        if query.lastInsertId() is None:
            err = query.lastError()
            raise ValueError(err.databaseText())


class Table_with_files(Table):

    def list_files(self):
        query = QSqlQuery(f"SELECT file_id FROM {self.t}s_files WHERE {self.t}_id == {self.id}")
        out = []
        while query.next():
            out.append(File(query.value('file_id')))
        return out

    def add_file(self, format, path):
        path = Path(path).resolve()

        query = QSqlQuery(f"SELECT id, format FROM files WHERE path == '{path}'")

        if query.next():
            file_id = query.value('id')
            format_in_table = query.value('format')

            if format != format_in_table:
                raise ValueError(f'Input format "{format}" does not match the format "{format_in_table}" in the table for {path}')

        else:
            QSqlQuery(f"""\
                INSERT INTO files ("format", "path")
                VALUES ("{format}", "{path.resolve()}")""")
            file_id = query.lastInsertId()

        query = QSqlQuery(f"""\
            INSERT INTO {self.t}s_files ("{self.t}_id", "file_id")
            VALUES ({self.id}, {file_id})""")

        return File(id=file_id)

    def delete_file(self, file):
        """TODO: add trigger to remove file, here we only remove the link in the table
        """
        QSqlQuery(f'DELETE FROM {self.t}s_files WHERE {self.t}_id == "{self.id}" AND file_id == "{file.id}"')


class NumpyTable(Table):
    """Note that self.id points to the ID of the group
    """

    def __init__(self, id):
        super().__init__(id)
        self._tb_data = self.t.split('_')[0] + 's'

    @property
    def data(self):

        events_type = TABLES[self._tb_data]
        dtypes = []
        for k, v in events_type.items():
            if v is None:
                continue
            elif v['type'] == 'TEXT':
                dtypes.append((k, 'U4096'))
            elif v['type'] == 'FLOAT':
                dtypes.append((k, 'float'))
            else:
                assert False
        dtypes = dtype(dtypes)

        query_str = '"' + '", "'.join(dtypes.names) + '"'
        values = []
        query = QSqlQuery(f"""SELECT {query_str} FROM {self._tb_data} WHERE {self.t}_id == {self.id}""")
        while query.next():
            values.append(
                tuple(query.value(name) for name in dtypes.names)
                )
        query.clear()
        return array(values, dtype=dtypes)

    @data.setter
    def data(self, values):

        QSqlQuery(f'DELETE FROM {self._tb_data} WHERE {self.t}_id == "{self.id}"')

        if values is not None:
            query_str = '"' + '", "'.join(values.dtype.names) + '"'

            for row in values:
                values_str = ', '.join([f'"{x}"' for x in row])
                query = QSqlQuery(f"""\
                    INSERT INTO {self._tb_data} ("{self.t}_id", {query_str})
                    VALUES ("{self.id}", {values_str})
                    """)


class Channels(NumpyTable):
    t = 'channel_group'  # for Table.__getattr__

    def __init__(self, id=None):
        """Use ID if provided, otherwise create a new channel_group"""
        if id is None:
            query = QSqlQuery(f"""\
                INSERT INTO channel_groups ("Reference")
                VALUES ("n/a")
                """)
            id = query.lastInsertId()

        super().__init__(id)


class Electrodes(NumpyTable):
    t = 'electrode_group'  # for Table.__getattr__

    def __init__(self, id=None):
        """Use ID if provided, otherwise create a new electrode_group with
        reasonable parameters"""
        if id is None:
            query = QSqlQuery(f"""\
                INSERT INTO electrode_groups ("CoordinateSystem", "CoordinateUnits")
                VALUES ("ACPC", "mm")
                """)
            id = query.lastInsertId()

        super().__init__(id)


class File(Table):
    t = 'file'

    def __init__(self, id):
        super().__init__(id)

    @property
    def path(self):
        return Path(self.__getattr__('path')).resolve()


class Recording(Table_with_files):
    t = 'recording'
    run = None

    def __init__(self, id, run=None):
        self.run = run
        super().__init__(id)

    @property
    def electrodes(self):
        return Electrodes(id=recording_get('electrode', self.id))

    @property
    def channels(self):
        return Channels(id=recording_get('channel', self.id))

    def attach_electrodes(self, electrodes):
        """Only recording_ieeg"""
        recording_attach('electrode', self.id, group_id=electrodes.id)

    def attach_channels(self, channels):
        """Only recording_ieeg"""
        recording_attach('channel', self.id, group_id=channels.id)

    def detach_electrodes(self):
        """Only recording_ieeg"""
        recording_attach('electrode', self.id, group_id=None)

    def detach_channels(self):
        """Only recording_ieeg"""
        recording_attach('channel', self.id, group_id=None)


def recording_get(group, recording_id):
        query = QSqlQuery(f"""\
            SELECT {group}_group_id FROM recordings_ieeg
            WHERE recording_id == {recording_id}""")
        if query.next():
            return query.value(f'{group}_group_id')
        else:
            raise ValueError(query.lastError().databaseText())


def recording_attach(group, recording_id, group_id=None):

    if group_id is None:
        group_id = 'null'

    query = QSqlQuery(f"""\
        INSERT INTO recordings_ieeg
        ("{group}_group_id", "recording_id")
        VALUES ({group_id}, {recording_id})""")

    if query.lastInsertId() is None:
        QSqlQuery(f"""\
            UPDATE recordings_ieeg
            SET "{group}_group_id"={group_id}
            WHERE recording_id == "{recording_id}" """)


class Run(Table_with_files):
    t = 'run'
    session = None

    def __init__(self, id, session=None):
        self.session = session
        super().__init__(id)

    def __str__(self):
        return f'<{self.t} (#{self.id})>'

    def __lt__(self, other):
        """For sorting. None goes to the end
        """
        if other.start_time is None:
            return False

        elif self.start_time is None:
            return False

        else:
            return self.start_time < other.start_time

    def list_recordings(self):
        query = QSqlQuery(f"""\
            SELECT recordings.id FROM recordings
            WHERE recordings.run_id == {self.id}""")

        list_of_recordings = []
        while query.next():
            list_of_recordings.append(
                Recording(
                    id=query.value('id'),
                    run=self))
        return sorted(list_of_recordings)

    def add_recording(self, modality, offset=0):

        query = QSqlQuery(f"""\
            INSERT INTO recordings ("run_id", "modality", "offset")
            VALUES ("{self.id}", "{modality}", "{offset}")""")

        recording_id = query.lastInsertId()
        if recording_id is None:
            err = query.lastError()
            raise ValueError(err.databaseText())

        recording = Recording(recording_id, run=self)
        return recording

    @property
    def events(self):
        events_type = TABLES['events']
        dtypes = []
        for k, v in events_type.items():
            if v is None:
                continue
            elif v['type'] == 'TEXT':
                dtypes.append((k, 'U4096'))
            elif v['type'] == 'FLOAT':
                dtypes.append((k, 'float'))
            else:
                assert False
        dtypes = dtype(dtypes)

        query_str = '"' + '", "'.join(dtypes.names) + '"'
        values = []
        query = QSqlQuery(f"""SELECT {query_str} FROM events WHERE run_id == {self.id}""")
        while query.next():
            values.append(
                tuple(query.value(name) for name in dtypes.names)
                )
        return array(values, dtype=dtypes)

    @events.setter
    def events(self, values):

        QSqlQuery(f'DELETE FROM events WHERE run_id == "{self.id}"')

        if values is not None:
            query_str = '"' + '", "'.join(values.dtype.names) + '"'

            for row in values:
                values_str = ', '.join([f'"{x}"' for x in row])
                query = QSqlQuery(f"""\
                    INSERT INTO events ("run_id", {query_str})
                    VALUES ("{self.id}", {values_str})
                    """)

    @property
    def experimenters(self):
        query = QSqlQuery(f"""\
            SELECT name FROM experimenters
            JOIN runs_experimenters ON experimenters.id == runs_experimenters.experimenter_id
            WHERE run_id == {self.id}""")
        list_of_experimenters = []
        while query.next():
            list_of_experimenters.append(query.value('name'))
        return sorted(list_of_experimenters)

    @experimenters.setter
    def experimenters(self, experimenters):

        QSqlQuery(f'DELETE FROM runs_experimenters WHERE run_id == "{self.id}"')
        for exp in experimenters:
            query = QSqlQuery(f'SELECT id FROM experimenters WHERE name == "{exp}"')

            if query.next():
                exp_id = query.value('id')
                QSqlQuery(f"""\
                    INSERT INTO runs_experimenters ("run_id", "experimenter_id")
                    VALUES ("{self.id}", "{exp_id}")""")
            else:
                lg.warning(f'Could not find Experimenter called "{exp}". You should add it to "Experimenters" table')

    def attach_protocol(self, protocol):
        query = QSqlQuery(f"""\
            INSERT INTO runs_protocols ("run_id", "protocol_id")
            VALUES ("{self.id}", "{protocol.id}")""")

        if query.lastInsertId() is None:
            err = query.lastError()
            raise ValueError(err.databaseText())

    def detach_protocol(self, protocol):
        QSqlQuery(f"""\
            DELETE FROM runs_protocols
            WHERE run_id == {self.id} AND protocol_id == {protocol.id}
            """)

    def list_protocols(self):
        query = QSqlQuery(f"SELECT run_id FROM runs_protocols WHERE run_id == {self.id}")
        list_of_protocols = []
        while query.next():
            list_of_protocols.append(
                Protocol(query.value('protocol_id')))
        return list_of_protocols


class Protocol(Table_with_files):
    t = 'protocol'

    def __init__(self, id, subject=None):
        super().__init__(id)
        self.subject = subject

    def __lt__(self, other):
        """For sorting. None goes to the end
        """
        if other.date_of_signature is None:
            return False

        elif self.date_of_signature is None:
            return False

        else:
            return self.date_of_signature < other.date_of_signature


class Session(Table_with_files):
    t = 'session'
    subject = None

    def __init__(self, id, subject=None):
        super().__init__(id)
        self.subject = subject

    def __str__(self):
        return f'<{self.t} {self.name} (#{self.id})>'

    def __lt__(self, other):
        """For sorting
        None goes to the end
        """
        if other.start_time is None:
            return False

        elif self.start_time is None:
            return False

        else:
            return self.start_time < other.start_time

    @property
    def start_time(self):
        query = QSqlQuery(f"""\
            SELECT MIN(runs.start_time) FROM runs WHERE runs.session_id == {self.id}
            """)
        if query.next():
            return _datetime_out(query.value(0))

    @property
    def end_time(self):
        query = QSqlQuery(f"""\
            SELECT MAX(runs.end_time) FROM runs WHERE runs.session_id == {self.id}
            """)
        if query.next():
            return _datetime_out(query.value(0))

    def list_runs(self):

        query = QSqlQuery(f"""\
            SELECT runs.id FROM runs
            WHERE runs.session_id == {self.id}""")

        list_of_runs = []
        while query.next():
            list_of_runs.append(
                Run(
                    id=query.value('id'),
                    session=self))
        return sorted(list_of_runs)

    def add_run(self, task_name, start_time=None, end_time=None):

        query = QSqlQuery(f"""\
            INSERT INTO runs ("session_id", "task_name", "start_time", "end_time")
            VALUES ("{self.id}", "{task_name}", {_datetime(start_time)}, {_datetime(end_time)})""")

        run_id = query.lastInsertId()
        if run_id is None:
            err = query.lastError()
            raise ValueError(err.databaseText())

        run = Run(run_id, session=self)
        return run


class Subject(Table_with_files):
    t = 'subject'

    def __init__(self, code=None, id=None):

        if code is not None:
            self.code = code
            query = QSqlQuery(f"SELECT id FROM subjects WHERE code == '{code}'")

            if query.next():
                id = query.value('id')
            else:
                raise ValueError(f'There is no "{code}" in "subjects" table')

        super().__init__(id)

        if code is None:
            self.code = self.__getattr__('code')  # explicit otherwise it gets ignored

    def __repr__(self):
        return f'{self.t.capitalize()}(code="{self.code}")'

    def __lt__(self, other):

        self_sessions = self.list_sessions()
        other_sessions = other.list_sessions()

        if len(other_sessions) == 0 or other_sessions[0] is None:
            return False

        elif len(self_sessions) == 0 or self_sessions[0] is None:
            return True

        else:
            return self_sessions[0].start_time < other_sessions[0].start_time

    @classmethod
    def add(cls, code, date_of_birth=None, sex=None):

        query = QSqlQuery(f"""\
            INSERT INTO subjects ("code", "date_of_birth", "sex")
            VALUES ("{code}", {_date(date_of_birth)}, {_null(sex)})""")

        id = query.lastInsertId()
        if id is None:
            err = query.lastError()
            raise ValueError(err.databaseText())

        return Subject(id=id)

    def add_session(self, name):

        query = QSqlQuery(f"""\
            INSERT INTO sessions ("subject_id", "name")
            VALUES ("{self.id}", "{name}")""")

        session_id = query.lastInsertId()
        if session_id is None:
            err = query.lastError()
            raise ValueError(err.databaseText())

        return Session(session_id, subject=self)

    def list_sessions(self):
        query = QSqlQuery(f"""\
            SELECT sessions.id, name FROM sessions
            WHERE sessions.subject_id ==  '{self.id}'""")

        list_of_sessions = []
        while query.next():
            list_of_sessions.append(
                Session(
                    id=query.value('id'),
                    subject=self))
        return sorted(list_of_sessions)

    def add_protocol(self, METC, date_of_signature=None):

        query = QSqlQuery(f"""\
            INSERT INTO protocols ("subject_id", "METC", "date_of_signature")
            VALUES ("{self.id}", "{METC}", {_date(date_of_signature)})""")

        protocol_id = query.lastInsertId()
        if protocol_id is None:
            err = query.lastError()
            raise ValueError(err.databaseText())

        return Protocol(protocol_id, subject=self)

    def list_protocols(self):
        query = QSqlQuery(f"""\
            SELECT id FROM protocols WHERE subject_id ==  '{self.id}'""")

        list_of_protocols = []
        while query.next():
            list_of_protocols.append(
                Protocol(
                    id=query.value('id'),
                    subject=self))
        return sorted(list_of_protocols)


def columns(t):
    return [x for x in TABLES[t + 's'] if not x.endswith('id') and x != 'subtables']


def construct_subtables(t):
    if 'subtables' not in TABLES[t + 's']:
        return {}
    else:
        subtables = TABLES[t + 's']['subtables']

    attr_tables = {}
    for k, v in subtables.items():
        for i_v in v:
            if i_v.endswith('_id'):
                continue
            attr_tables[i_v] = k

    return attr_tables


def _null(s):
    if s is None:
        return 'null'
    else:
        return f'"{s}"'


def _date(s):
    if s is None:
        return 'null'
    else:
        return f'"{s:%Y-%m-%d}"'


def _datetime(s):
    if s is None:
        return 'null'
    else:
        return f'"{s:%Y-%m-%dT%H:%M:%S}"'


def _date_out(s):
    if s == 'null' or s == '':
        return None
    else:
        return datetime.strptime(s, '%Y-%m-%d').date()


def _datetime_out(s):
    if s == 'null' or s == '':
        return None
    else:
        return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')