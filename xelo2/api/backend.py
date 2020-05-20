from logging import getLogger
from datetime import datetime
from pathlib import Path

from numpy import (
    array,
    character,
    dtype,
    empty,
    floating,
    isnan,
    NaN,
    issubdtype,
    )
from PyQt5.QtSql import QSqlQuery
from PyQt5.QtCore import QDateTime, QDate

from ..database import TABLES
from .utils import (
    construct_subtables,
    out_date,
    out_datetime,
    )

lg = getLogger(__name__)


class Table():
    """General class to handle one row in a SQL table. End users should not
    use this class but only its subclasses.

    Parameters
    ----------
    id : int
        row index for an unspecified table
    """
    db = None  # instance of database
    t = ''
    columns = []
    subtables = {}

    def __init__(self, db, id):
        self.db = db
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
        """Delete current item / this row from this table. It does not delete
        the python object.
        """
        QSqlQuery(f"""\
            DELETE FROM {self.t}s WHERE id = {self.id}
            """)
        self.id = None

    def __getattr__(self, key):

        if key in self.subtables:
            table_name = self.subtables[key]
            id_name = f'{self.t}_id'

        else:
            table_name = f'{self.t}s'
            id_name = 'id'

        query = QSqlQuery(self.db)
        query.prepare(f"SELECT {key} FROM {table_name} WHERE {id_name} = :id")
        query.bindValue(':id', self.id)

        if not query.exec():
            raise ValueError(f'Could not get {key} from {table_name}')

        if query.next():
            out = query.value(key)

            if out == '':
                return None

            elif TABLES[table_name][key]['type'] == 'DATE':
                return out_date(self.db.driverName(), out)

            elif TABLES[table_name][key]['type'] == 'DATETIME':
                return out_datetime(self.db.driverName(), out)

            else:
                return out

    def __setattr__(self, key, value):
        """Set a value for a key at this row.
        Note that __setattr__ has precedence over all other attributes, so we need
        to make sure that important attributes are handled correctly by the
        subclasses.

        Notes
        -----
        Order in python:
        1. __getattribute__ and __setattr__
        2. Data descriptors, like property
        3. Instance variables from the object's __dict__ (when setting an attribute, the search ends here)
        4. Non-Data descriptors (like methods) and other class variables
        5. __getattr__
        """
        BUILTINS = (
            'db',
            'id',
            't',
            'columns',
            'subtables',
            'experimenters',
            'codes',
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

        query = QSqlQuery(self.db)
        query.prepare(f"UPDATE {table_name} SET `{key}` = {value} WHERE {id_name} = :id")
        query.bindValue(':id', self.id)

        if not query.exec():
            raise ValueError(query.lastError().text())


class Table_with_files(Table):
    """This class (which should be used by end-users) is useful when handling
    objects which might be associated with files.
    """
    def list_files(self):
        """List all the files associated with this object
        """
        query = QSqlQuery(f"SELECT file_id FROM {self.t}s_files WHERE {self.t}_id = {self.id}")
        out = []
        while query.next():
            out.append(File(query.value('file_id')))
        return out

    def add_file(self, format, path):
        """Add a file to this object.

        Parameters
        ----------
        format : str
            type of file (list of acceptable formats is stored in "allowed_values"
        path : str or Path
            path of the file (it does not need to exist)
        """
        path = Path(path).resolve()

        query = QSqlQuery(f"SELECT id, format FROM files WHERE path = '{path}'")

        if query.next():
            file_id = query.value('id')
            format_in_table = query.value('format')

            if format != format_in_table:
                raise ValueError(f'Input format "{format}" does not match the format "{format_in_table}" in the table for {path}')

        else:
            QSqlQuery(f"""\
                INSERT INTO files (`format`, `path`)
                VALUES ("{format}", "{path.resolve()}")""")
            file_id = query.lastInsertId()

        query = QSqlQuery(f"""\
            INSERT INTO {self.t}s_files (`{self.t}_id`, `file_id`)
            VALUES ({self.id}, {file_id})""")

        return File(id=file_id)

    def delete_file(self, file):
        """TODO: add trigger to remove file, here we only remove the link in the table
        """
        QSqlQuery(f'DELETE FROM {self.t}s_files WHERE {self.t}_id = "{self.id}" AND file_id = "{file.id}"')


class NumpyTable(Table_with_files):
    """Note that self.id points to the ID of the group
    """

    def __init__(self, id):
        super().__init__(id)
        self._tb_data = self.t.split('_')[0] + 's'

    @property
    def data(self):
        dtypes = _get_dtypes(TABLES[self._tb_data])
        query_str = ", ".join(f"`{col}`" for col in dtypes.names)
        values = []
        query = QSqlQuery(f"""SELECT {query_str} FROM {self._tb_data} WHERE {self.t}_id = {self.id}""")

        while query.next():
            row = []
            for name in dtypes.names:
                v = query.value(name)
                if issubdtype(dtypes[name].type, floating) and v == '':
                    v = NaN
                row.append(v)

            values.append(tuple(row))

        return array(values, dtype=dtypes)

    @data.setter
    def data(self, values):

        QSqlQuery(f"DELETE FROM {self._tb_data} WHERE {self.t}_id = '{self.id}'")

        if values is not None:
            for row in values:
                column_str, values_str = _create_query(row)
                query = QSqlQuery(f"""\
                    INSERT INTO {self._tb_data} (`{self.t}_id`, {column_str})
                    VALUES ('{self.id}', {values_str})
                    """)

                if not query.isActive():
                    print(query.lastQuery())
                    err = query.lastError()
                    raise ValueError(err.text())

    def empty(self, n_rows):
        """convenience function to get an empty array with empty values if
        necessary"""
        dtypes = _get_dtypes(TABLES[self._tb_data])

        values = empty(n_rows, dtype=dtypes)
        for name in values.dtype.names:
            if issubdtype(dtypes[name].type, floating):
                values[name].fill(NaN)

        return values


class Channels(NumpyTable):
    t = 'channel_group'  # for Table.__getattr__

    def __init__(self, id=None):
        """Use ID if provided, otherwise create a new channel_group"""
        if id is None:
            query = QSqlQuery("""\
                INSERT INTO channel_groups (`Reference`)
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
            query = QSqlQuery("""\
                INSERT INTO electrode_groups (`CoordinateSystem`, `CoordinateUnits`)
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
        electrode_id = recording_get('electrode', self.id)
        if electrode_id is None:
            return None
        return Electrodes(id=electrode_id)

    @property
    def channels(self):
        channel_id = recording_get('channel', self.id)
        if channel_id is None:
            return None
        return Channels(id=channel_id)

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
        WHERE recording_id = {recording_id}""")
    if query.next():
        out = query.value(f'{group}_group_id')
        if out == '':
            return None
        else:
            return out
    else:
        return None


def recording_attach(group, recording_id, group_id=None):

    if group_id is None:
        group_id = 'null'

    query = QSqlQuery(f"""\
        INSERT INTO recordings_ieeg
        (`{group}_group_id`, `recording_id`)
        VALUES ({group_id}, {recording_id})""")

    if query.lastInsertId() is None:
        QSqlQuery(f"""\
            UPDATE recordings_ieeg
            SET "{group}_group_id"={group_id}
            WHERE recording_id = "{recording_id}" """)


def columns(t):
    return [x for x in TABLES[t + 's'] if not x.endswith('id') and x != 'subtables']

def _get_dtypes(table):
    dtypes = []
    for k, v in table.items():
        if v is None:
            continue
        elif v['type'] == 'TEXT':
            dtypes.append((k, 'U4096'))
        elif v['type'] == 'FLOAT':
            dtypes.append((k, 'float'))
        else:
            assert False
    return dtype(dtypes)


def _null(s):
    if s is None:
        return 'null'
    else:
        s = str(s).replace("'", '"')
        s = s.replace('\\', '"')
        return f"'{s}'"


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


def _datetime_out(out):
    assert False
    if out == 'null' or out == '':
        return None
    elif isinstance(out, QDateTime):
        if not out.isValid():
            return None
        else:
            return out.toPyDateTime()
    else:
        return datetime.strptime(out, '%Y-%m-%dT%H:%M:%S')


def _create_query(row):
    """discard nan and create query strings"""
    dtypes = row.dtype
    columns = []
    values = []
    for name in dtypes.names:
        if issubdtype(dtypes[name].type, floating):
            if not isnan(row[name]):
                columns.append(name)
                values.append(f"'{row[name]}'")
        elif issubdtype(dtypes[name].type, character):
            if row[name] != '':
                columns.append(name)
                values.append(f"'{row[name]}'")
        else:
            raise ValueError(f'Unknown dtype {dtypes[name]}')

        assert 'name' in columns

    columns_str = ', '.join([f'`{x}`' for x in columns])
    values_str = ', '.join(values)

    return columns_str, values_str


def list_channels_electrodes(session_id, name='channel'):

    query = QSqlQuery(f"""\
        SELECT DISTINCT recordings_ieeg.{name}_group_id FROM recordings_ieeg
        JOIN recordings ON recordings_ieeg.recording_id = recordings.id
        JOIN runs ON runs.id = recordings.run_id
        WHERE recordings.modality = 'ieeg'
        AND runs.session_id = {session_id}
        ORDER BY runs.start_time""")

    list_of_items = []
    while query.next():
        val = query.value(0)
        if val == '':
            continue
        list_of_items.append(int(val))
    return list_of_items
