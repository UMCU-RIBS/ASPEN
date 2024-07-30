from logging import getLogger
from pathlib import Path
from datetime import date, datetime
from functools import partial
from numpy import isin, array

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDialog,
    QDockWidget,
    QGroupBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressDialog,
    QDoubleSpinBox,
    QSpinBox,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    )
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QDesktopServices,
    QGuiApplication,
    QPalette,
    )
from PyQt5.QtCore import (
    Qt,
    pyqtSlot,
    QDate,
    QDateTime,
    QSettings,
    QUrl,
    )
from PyQt5.QtSql import (
    QSqlQuery,
    QSqlTableModel,
    )

from ..api import list_subjects, Subject, Session, Run, Channels, Electrodes
from ..api.utils import collect_columns
from ..database import access_database, lookup_allowed_values
from ..database.tables import LEVELS
from ..bids.root import create_bids
from ..bids.io.parrec import convert_parrec_nibabel
from ..bids.utils import find_one_file
from ..io.parrec import add_parrec
from ..io.ephys import add_ephys_to_sess
from ..io.channels import create_channels
from ..io.electrodes import import_electrodes
from ..io.events import read_events_from_ephys
from ..io.tsv import load_tsv, save_tsv

from .utils import _protocol_name, _name, _session_name, guess_modality, _sort_session_bci, _check_session_bci, \
    _session_bci_hide_fields, _check_change_age
from .actions import create_menubar, Search, create_shortcuts
from .models import FilesWidget, EventsModel
from .modal import (
    NewFile,
    EditElectrodes,
    Popup_Experimenters,
    Popup_Protocols,
    Popup_IntendedFor,
    CompareEvents,
    CalculateOffset,
    parse_accessdatabase,
    )

# XEL-71
INACTIVE_TASKS = ['abled', 'action_selection', 'animal', 'angiography_scan', 'audcomsent', 'audcomword',
                  'auditory_attention', 'bargrasp', 'auditory_localizer', 'bair_finger_mapping',
                  'bci_cursor_control_attent', 'bci_cursor_control_motor', 'bci_cursor_control_taal',
                  'bci_cursor_control_wm', 'bci_cursor_control_visual', 'boldhand', 'boldsat', 'checkerboard',
                  'clickaway', 'deleted', 'divatt', 'eccentricity_mapping', 'emotion', 'eye_task', 'eyes_open_close',
                  'faces_houses', 'facial_expressions', 'movi', 'feedback_wm', 'flip', 'gestures', 'music',
                  'grootmoeder', 'instant_aud_recall', 'knottask', 'language', 'line_bisection', 'mario',
                  'mental_rotation', 'mooney', 'motionmapper', 'polar_mapping', 'portem', 'pulse', 'sweeptone',
                  'reading_task', 'switchspeed', 'retinotopic_map', 'rotating_sphere', 'rotmotion', 'saccade',
                  'sendkeys', 'threshold', 'touchy', 'smartbrain', 'soc_patterns', 'vardy_beeps', 'sternberg',
                  'movieben', 'verb_it', 'natural_rest', 'notask', 'noun', 'number', 'numerosity', 'noun'
                  'phonemes_and_jipjanneke', 'phonemes', 'vowels', 'visual_field_map', 'visual_left_right_map',
                  'visual_speed_task', 'visual_task_serge', 'visual_attention', 'frontal_eye_field'
                  'visual_field_map', 'visual_up_down_map', 'ct_anatomy_scan', 'faces_emotion', 'flair_anatomy_scan'
                  ]

# XEL-71
NO_MANAGER_TASKS = ['bair_hrfpattern', 'anatomie', 'angio', 'bair_prf', 'bair_spatialobject', 'bair_spatialpattern',
                    'bair_temporalpattern', 'balltalk', 'calc', 'count', 'motor', 'picnam', 'verb', 'mouth_movements']

# ASP-71
UNKNOWN_TASKS = ['instant_aud_recall', 'mental_rotation', 'move_imagine_rest', 'move_three_conditions', 'MP2RAGE',
                 'NOTE', 'pd_anatomy_scan', 'pRF_alessio', 'reference_scan', 'retinotopic_map', 'rotating_sphere',
                 'single_words', 'sixcatlocisidiff', 'sixcatloctemporal', 'vardy_beeps', 'vts_prf',
                 'vts_temporalpattern', 'balltlk', 'flipballistic', 'flipintegration', 'fliprelaxperturb',
                 'flipbaseline']

# XEL-71 one list to filter them all
FILTER_TASKS = INACTIVE_TASKS
FILTER_TASKS.extend(NO_MANAGER_TASKS)
FILTER_TASKS.extend(UNKNOWN_TASKS)


EXTRA_LEVELS = ['channels', 'electrodes']
NULL_TEXT = 'Unknown / Unspecified'

settings = QSettings("xelo2", "xelo2")
lg = getLogger(__name__)


class Interface(QMainWindow):
    """TODO: disable everything until you load database"""
    db = None
    test = False
    unsaved_changes = False

    def __init__(self, db_name=None, username=None, password=None, hostname='localhost'):

        super().__init__()
        create_menubar(self)
        create_shortcuts(self)

        lists = {}
        groups = {}
        for k in LEVELS + EXTRA_LEVELS:
            groups[k] = QGroupBox(k.capitalize())
            lists[k] = QListWidget()
            if k in LEVELS:
                lists[k].currentItemChanged.connect(self.proc_all)
            elif k in EXTRA_LEVELS:
                lists[k].currentItemChanged.connect(self.show_channels_electrodes)

            # right click
            lists[k].setContextMenuPolicy(Qt.CustomContextMenu)
            lists[k].customContextMenuRequested.connect(partial(self.rightclick_list, level=k))

            layout = QVBoxLayout()
            layout.addWidget(lists[k])
            if k == 'runs':
                b = QPushButton('Add to export list')
                b.clicked.connect(self.exporting)
                layout.addWidget(b)
            groups[k].setLayout(layout)

        # PARAMETERS: Widget
        t_params = QTableWidget()
        t_params.horizontalHeader().setStretchLastSection(True)
        t_params.setSelectionBehavior(QAbstractItemView.SelectRows)
        t_params.setColumnCount(3)
        t_params.setHorizontalHeaderLabels(['Level', 'Parameter', 'Value'])
        t_params.verticalHeader().setVisible(False)

        # EVENTS: Widget
        self.events_view = QTableView(self)
        self.events_view.horizontalHeader().setStretchLastSection(True)
        self.events_view.setAlternatingRowColors(True)
        self.events_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.events_view.customContextMenuRequested.connect(partial(self.rightclick_table, table='events'))

        # CHANNELS: Widget
        self.channels_view = QTableView(self)
        self.channels_view.horizontalHeader().setStretchLastSection(True)
        self.channels_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.channels_view.customContextMenuRequested.connect(partial(self.rightclick_table, table='channels'))

        # ELECTRODES: Form
        self.elec_form = QTableWidget()
        self.elec_form.horizontalHeader().setStretchLastSection(True)
        self.elec_form.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.elec_form.setColumnCount(2)
        self.elec_form.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.elec_form.verticalHeader().setVisible(False)

        # ELECTRODES: Widget
        self.electrodes_view = QTableView(self)
        self.electrodes_view.horizontalHeader().setStretchLastSection(True)
        self.electrodes_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.electrodes_view.customContextMenuRequested.connect(partial(self.rightclick_table, table='electrodes'))

        # FILES: Widget
        t_files = FilesWidget(self)
        t_files.horizontalHeader().setStretchLastSection(True)
        t_files.setSelectionBehavior(QAbstractItemView.SelectRows)
        t_files.setColumnCount(3)
        t_files.setHorizontalHeaderLabels(['Level', 'Format', 'File'])
        t_files.verticalHeader().setVisible(False)
        # right click
        t_files.setContextMenuPolicy(Qt.CustomContextMenu)
        t_files.customContextMenuRequested.connect(self.rightclick_files)

        # EXPORT: Widget
        w_export = QWidget()
        col_export = QVBoxLayout()

        t_export = QTableWidget()
        t_export.horizontalHeader().setStretchLastSection(True)
        t_export.setSelectionBehavior(QAbstractItemView.SelectRows)
        t_export.setColumnCount(4)
        t_export.setHorizontalHeaderLabels(['Subject', 'Session', 'Run', 'Start Time'])
        t_export.verticalHeader().setVisible(False)

        p_clearexport = QPushButton('Clear list')
        p_clearexport.clicked.connect(self.clear_export)

        p_doexport = QPushButton('Export ...')
        p_doexport.clicked.connect(self.do_export)

        col_export.addWidget(t_export)
        col_export.addWidget(p_clearexport)
        col_export.addWidget(p_doexport)
        w_export.setLayout(col_export)

        # session and protocol in the same column
        col_sessmetc = QVBoxLayout()
        col_sessmetc.addWidget(groups['sessions'])
        col_sessmetc.addWidget(groups['protocols'])

        # recordings, channels and electrodes
        col_recchanelec = QVBoxLayout()
        col_recchanelec.addWidget(groups['recordings'])
        col_recchanelec.addWidget(groups['channels'])
        col_recchanelec.addWidget(groups['electrodes'])

        # TOP PANELS
        layout_top = QHBoxLayout()
        layout_top.addWidget(groups['subjects'])
        layout_top.addLayout(col_sessmetc)
        layout_top.addWidget(groups['runs'])
        layout_top.addLayout(col_recchanelec)

        # FULL LAYOUT
        # central widget
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addLayout(layout_top)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        # parameters
        dockwidget = QDockWidget('Parameters', self)
        dockwidget.setWidget(t_params)
        dockwidget.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        dockwidget.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dockwidget.setObjectName('dock_parameters')  # savestate
        self.addDockWidget(Qt.RightDockWidgetArea, dockwidget)

        # events
        dockwidget = QDockWidget('Events', self)
        dockwidget.setWidget(self.events_view)
        dockwidget.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        dockwidget.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dockwidget.setObjectName('dock_events')  # savestate
        self.addDockWidget(Qt.RightDockWidgetArea, dockwidget)

        # channels
        dockwidget = QDockWidget('Channels', self)
        dockwidget.setWidget(self.channels_view)
        dockwidget.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        dockwidget.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dockwidget.setObjectName('dock_channels')  # savestate
        self.addDockWidget(Qt.RightDockWidgetArea, dockwidget)

        # electrodes
        dockwidget = QDockWidget('Electrodes', self)
        temp_widget = QWidget()  # you need extra widget to set layout in qdockwidget
        elec_layout = QVBoxLayout(temp_widget)
        elec_layout.addWidget(self.elec_form)
        elec_layout.addWidget(self.electrodes_view, stretch=1)
        dockwidget.setWidget(temp_widget)

        dockwidget.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        dockwidget.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dockwidget.setObjectName('dock_electrodes')  # savestate
        self.addDockWidget(Qt.RightDockWidgetArea, dockwidget)

        # files
        dockwidget = QDockWidget('Files', self)
        dockwidget.setWidget(t_files)
        dockwidget.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        dockwidget.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dockwidget.setObjectName('dock_files')  # savestate
        self.addDockWidget(Qt.BottomDockWidgetArea, dockwidget)

        # export
        dockwidget = QDockWidget('Export', self)
        dockwidget.setWidget(w_export)
        dockwidget.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        dockwidget.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dockwidget.setObjectName('dock_export')  # savestate
        self.addDockWidget(Qt.RightDockWidgetArea, dockwidget)

        # restore geometry
        window_geometry = settings.value('window/geometry')
        if window_geometry is not None:
            self.restoreGeometry(window_geometry)
        window_state = settings.value('window/state')
        if window_state is not None:
            self.restoreState(window_state)

        # SAVE THESE ITEMS
        self.groups = groups
        self.lists = lists
        self.t_params = t_params
        self.t_files = t_files
        self.t_export = t_export
        self.exports = []

        self.search = Search()

        self.statusBar()
        self.show()

        if db_name is None:
            DB_ARGS = parse_accessdatabase(self)
            if DB_ARGS is not None:
                self.sql_access(**DB_ARGS)

        else:
            self.sql_access(db_name, username, password, hostname=hostname)

    def sql_access(self, db_name=None, username=None, password=None, hostname=None):
        """This is where you access the database
        """
        self.db = access_database(db_name, username, hostname, password)
        self.db['db'].transaction()

        self.events_model = EventsModel(self.db)

        self.events_view.setModel(self.events_model)
        self.events_view.hideColumn(0)

        self.channels_model = QSqlTableModel(self, self.db['db'])
        self.channels_model.setTable('channels')
        self.channels_view.setModel(self.channels_model)
        self.channels_view.hideColumn(0)

        self.electrodes_model = QSqlTableModel(self, self.db['db'])
        self.electrodes_model.setTable('electrodes')
        self.electrodes_view.setModel(self.electrodes_model)
        self.electrodes_view.hideColumn(0)

        self.list_subjects()

    def sql_commit(self):
        self.db['db'].commit()
        self.setWindowTitle('')
        self.unsaved_changes = False
        self.db['db'].transaction()

    def sql_rollback(self):
        self.db['db'].rollback()
        self.unsaved_changes = False
        self.setWindowTitle('')
        self.db['db'].transaction()
        self.list_subjects()

    def list_subjects(self, code_to_select=None):
        """
        code_to_select : str
            code of the subject to select
        """
        for line in self.lists.values():
            line.clear()

        to_select = None
        if self.subjsort.isChecked():
            args = {
                'alphabetical': True,
                'reverse': False,
                }
        else:
            args = {
                'alphabetical': False,
                'reverse': True,
                }
        for subj in list_subjects(self.db, **args):
            # ASP-62 Request to display all patient names in lowercase.
            item = QListWidgetItem(str(subj).lower())
            if subj.id in self.search.subjects:
                highlight(item)
            item.setData(Qt.UserRole, subj)
            self.lists['subjects'].addItem(item)
            if code_to_select is not None and code_to_select == str(subj):
                to_select = item
            if to_select is None:  # select first one
                to_select = item
        self.lists['subjects'].setCurrentItem(to_select)

    @pyqtSlot(QListWidgetItem, QListWidgetItem)
    def proc_all(self, current=None, previous=None, item=None):
        """GUI calls current and previous. You can call item"""

        self.list_channels_electrodes()
        if item is None:
            # when clicking on a previously selected list, it sends a signal where current is None, but I don't understand why
            if current is None:
                return
            item = current.data(Qt.UserRole)

        if item.t == 'subject':
            self.list_sessions_and_protocols(item)

        elif item.t == 'session':
            self.list_runs(item)

        elif item.t == 'protocol':
            pass

        elif item.t == 'run':
            self.list_recordings(item)
            self.show_events(item)

        elif item.t == 'recording':
            self.list_channels_electrodes(item)

        self.list_params()
        self.list_files()

    def list_sessions_and_protocols(self, subj=None):

        if subj is None or subj is False:
            subj = self.current('subjects')

        for level, l in self.lists.items():
            if level in ('subjects', ):
                continue
            l.clear()

        # XEL-60 We need to sort BCI sessions differently
        subject_list = subj.list_sessions()
        bci_list = []
        for session in subject_list:
            if session.name == 'BCI':
                bci_list.append(session)

        subject_list = [subject for subject in subject_list if subject not in bci_list]  # filter to contain non-bci
        bci_list = _sort_session_bci(bci_list)
        subject_list.extend(bci_list)  # add bci entries at end of list so sort goes non-bci -> bci in view

        # XEL-60 adding a display of session number on the session list view
        for index, sess in enumerate(subject_list):  # XEL-60 index
            item = QListWidgetItem_time(sess, f"# {index+1}  {_session_name(sess)}")  # XEL-60 adding index to view
            if sess.id in self.search.sessions:
                highlight(item)
            self.lists['sessions'].addItem(item)
        self.lists['sessions'].setCurrentRow(0)

        for protocol in subj.list_protocols():
            item = QListWidgetItem(_protocol_name(protocol))
            item.setData(Qt.UserRole, protocol)
            self.lists['protocols'].addItem(item)
        self.lists['protocols'].setCurrentRow(0)

    def list_runs(self, sess=None):

        if sess is None or sess is False:
            sess = self.current('sessions')

        for level, l in self.lists.items():
            if level in ('subjects', 'sessions', 'protocols'):
                continue
            l.clear()

        for i, run in enumerate(sess.list_runs()):
            item = QListWidgetItem_time(run, f'#{i + 1: 3d}: {run.task_name}')
            if run.id in self.search.runs:
                highlight(item)
            self.lists['runs'].addItem(item)
        self.lists['runs'].setCurrentRow(0)

    def list_recordings(self, run=None):

        if run is None or run is False:
            run = self.current('runs')

        for level, l in self.lists.items():
            if level in ('subjects', 'sessions', 'protocols', 'runs'):
                continue
            l.clear()

        for recording in run.list_recordings():
            item = QListWidgetItem(recording.modality)
            item.setData(Qt.UserRole, recording)
            if recording.id in self.search.recordings:
                highlight(item)
            self.lists['recordings'].addItem(item)
        self.lists['recordings'].setCurrentRow(0)

    def list_channels_electrodes(self, recording=None):

        for level, l in self.lists.items():
            if level in ('channels', 'electrodes'):
                l.clear()

        self.channels_model.setFilter('channel_group_id = 0')
        self.channels_model.select()
        self.channels_view.setEnabled(False)
        self.electrodes_model.setFilter('electrode_group_id = 0')
        self.electrodes_model.select()
        self.electrodes_view.setEnabled(False)
        self.elec_form.clearContents()

        if recording is None:
            return

        sess = self.current('sessions')

        if recording.modality in ('ieeg', 'eeg', 'meg'):
            for chan in sess.list_channels():
                item = QListWidgetItem(_name(chan.name))
                item.setData(Qt.UserRole, chan)
                self.lists['channels'].addItem(item)

            for elec in sess.list_electrodes():
                item = QListWidgetItem(_name(elec.name))
                item.setData(Qt.UserRole, elec)
                self.lists['electrodes'].addItem(item)

    def statusbar_selected(self):

        statusbar = []
        for k, v in self.lists.items():
            item = v.currentItem()
            if item is None:
                continue
            obj = item.data(Qt.UserRole)
            statusbar.append(repr(obj))

        self.statusBar().showMessage('\t'.join(statusbar))

    def list_params(self):
        self.statusbar_selected()

        self.t_params.blockSignals(True)
        self.t_params.clearContents()

        # ASP-64 Need to store the session, so we don't create a lookup request inside the dict loop
        current_session_name = self.lists['sessions'].currentItem().data(Qt.UserRole).name

        all_params = []
        for k, v in self.lists.items():
            item = v.currentItem()
            if item is None:
                continue
            obj = item.data(Qt.UserRole)

            parameters = {}
            parameters.update(list_parameters(self, obj))

            # ASP-63 We need a small reference when checking parms to corresponding fields. When found connect slots.
            if 'Age' in parameters:
                _age = parameters['Age']
            if 'Date of Birth' in parameters:
                _dob = parameters['Date of Birth']
                _dob.dateChanged.connect(lambda: _check_change_age(_dob, _start_time, _age))
            if 'Start Time' in parameters:
                _start_time = parameters['Start Time']
                _start_time.dateChanged.connect(lambda: _check_change_age(_dob, _start_time, _age))

            # ASP-64 Check if we are dealing with BCI-session and clear the parameters that shouldn't be displayed
            if _check_session_bci(current_session_name):
                _session_bci_hide_fields(parameters)

            if k == 'runs':
                w = Popup_Experimenters(obj, self)
                parameters.update({'Experimenters': w})
                w = Popup_Protocols(obj, self)
                parameters.update({'Protocols': w})
                if obj.task_name == 'top_up':
                    w = Popup_IntendedFor(obj, self)
                    parameters.update({'Intended For': w})

            elif k == 'recordings':

                if obj.modality in ('ieeg', 'eeg', 'meg'):
                    parameters.update(list_parameters(self, obj))

                    sess = self.current('sessions')

                    w = QComboBox()  # add callback here
                    w.addItem('(undefined channels)', None)
                    for chan in sess.list_channels():
                        w.addItem(_name(chan.name), chan)
                    channels = obj.channels
                    if channels is None:
                        w.setCurrentText('')
                    else:
                        w.setCurrentText(_name(channels.name))
                    w.activated.connect(partial(self.combo_chanelec, widget=w))
                    parameters.update({'Channels': w})

                    w = QComboBox()
                    w.addItem('(undefined electrodes)', None)
                    for elec in sess.list_electrodes():
                        w.addItem(_name(elec.name), elec)
                    electrodes = obj.electrodes
                    if electrodes is None:
                        w.setCurrentText('')
                    else:
                        w.setCurrentText(_name(electrodes.name))
                    w.activated.connect(partial(self.combo_chanelec, widget=w))
                    parameters.update({'Electrodes': w})

            for p_k, p_v in parameters.items():
                all_params.append({
                    'level': self.groups[k].title(),
                    'parameter': p_k,
                    'value': p_v,
                    })

        self.t_params.setRowCount(len(all_params))

        for i, val in enumerate(all_params):
            item = QTableWidgetItem(val['level'])
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setBackground(QBrush(QColor('lightGray')))
            self.t_params.setItem(i, 0, item)
            item = QTableWidgetItem(val['parameter'])
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.t_params.setItem(i, 1, item)
            item = QTableWidgetItem(str(val['value']))
            self.t_params.setCellWidget(i, 2, val['value'])

        self.t_params.blockSignals(False)

    def combo_chanelec(self, i, widget):
        data = widget.currentData()
        recording = self.current('recordings')
        if data is None:
            if widget.currentText() == '(undefined channels)':
                recording.detach_channels()
            else:
                recording.detach_electrodes()

        elif data.t == 'channel_group':
            recording.attach_channels(data)

        elif data.t == 'electrode_group':
            recording.attach_electrodes(data)

    def electrode_intendedfor(self, index, elec, combobox):
        if index == 0:
            elec.IntendedFor = None
        else:
            elec.IntendedFor = combobox[index]
        self.modified()

    def current(self, level):

        item = self.lists[level].currentItem()
        if item is not None:
            return item.data(Qt.UserRole)

    def list_files(self):

        self.t_files.blockSignals(True)
        self.t_files.clearContents()

        all_files = []
        for k, v in self.lists.items():
            item = v.currentItem()
            if item is None:
                continue
            obj = item.data(Qt.UserRole)
            for file in obj.list_files():
                all_files.append({
                    'level': self.groups[k].title(),
                    'format': file.format,
                    'path': file.path,
                    'obj': [obj, file],
                    })

        self.t_files.setRowCount(len(all_files))

        for i, val in enumerate(all_files):

            item = QTableWidgetItem(val['level'])
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setBackground(QBrush(QColor('lightGray')))
            item.setData(Qt.UserRole, val['obj'])
            self.t_files.setItem(i, 0, item)

            item = QTableWidgetItem(val['format'])
            item.setData(Qt.UserRole, val['obj'])
            self.t_files.setItem(i, 1, item)

            item = QTableWidgetItem(str(val['path']))
            try:
                path_exists = val['path'].exists()

            except PermissionError as err:
                lg.warning(err)
                item.setForeground(QBrush(QColor('orange')))

            else:
                if not path_exists:
                    item.setForeground(QBrush(QColor('red')))

            item.setData(Qt.UserRole, val['obj'])
            self.t_files.setItem(i, 2, item)

        self.t_files.blockSignals(False)

    def changed(self, obj, column, x):
        if isinstance(x, QDate):
            x = x.toPyDate()
        elif isinstance(x, QDateTime):
            x = x.toPyDateTime()
        else:
            if isinstance(x, QLineEdit):
                x = x.text()

            if x == NULL_TEXT:
                x = None
            else:
                x = f'{x}'

        setattr(obj, column, x)
        self.modified()

    def show_events(self, item):
        self.events_model.update(item.events)

    def compare_events_with_file(self):

        run = self.current('runs')
        rec = self.current('recordings')

        file = find_one_file(rec, ('blackrock', 'micromed', 'bci2000'))
        if file is None:
            print('Could not find electrophysiology file')
            return

        self.events_model.compare(run, rec, file)

    @pyqtSlot(QListWidgetItem, QListWidgetItem)
    def show_channels_electrodes(self, current=None, previous=None, item=None):

        if current is not None:
            item = current.data(Qt.UserRole)

        if item is None:
            return

        self.statusbar_selected()
        if item.t == 'channel_group':
            self.channels_view.setEnabled(True)
            self.channels_model.setFilter(f'channel_group_id = {item.id}')
            self.channels_model.select()

        elif item.t == 'electrode_group':
            self.elec_form.blockSignals(True)

            parameters = list_parameters(self, item)
            parameters['Intended For'] = make_electrode_combobox(self, item)
            self.elec_form.setRowCount(len(parameters))
            for i, kv in enumerate(parameters.items()):
                k, v = kv
                table_item = QTableWidgetItem(k)
                self.elec_form.setItem(i, 0, table_item)
                self.elec_form.setCellWidget(i, 1, v)
            self.elec_form.blockSignals(False)

            self.electrodes_view.setEnabled(True)
            self.electrodes_model.setFilter(f'electrode_group_id = {item.id}')
            self.electrodes_model.select()

    def exporting(self, checked=None, subj=None, sess=None, run=None):

        if subj is None:
            subj = self.lists['subjects'].currentItem().data(Qt.UserRole)
            sess = self.lists['sessions'].currentItem().data(Qt.UserRole)
            run = self.lists['runs'].currentItem().data(Qt.UserRole)

        d = {}
        d['subjects'] = str(subj)
        if sess.name == 'MRI':
            d['sessions'] = f'{sess.name} ({sess.MagneticFieldStrength})'
        else:
            d['sessions'] = sess.name
        d['run_id'] = run.id
        d['runs'] = f'{run.task_name}'
        d['start_time'] = f'{run.start_time:%d %b %Y %H:%M:%S}'
        self.exports.append(d)

        self.list_exports()

    def clear_export(self):
        self.exports = []
        self.list_exports()

    def list_exports(self):

        self.t_export.clearContents()
        n_exports = len(self.exports)

        self.t_export.setRowCount(n_exports)

        for i, l in enumerate(self.exports):
            item = QTableWidgetItem(l['subjects'])
            self.t_export.setItem(i, 0, item)
            item = QTableWidgetItem(l['sessions'])
            self.t_export.setItem(i, 1, item)
            item = QTableWidgetItem(l['runs'])
            self.t_export.setItem(i, 2, item)
            item = QTableWidgetItem(l['start_time'])
            self.t_export.setItem(i, 3, item)

    def rightclick_table(self, pos, table=None):
        if table == 'events':
            view = self.events_view
        elif table == 'channels':
            view = self.channels_view
        elif table == 'electrodes':
            view = self.electrodes_view

        menu = QMenu(self)
        action = QAction(f'Import {table} from tsv ...', self)
        action.triggered.connect(lambda x: self.tsv_import(table=table))
        menu.addAction(action)
        action = QAction(f'Export {table} to tsv ...', self)
        action.triggered.connect(lambda x: self.tsv_export(table=table))
        menu.addAction(action)
        menu.popup(view.mapToGlobal(pos))

    def tsv_import(self, table):

        tsv_file = QFileDialog.getOpenFileName(
            self,
            f"Import {table} from file",
            None,
            "Tab-separated values (*.tsv)")[0]

        if tsv_file == '':
            return

        if table == 'events':
            run = self.current('runs')
            X = run.events
        else:
            current = self.current(table)
            X = current.data

        X = load_tsv(Path(tsv_file), X.dtype)

        if table == 'events':
            run.events = X
            self.show_events(run)

        else:
            current.data = _fake_names(X)
            recording = self.current('recordings')
            self.list_channels_electrodes(recording=recording)

        self.modified()

    def tsv_export(self, table):

        tsv_file = QFileDialog.getSaveFileName(
            self,
            f"Save {table} to file",
            None,
            "Tab-separated values (*.tsv)")[0]

        if tsv_file == '':
            return

        if table == 'events':
            run = self.current('runs')
            X = run.events
        else:
            current = self.current(table)
            X = current.data

        save_tsv(Path(tsv_file), X)

    def rightclick_list(self, pos, level=None):
        item = self.lists[level].itemAt(pos)

        menu = QMenu(self)
        if item is None:
            action = QAction(f'Add {level}', self)
            action.triggered.connect(lambda x: self.new_item(level=level))
            menu.addAction(action)

        else:
            obj = item.data(Qt.UserRole)

            if obj.t in ('channel_group', 'electrode_group'):
                action_rename = QAction('Rename', self)
                action_rename.triggered.connect(lambda x: self.rename_item(obj))
                menu.addAction(action_rename)
            action_delete = QAction('Delete', self)
            action_delete.triggered.connect(lambda x: self.delete_item(obj))
            menu.addAction(action_delete)

        menu.popup(self.lists[level].mapToGlobal(pos))

    def rename_item(self, item):
        text, ok = QInputDialog.getText(
            self,
            f'Rename {item.t.split("_")[0]}',
            'New title:',
            )

        if ok and text != '':
            item.name = text

    def delete_item(self, item):
        item.delete()

        if item.t == 'subject':
            self.list_subjects()

        elif item.t == 'session':
            self.list_sessions_and_protocols(item.subject)

        elif item.t == 'protocol':
            self.list_sessions_and_protocols(item.subject)

        elif item.t == 'run':
            self.list_runs(item.session)

        elif item.t == 'recording':
            self.list_recordings(item.run)

        self.list_params()
        self.list_files()

    def rightclick_files(self, pos):
        item = self.t_files.itemAt(pos)

        if item is None:
            menu = QMenu(self)
            action = QAction('Add File', self)
            action.triggered.connect(lambda x: self.new_file(self))
            menu.addAction(action)
            menu.popup(self.t_files.mapToGlobal(pos))

        else:
            level_obj, file_obj = item.data(Qt.UserRole)
            file_path = file_obj.path.resolve()
            url_directory = QUrl.fromLocalFile(str(file_path.parent))

            action_edit = QAction('Edit File', self)
            action_edit.triggered.connect(lambda x: self.edit_file(level_obj, file_obj))
            action_copy = QAction('Copy Path to File', self)
            action_copy.triggered.connect(lambda x: copy_to_clipboard(str(file_obj.path)))
            action_openfile = QAction('Open File', self)
            action_openfile.triggered.connect(lambda x: self.open_file(file_path))

            action_opendirectory = QAction('Open Containing Folder', self)
            action_opendirectory.triggered.connect(lambda x: QDesktopServices.openUrl(url_directory))
            action_delete = QAction('Delete', self)
            action_delete.triggered.connect(lambda x: self.delete_file(level_obj, file_obj))
            menu = QMenu('File Information', self)
            menu.addAction(action_edit)
            menu.addAction(action_copy)
            menu.addAction(action_openfile)
            menu.addAction(action_opendirectory)
            menu.addSeparator()
            menu.addAction(action_delete)
            menu.popup(self.t_files.mapToGlobal(pos))

    def open_file(self, file_path):
        if file_path.suffix.lower() == '.par':
            print(f'converting {file_path}')
            file_path = convert_parrec_nibabel(file_path)[0]
            print(f'converted to {file_path}')

        url_file = QUrl.fromLocalFile(str(file_path))
        QDesktopServices.openUrl(url_file)

    def sql_search(self):

        text, ok = QInputDialog.getText(
            self,
            'Search the database',
            'WHERE statement' + ' ' * 200,
            QLineEdit.Normal,
            self.search.previous,
            )

        if ok and text != '':
            self.search.where(self.db, text)
            self.list_subjects()

    def sql_search_clear(self):
        self.search.clear()
        self.list_subjects()

    def add_search_results_to_export(self):

        for subj_id, sess_id, run_id in zip(self.search.subjects, self.search.sessions, self.search.runs):
            self.exporting(
                subj=Subject(self.db, id=subj_id),
                sess=Session(self.db, id=sess_id),
                run=Run(self.db, id=run_id),
                )

    def modified(self):
        self.unsaved_changes = True
        self.setWindowTitle('*' + self.windowTitle())

    def do_export(self, checked=None):

        subset = {'subjects': [], 'sessions': [], 'runs': []}
        run_ids = '(' + ', '.join([str(x['run_id']) for x in self.exports]) + ')'

        query = QSqlQuery(self.db['db'])
        query.prepare(f"""\
            SELECT subjects.id, sessions.id, runs.id FROM runs
            JOIN sessions ON sessions.id = runs.session_id
            JOIN subjects ON subjects.id = sessions.subject_id
            WHERE runs.id IN {run_ids}
            """)

        if not query.exec():
            raise SyntaxError(query.lastError().text())

        while query.next():
            subset['subjects'].append(query.value(0))
            subset['sessions'].append(query.value(1))
            subset['runs'].append(query.value(2))

        data_path = QFileDialog.getSaveFileName(
            self,
            "Choose directory where to save the recordings in BIDS format",
            'bids_output',
            'Folder (*)',
            )[0]
        if data_path == '':
            return

        data_path = Path(data_path).resolve()
        if data_path.exists():
            QMessageBox.warning(
                self,
                'Folder exists',
                'This folder already exists. Make sure you choose a folder name that does not exist',
                )
            return

        create_bids(self.db, data_path, deface=False, subset=subset)

    def new_item(self, checked=None, level=None):

        if level == 'subjects':
            text, ok = QInputDialog.getText(
                self,
                'Add New Subject',
                'Subject Code:',
                )

        elif level == 'sessions':
            current_subject = self.current('subjects')
            text, ok = QInputDialog.getItem(
                self,
                f'Add New Session for {current_subject}',
                'Session Name:',
                lookup_allowed_values(self.db['db'], 'sessions', 'name'),
                0, False)

        elif level == 'protocols':
            current_subject = self.current('subjects')
            text, ok = QInputDialog.getItem(
                self,
                f'Add New Protocol for {current_subject}',
                'Protocol Name:',
                lookup_allowed_values(self.db['db'], 'protocols', 'metc'),
                0, False)

        elif level == 'runs':
            current_session = self.current('sessions')

            # XEL-61 sorted view of tasks list # ASP-71 case-insensitive sorting
            runs_list = sorted(lookup_allowed_values(self.db['db'], 'runs', 'task_name'), key=str.casefold)

            # XEL-71 Without deleting earlier tasks, we filter the list the user gets to see, check top of file for list
            runs_list = [task for task in runs_list if task not in FILTER_TASKS]

            text, ok = QInputDialog.getItem(
                self,
                f'Add New Run for {current_session.name}',
                'Task Name:',
                runs_list,
                0, False)

        elif level == 'recordings':
            current_run = self.current('runs')

            modalities = lookup_allowed_values(self.db['db'], 'recordings', 'modality')
            guess = guess_modality(current_run)

            if guess is None or guess not in modalities:
                idx = 0
            else:
                idx = modalities.index(guess)

            text, ok = QInputDialog.getItem(
                self,
                f'Add New Recording for {current_run.task_name}',
                'Modality:',
                modalities,
                idx,
                False)

        elif level in ('channels', 'electrodes'):
            current_recording = self.current('recordings')
            if current_recording is None or current_recording.modality not in ('ieeg', 'eeg', 'meg'):
                QMessageBox.warning(
                    self,
                    f'Cannot add {level}',
                    'You should first select an "ieeg" / "eeg" / "meg" recording')
                return

            text, ok = QInputDialog.getText(
                self,
                f'Add new {level}',
                'Name to identify this setup:',
                )

        if ok and text != '':
            if level == 'subjects':
                code = text.strip()
                Subject.add(self.db, code)
                self.list_subjects(code)

            elif level == 'sessions':
                current_subject.add_session(text)
                self.list_sessions_and_protocols(current_subject)

            elif level == 'protocols':
                current_subject.add_protocol(text)
                self.list_sessions_and_protocols(current_subject)

            elif level == 'runs':
                current_session.add_run(text)
                self.list_runs(current_session)

            elif level == 'recordings':
                current_run.add_recording(text)
                self.list_recordings(current_run)

            elif level in ('channels', 'electrodes'):
                if level in 'channels':
                    chan = Channels.add(self.db)
                    chan.name = text
                    current_recording.attach_channels(chan)

                elif level in 'electrodes':
                    elec = Electrodes.add(self.db)
                    elec.name = text
                    current_recording.attach_electrodes(elec)

                self.list_recordings(self.current('runs'))
                self.list_channels_electrodes(current_recording)
                self.list_params()

            self.modified()

    def edit_subject_codes(self):
        subject = self.current('subjects')
        text = str(subject)
        if text == '(subject without code)':
            text = ''
        text, ok = QInputDialog.getText(
            self,
            'Edit Subject Codes',
            'Separate each code by a comma (spaces are ignored)',
            text=text,
            )

        if ok and text != '':
            text = text.strip(', ')
            subject.codes = [x.strip() for x in text.split(',')]
            self.list_subjects()
            self.modified()

    def new_file(self, checked=None, filename=None):
        get_new_file = NewFile(self, filename=filename)
        result = get_new_file.exec()

        if result:
            level = get_new_file.level.currentText().lower() + 's'
            item = self.current(level)
            format = get_new_file.format.currentText()
            path = get_new_file.filepath.text()
            item.add_file(format, path)

            self.list_files()
            self.modified()

    def edit_file(self, level_obj, file_obj):
        get_new_file = NewFile(self, file_obj, level_obj)
        result = get_new_file.exec()

        if result:
            format = get_new_file.format.currentText()
            path = get_new_file.filepath.text()
            file_obj.path = path
            file_obj.format = format

        self.list_files()
        self.modified()

    def calculate_offset(self):
        warning_title = 'Cannot calculate offset'
        run = self.current('runs')
        recordings = run.list_recordings()

        if len(recordings) == 0:
            QMessageBox.warning(self, warning_title, 'There are no recordings')
            return

        rec_fixed = recordings[0]
        rec_moving = self.current('recordings')
        if rec_fixed.id == rec_moving.id:
            QMessageBox.warning(self, warning_title, 'This function compares the first recording with the highlighted recording. Please select another recording to compute the offset')
            return

        file_fixed = find_one_file(rec_fixed, ('blackrock', 'micromed', 'bci2000'))
        if file_fixed is None:
            QMessageBox.warning(self, warning_title, 'The first recording does not have an ephys file')
            return
        file_moving = find_one_file(rec_moving, ('blackrock', 'micromed', 'bci2000'))
        if file_moving is None:
            QMessageBox.warning(self, warning_title, 'The selected recording does not have an ephys file')
            return

        calcoffset = CalculateOffset(self, file_fixed, file_moving)
        result = calcoffset.exec()
        if result:
            text = calcoffset.offset.text()
            if text.endswith(')'):
                return
            offset = float(text[:-1])
            rec_moving.offset = offset

            self.list_params()
            self.modified()

    def edit_electrode_data(self):
        elec = self.current('electrodes')
        data = elec.data
        edit_electrodes = EditElectrodes(self, data)
        result = edit_electrodes.exec()

        if result:
            parameter = edit_electrodes.parameter.currentText()
            value = edit_electrodes.value.text()

            data[parameter] = array(value).astype(data.dtype[parameter])
            elec.data = data

            self.show_channels_electrodes(item=elec)
            self.modified()

    def io_parrec(self):
        run = self.current('runs')
        recording = self.current('recordings')

        success = False
        for file in recording.list_files():
            if file.format == 'parrec':
                add_parrec(file.path, run=run, recording=recording, update=True)
                success = True
                break

        if success:
            self.list_recordings(run)
            self.list_params()
            self.modified()
        else:
            self.statusBar().showMessage('Cound not find PAR/REC to collect info from')

    def io_parrec_sess(self):
        sess = self.current('sessions')

        par_folder = QFileDialog.getExistingDirectory()
        if par_folder == '':
            return

        list_parrec = list(Path(par_folder).glob('*.PAR'))
        progress = QProgressDialog('', 'Cancel', 0, len(list_parrec), self)
        progress.setWindowTitle(f'Importing PAR/REC files to "{sess.subject}"/"{sess.name}"')
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModal)

        for i, par_file in enumerate(list_parrec):
            progress.setValue(i)
            progress.setLabelText(f'Importing {par_file.name}')
            QGuiApplication.processEvents()
            add_parrec(par_file, sess=sess)

            if progress.wasCanceled():
                break

        progress.setValue(i + 1)
        self.list_runs(sess)
        self.list_params()
        self.modified()

    def io_ephys(self):
        sess = self.current('sessions')

        ephys_file = QFileDialog.getOpenFileName(
            self,
            "Select File",
            None)[0]

        if ephys_file == '':
            return

        add_ephys_to_sess(self.db, sess, Path(ephys_file))

        self.list_runs(sess)
        self.list_params()
        self.modified()

    def io_events_only(self):
        run = self.current('runs')
        recording = self.current('recordings')

        ephys_file = find_one_file(recording, ('blackrock', 'micromed', 'bci2000'))
        if ephys_file is None:
            return

        events = read_events_from_ephys(ephys_file, run, recording)

        if len(events) > 0:
            run.events = events
            self.show_events(run)

            self.modified()
        else:
            print('there were no events')

    def io_events(self):
        run = self.current('runs')
        recording = self.current('recordings')

        ephys_file = find_one_file(recording, ('blackrock', 'micromed', 'bci2000'))
        if ephys_file is None:
            return

        compare_events = CompareEvents(self, run, ephys_file.path)
        result = compare_events.exec()

        if result == QDialog.Accepted:
            run.start_time = compare_events.info['start_time']
            run.duration = compare_events.info['duration']
            run.events = compare_events.info['events']

            self.list_params()
            self.show_events(run)
            self.modified()

    def io_channels(self):
        recording = self.current('recordings')

        ephys_file = find_one_file(recording, ('blackrock', 'micromed', 'bci2000'))
        if ephys_file is None:
            return

        chan = create_channels(self.db, ephys_file.path)
        if chan is None:
            return
        chan.name = '(imported)'
        recording.attach_channels(chan)

        self.modified()
        self.list_recordings()

    def io_electrodes(self):

        mat_file = QFileDialog.getOpenFileName(
            self,
            "Open File",
            None,
            "Matlab (*.mat)")[0]

        if mat_file == '':
            return

        rec = self.current('recordings')
        chan = rec.channels
        chan_data = chan.data
        idx = isin(chan_data['type'], ('ECOG', 'SEEG'))
        n_chan = idx.sum()
        lg.warning(f'# of ECOG/SEEG channels for this recording: {n_chan}')

        xyz = import_electrodes(mat_file, n_chan)
        if xyz is None:
            print('you need to do this manually')
            return

        elec = Electrodes.add(self.db)
        elec_data = elec.empty(n_chan)
        elec_data['name'] = chan_data['name'][idx]
        elec_data['x'] = xyz[:, 0]
        elec_data['y'] = xyz[:, 1]
        elec_data['z'] = xyz[:, 2]
        elec.data = elec_data
        rec.attach_electrodes(elec)

        self.modified()
        self.list_recordings()

    def delete_file(self, level_obj, file_obj):
        level_obj.delete_file(file_obj)
        self.list_files()
        self.modified()

    def closeEvent(self, event):

        if self.unsaved_changes:
            answer = QMessageBox.question(
                self,
                'Confirm Closing',
                'There are unsaved changes. Are you sure you want to exit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No)

            if answer == QMessageBox.No:
                event.ignore()
                return

        settings.setValue('window/geometry', self.saveGeometry())
        settings.setValue('window/state', self.saveState())

        event.accept()


def list_parameters(parent, obj):
    db = parent.db

    columns = collect_columns(db, obj=obj)

    d = {}
    for col, t in columns.items():
        col_info = db['tables'][t][col]

        if not (col_info['index'] is False):
            continue

        value = getattr(obj, col)

        if col_info['type'] == 'QDateTime':
            w = make_datetime(value)
            w.dateTimeChanged.connect(partial(parent.changed, obj, col))

        elif col_info['type'] == 'QDate':
            w = make_date(value)
            w.dateChanged.connect(partial(parent.changed, obj, col))

        elif col_info['type'] == 'double':
            w = make_float(value)
            w.valueChanged.connect(partial(parent.changed, obj, col))

        elif col_info['type'] == 'int':
            w = make_integer(value)
            w.valueChanged.connect(partial(parent.changed, obj, col))

        elif col_info['type'] == 'QString':
            if col_info['values']:
                values = col_info['values']
                if len(values) > 20:
                    values = sorted(values)
                w = make_combobox(value, values)

                w.currentTextChanged.connect(partial(parent.changed, obj, col))
            else:
                w = make_edit(value)
                w.editingFinished.connect(partial(parent.changed, obj, col, w))

        else:
            raise ValueError(f'unknown type "{col_info["type"]}"')

        if col_info['doc'] is not None:
            w.setToolTip(col_info['doc'])

        d[col_info['alias']] = w

    return d


def make_edit(value):
    w = QLineEdit()
    w.insert(value)
    return w


def make_integer(value):
    w = QSpinBox()
    # w.setRange(-2e7, 2e7)

    if value is None:
        w.setValue(0)
        palette = QPalette()
        palette.setColor(QPalette.Text, Qt.red)
        w.setPalette(palette)

    else:
        w.setValue(value)

    return w


def make_float(value):
    w = QDoubleSpinBox()
    w.setDecimals(3)
    w.setRange(-1e8, 1e8)

    if value is None:
        w.setValue(0)
        palette = QPalette()
        palette.setColor(QPalette.Text, Qt.red)
        w.setPalette(palette)

    else:
        try:
            w.setValue(value)
        except TypeError:
            print(value)
            print(type(value))

    return w


def make_combobox(value, possible_values):
    w = QComboBox()
    values = [NULL_TEXT, ] + possible_values
    w.addItems(values)
    w.setCurrentText(value)

    return w


def make_electrode_combobox(self, elec):
    subj = self.lists['subjects'].currentItem().data(Qt.UserRole)
    INTENDED = {'Unknown': 0}
    for sess in subj.list_sessions():
        sess_name = _session_name(sess)
        for i, one_run in enumerate(sess.list_runs()):
            if one_run.task_name in ('ct_anatomy_scan', 'flair_anatomy_scan', 't1_anatomy_scan', 't2_anatomy_scan', 't2star_anatomy_scan', 'MP2RAGE'):
                name = f'#{i + 1: 2d}: {one_run.task_name}'
                INTENDED[sess_name + ' / ' + name] = one_run.id

    w = QComboBox()
    for k in INTENDED:
        w.addItem(k)

    intendedfor = elec.IntendedFor
    if intendedfor is not None:
        w.setCurrentIndex(list(INTENDED.values()).index(intendedfor))
    w.currentIndexChanged.connect(partial(self.electrode_intendedfor, elec=elec, combobox=list(INTENDED.values())))

    return w


def make_date(value):
    w = QDateEdit()
    w.setCalendarPopup(True)
    w.setDisplayFormat('dd/MM/yyyy')
    if value is None:
        w.setDate(date(1900, 1, 1))
        palette = QPalette()
        palette.setColor(QPalette.Text, Qt.red)
        w.setPalette(palette)
    else:
        w.setDate(value)

    return w


def make_datetime(value):
    w = QDateTimeEdit()
    w.setCalendarPopup(True)
    w.setDisplayFormat('dd/MM/yyyy HH:mm:ss.zzz')
    if value is None:
        w.setDateTime(datetime(1900, 1, 1, 0, 0, 0))
        palette = QPalette()
        palette.setColor(QPalette.Text, Qt.red)
        w.setPalette(palette)
    else:
        w.setDateTime(value)

    return w


def copy_to_clipboard(text):

    clipboard = QGuiApplication.clipboard()
    clipboard.setText(text)


def highlight(item):
    item.setBackground(Qt.yellow)
    font = item.font()
    font.setBold(True)
    item.setFont(font)


class QListWidgetItem_time(QListWidgetItem):
    def __init__(self, obj, title):
        self.obj = obj
        super().__init__(title)
        self.setData(Qt.UserRole, obj)

    def __lt__(self, other):
        return self.obj.start_time < other.obj.start_time


def _fake_names(X):
    """We cannot have empty channel names, so we use it the MICROMED
    convention
    """
    for i in range(X['name'].shape[0]):
        if X['name'][i] == '':
            X['name'][i] = f'el{i + 1}'
    return X
