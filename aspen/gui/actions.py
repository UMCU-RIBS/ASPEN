from functools import partial
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QShortcut,
    )
from PyQt5.QtSql import QSqlQuery

from ..database.tables import LEVELS
from .summary import show_summary
from ..bids.utils import SEARCH_STATEMENT


def create_menubar(main):
    menubar = main.menuBar()

    # FILE
    menu_db = menubar.addMenu('Database')

    action_commit = QAction('Commit', main)
    action_commit.triggered.connect(main.sql_commit)
    menu_db.addAction(action_commit)

    action_revert = QAction('Rollback', main)
    action_revert.triggered.connect(main.sql_rollback)
    menu_db.addAction(action_revert)

    action_close = QAction('Quit', main)
    action_close.triggered.connect(main.close)
    menu_db.addAction(action_close)

    menu_db.addSeparator()

    action_info = QAction('Information', main)
    action_info.triggered.connect(lambda x: show_summary(main))
    menu_db.addAction(action_info)

    # View
    menu_view = menubar.addMenu('View')
    main.subjsort = QAction('Sort Subjects A->Z', main)
    main.subjsort.setCheckable(True)
    main.subjsort.triggered.connect(main.list_subjects)
    menu_view.addAction(main.subjsort)
    # Due to requests based on User feedback, we like to start with A-Z, a-z sorted subjects. XEL-62, even though
    # the database includes actions for sorting the subject views, it is often missed by the user.
    main.subjsort.setChecked(True)

    menu_view.addSeparator()

    action_refresh = QAction('Refresh Subjects', main)
    action_refresh.triggered.connect(main.list_subjects)
    menu_view.addAction(action_refresh)

    action_refresh = QAction('Refresh Sessions', main)
    action_refresh.triggered.connect(main.list_sessions_and_protocols)
    menu_view.addAction(action_refresh)

    action_refresh = QAction('Refresh Protocols', main)
    action_refresh.triggered.connect(main.list_sessions_and_protocols)
    menu_view.addAction(action_refresh)

    action_refresh = QAction('Refresh Runs', main)
    action_refresh.triggered.connect(main.list_runs)
    menu_view.addAction(action_refresh)

    action_refresh = QAction('Refresh Recordings', main)
    action_refresh.triggered.connect(main.list_recordings)
    menu_view.addAction(action_refresh)

    action_refresh = QAction('Refresh Parameters', main)
    action_refresh.triggered.connect(main.list_params)
    menu_view.addAction(action_refresh)

    # New
    menu_new = menubar.addMenu('Add')
    for level in LEVELS + ['channels', 'electrodes']:
        action = QAction(f'new {level[:-1]}', main)
        action.triggered.connect(partial(main.new_item, level=level))
        menu_new.addAction(action)

    menu_new.addSeparator()
    action = QAction('new file ...', main)
    action.triggered.connect(main.new_file)
    menu_new.addAction(action)

    # ASP-167 Adding a new option to expand the mental strategy list under runs > mental strategy
    action = QAction('new Mental Strategy ...', main)
    action.triggered.connect(main.new_mental_strategy)
    menu_new.addAction(action)

    # ASP-174 Adding a new option to expand the Mode under runs > Mode.
    action = QAction('new Mode ...', main)
    action.triggered.connect(main.new_mode)
    menu_new.addAction(action)

    # Edit
    menu_edit = menubar.addMenu('Edit')
    menu_new.addSeparator()
    action = QAction('subject codes ...', main)
    action.triggered.connect(main.edit_subject_codes)
    menu_edit.addAction(action)
    action = QAction('calculate offset', main)
    action.triggered.connect(main.calculate_offset)
    menu_edit.addAction(action)
    action = QAction('compare events to those on file', main)
    action.triggered.connect(main.compare_events_with_file)
    menu_edit.addAction(action)
    action = QAction('data for all the electrodes ...', main)
    action.triggered.connect(main.edit_electrode_data)
    menu_edit.addAction(action)

    # io
    menu_io = menubar.addMenu('Import')
    action_parrec = QAction('PAR/REC folder ...', main)
    action_parrec.triggered.connect(main.io_parrec_sess)
    menu_io.addAction(action_parrec)
    action_parrec = QAction('info from PAR/REC recording', main)
    action_parrec.triggered.connect(main.io_parrec)
    menu_io.addAction(action_parrec)
    menu_io.addSeparator()
    action_ephys = QAction('iEEG/EEG/MEG file ...', main)
    action_ephys.triggered.connect(main.io_ephys)
    menu_io.addAction(action_ephys)
    action_events = QAction('info and events from IEEG/EEG/MEG recording ...', main)
    action_events.triggered.connect(main.io_events)
    menu_io.addAction(action_events)
    action_chan = QAction('channels from IEEG/EEG/MEG recording', main)
    action_chan.triggered.connect(main.io_channels)
    menu_io.addAction(action_chan)
    action_elec = QAction('electrodes from ALICE ...', main)
    action_elec.triggered.connect(main.io_electrodes)
    menu_io.addAction(action_elec)
    menu_io.addSeparator()
    action_events = QAction('only events from IEEG/EEG/MEG recording (deprecated)', main)
    action_events.triggered.connect(main.io_events_only)
    menu_io.addAction(action_events)

    # search
    menu_search = menubar.addMenu('Search')
    action_search = QAction('WHERE ...', main)
    action_search.triggered.connect(main.sql_search)
    menu_search.addAction(action_search)
    action_clear = QAction('clear', main)
    action_clear.triggered.connect(main.sql_search_clear)
    menu_search.addAction(action_clear)
    menu_search.addSeparator()
    action_export = QAction('add to list to export', main)
    action_export.triggered.connect(main.add_search_results_to_export)
    menu_search.addAction(action_export)


def create_shortcuts(main):

    shortcut = QShortcut(QKeySequence.Save, main)
    shortcut.activated.connect(main.sql_commit)


class Search():
    subjects = []
    sessions = []
    runs = []
    recordings = []
    previous = ''

    def __init__(self):
        pass

    def where(self, db, where):
        """TODO: where is not sanitized!!!"""

        self.clear()
        self.previous = where

        query = QSqlQuery(db['db'])
        query.prepare(SEARCH_STATEMENT + ' WHERE ' + where)
        if not query.exec():
            raise ValueError(query.lastError().text())

        while query.next():
            self.subjects.append(query.value(0))
            self.sessions.append(query.value(1))
            self.runs.append(query.value(2))
            self.recordings.append(query.value(3))

    def clear(self):

        self.subjects = []
        self.sessions = []
        self.runs = []
        self.recordings = []

        self.previous = ''
