from numpy import argmin, abs, empty, atleast_1d
from PyQt5.QtWidgets import (
    QTableWidget,
    )
from PyQt5.QtCore import QUrl, QAbstractTableModel, Qt, QVariant
from PyQt5.QtGui import QBrush

from ..io.ephys import localize_blackrock


class FilesWidget(QTableWidget):
    def __init__(self, parent):
        super().__init__()
        self.setAcceptDrops(True)
        self.parent = parent

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        # this one is also necessary for QTableWidget
        event.accept()

    def dropEvent(self, event):
        file_text = event.mimeData().text()
        file_path = QUrl(file_text).toLocalFile().strip()
        self.parent.new_file(filename=file_path)


class EventsModel(QAbstractTableModel):
    X = None
    columns = None
    file_events = None

    def __init__(self, db):
        columns = [k for k, v in db['tables']['events'].items()]
        self.columns = columns
        super().__init__()

    def update(self, data):
        self.file_events = None
        self.beginResetModel()
        self.X = data
        self.endResetModel()

    def compare(self, run, rec, file):

        d = localize_blackrock(file.path)
        offset = (run.start_time - d.header['start_time']).total_seconds()

        file_events = read_file_markers(d)
        if len(file_events) == 0:  # nothing to compare with
            return
        file_events['onset'] -= offset
        file_events['onset'] -= rec.offset

        self.beginResetModel()
        self.file_events = file_events
        self.endResetModel()

    def rowCount(self, index):
        if self.X is None:
            return 1
        else:
            return len(self.X)

    def columnCount(self, index):
        return len(self.columns)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.columns[section]
            elif orientation == Qt.Vertical:
                return str(section + 1)

    def data(self, index, role=Qt.DisplayRole):
        if self.X is None:
            return QVariant()

        i = index.row()
        j = self.columns[index.column()]

        if role == Qt.DisplayRole:
            val = self.X[i][j]
            return str(val)

        elif role == Qt.ForegroundRole and self.file_events is not None:
            mrk_diff = abs(self.file_events['onset'] - self.X[i]['onset'])
            i_min = argmin(mrk_diff)
            if mrk_diff[i_min] > 0.001 or self.file_events['value'][i_min] != self.X[i]['value']:
                return QBrush(Qt.red)
            else:
                return QBrush(Qt.green)

        else:
            return QVariant()


def read_file_markers(d):
    markers = d.read_markers()
    orig_mrk = empty(len(markers), dtype=[('onset', '<f8'), ('value', '<U8')])
    orig_mrk['onset'] = [x['start'] for x in markers]
    orig_mrk['value'] = [x['name'] for x in markers]
    return atleast_1d(orig_mrk)
