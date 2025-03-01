from logging import getLogger
from pathlib import Path

from numpy import (
    array,
    character,
    empty,
    floating,
    isnan,
    # NaN,
    issubdtype,
    )
from PyQt5.QtSql import QSqlQuery
from PyQt5.QtCore import QVariant
import sip

from .utils import (
    collect_columns,
    get_dtypes,
    out_date,
    out_datetime,
    )

lg = getLogger(__name__)


class Table():
    """General class to handle one row in a SQL table. End users should not
    use this class but only its subclasses.

    Parameters
    ----------
    db : instance of QSqlDatabase
        currently open database
    id : int
        row index for an unspecified table
    """
    db = None  # instance of database
    t = ''
    columns = {}

    def __init__(self, db, id):
        self.db = db
        self.id = id

        # check if it exists at all
        query = QSqlQuery(self.db['db'])
        query.prepare(f'SELECT id FROM {self.t}s WHERE id = :id')
        query.bindValue(':id', id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())
        if not query.next():
            raise ValueError(f'Could not find id = {id} in table {self.t}s')

        self.columns = collect_columns(self.db, self.t)

    def __str__(self):
        return f'<{self.t} (#{self.id})>'

    def __repr__(self):
        return f'{self.t.capitalize()}(db, id={self.id})'

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
        query = QSqlQuery(self.db['db'])
        query.prepare(f"DELETE FROM {self.t}s WHERE id = :id")
        query.bindValue(':id', self.id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())

        self.id = None

    def __getattr__(self, key):

        if key not in self.columns:
            raise ValueError(f'{key} is not stored in this {self.t}')

        table_name = self.columns[key]
        id_name = 'id'
        if table_name != (self.t + 's'):  # for subtables, use foreign key
            id_name = f'{self.t}_id'

        query = QSqlQuery(self.db['db'])
        query.prepare(f"SELECT {key} FROM {table_name} WHERE {id_name} = :id")
        query.bindValue(':id', self.id)

        if not query.exec():
            raise SyntaxError(query.lastError().text())

        # we need to use QVariant, because QMYSQL in PyQt5 does not distinguish between null and 0.0
        # see https://www.riverbankcomputing.com/static/Docs/PyQt5/pyqt_qvariant.html
        autoconversion = sip.enableautoconversion(QVariant, False)
        if query.next():
            out = query.value(key)

            if out.isNull():
                out = None

            elif self.db['tables'][table_name][key]['type'] == 'QDateTime':
                out = out_datetime(self.db['db'].driverName(), out.value())

            elif self.db['tables'][table_name][key]['type'] == 'QDate':
                out = out_date(self.db['db'].driverName(), out.value())

            else:
                out = out.value()
        else:
            lg.warning(f"Could not get {key} from {table_name} for id = '{self.id}'")
            out = None

        sip.enableautoconversion(QVariant, autoconversion)
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
            'experimenters',
            'codes',
            'subject',
            'session',
            'run',
            'events',
            'data',
            'intendedfor',
            '_tb_data',
            '__class__',
            )

        if key in BUILTINS:
            """__setattr__ comes first: https://stackoverflow.com/a/15751159"""
            super().__setattr__(key, value)
            return

        if key not in self.columns:
            raise ValueError(f'{key} is not stored in this {self.t}')

        table_name = self.columns[key]
        id_name = 'id'
        if table_name != (self.t + 's'):  # for subtables, use foreign key
            id_name = f'{self.t}_id'

        if self.db['tables'][table_name][key]['type'] == 'QDate':
            value = _date(value)
        elif self.db['tables'][table_name][key]['type'] == 'QDateTime':
            value = _datetime(value)
        else:
            value = _null(value)

        query = QSqlQuery(self.db['db'])
        query.prepare(f"UPDATE {table_name} SET `{key}` = {value} WHERE {id_name} = :id")
        query.bindValue(':id', self.id)

        if not query.exec():
            print(value)
            raise ValueError(query.lastError().text())


class Table_with_files(Table):
    """This class (which should be used by end-users) is useful when handling
    objects which might be associated with files.
    """
    def list_files(self):
        """List all the files associated with this object
        """
        query = QSqlQuery(self.db['db'])
        query.prepare(f"SELECT file_id FROM {self.t}s_files WHERE {self.t}_id = :id")
        query.bindValue(':id', self.id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())

        out = []
        while query.next():
            out.append(File(self.db, query.value('file_id')))
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

        query = QSqlQuery(self.db['db'])
        query.prepare("SELECT id, format FROM files WHERE path = :path")
        query.bindValue(':path', str(path))
        if not query.exec():
            raise SyntaxError(query.lastError().text())

        if query.next():
            file_id = query.value('id')
            format_in_table = query.value('format')

            if format != format_in_table:
                raise ValueError(f'Input format "{format}" does not match the format "{format_in_table}" in the table for {path}')

        else:
            query = QSqlQuery(self.db['db'])
            query.prepare("INSERT INTO files (`format`, `path`) VALUES (:format, :path)")
            query.bindValue(':format', format)
            query.bindValue(':path', str(path))
            if not query.exec():
                raise SyntaxError(query.lastError().text())

            file_id = query.lastInsertId()

        query = QSqlQuery(self.db['db'])
        query.prepare(f"INSERT INTO {self.t}s_files (`{self.t}_id`, `file_id`) VALUES (:id, :file_id)")
        query.bindValue(':id', self.id)
        query.bindValue(':file_id', file_id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())

        return File(db=self.db, id=file_id)

    def delete_file(self, file):
        """There should be a trigger that deletes the file when there are no pointers anymore
        """
        query = QSqlQuery(self.db['db'])
        query.prepare(f"DELETE FROM {self.t}s_files WHERE {self.t}_id = :id AND file_id = :file_id")
        query.bindValue(':id', self.id)
        query.bindValue(':file_id', file.id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())


class NumpyTable(Table_with_files):
    """Note that self.id points to the ID of the group
    """

    def __init__(self, db, id):
        super().__init__(db, id)
        self._tb_data = self.t.split('_')[0] + 's'

    @property
    def data(self):
        dtypes = get_dtypes(self.db['tables'][self._tb_data])
        query_str = ", ".join(f"`{col}`" for col in dtypes.names)
        query = QSqlQuery(self.db['db'])
        query.prepare(f"SELECT {query_str} FROM {self._tb_data} WHERE {self.t}_id = :id")
        query.bindValue(':id', self.id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())

        autoconversion = sip.enableautoconversion(QVariant, False)
        values = []
        while query.next():
            row = []
            for name in dtypes.names:
                v = query.value(name)
                if issubdtype(dtypes[name].type, floating) and v.isNull():
                    row.append(NaN)
                else:
                    row.append(v.value())

            values.append(tuple(row))

        sip.enableautoconversion(QVariant, autoconversion)
        return array(values, dtype=dtypes)

    @data.setter
    def data(self, values):
        """If values is None, it deletes all the events.
        """
        query = QSqlQuery(self.db['db'])
        query.prepare(f"DELETE FROM {self._tb_data} WHERE {self.t}_id = :id")
        query.bindValue(':id', self.id)
        if not query.exec():
            raise SyntaxError(query.lastError().text())

        if values is None:
            return

        for row in values:
            column_str, values_str = _create_query(row)
            query = QSqlQuery(self.db['db'])  # column_str depends on values as well (no column when value is NaN)
            sql_cmd = f"""\
                INSERT INTO {self._tb_data} (`{self.t}_id`, {column_str})
                VALUES ('{self.id}', {values_str})
                """
            if not query.exec(sql_cmd):
                raise ValueError(query.lastError().text())

    def empty(self, n_rows):
        """convenience function to get an empty array with empty values if
        necessary"""
        dtypes = get_dtypes(self.db['tables'][self._tb_data])

        values = empty(n_rows, dtype=dtypes)
        for name in values.dtype.names:
            if issubdtype(dtypes[name].type, floating):
                values[name].fill(NaN)

        return values


class File(Table):
    t = 'file'

    def __init__(self, db, id):
        super().__init__(db, id)

    @property
    def path(self):
        return Path(self.__getattr__('path')).resolve()


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
        return '"' + f'{s:%Y-%m-%dT%H:%M:%S.%f}'[:-3] + '"'


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
