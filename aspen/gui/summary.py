from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    )

from PyQt5.QtSql import QSqlQuery
from PyQt5.QtCore import Qt

from ..database import lookup_allowed_values


def show_summary(parent):
    s = Summary(parent)
    s.run()


class Summary(QDialog):

    def __init__(self, parent):
        super().__init__(parent)

        lay = QFormLayout()
        lay.addRow(
            '# Subjects',
            _info(parent.db, 'SELECT COUNT(id) FROM subjects'))
        for session_name in lookup_allowed_values(parent.db['db'], 'sessions', 'name'):
            lay.addRow(
                f'# Subjects with {session_name} session',
                _info(parent.db, f'SELECT COUNT(DISTINCT subject_id) FROM sessions WHERE name = "{session_name}"'))
        lay.addRow(
            '# Subjects with both MRI and IEMU sessions',
            _info(parent.db, """
                SELECT COUNT(id) FROM subjects
                WHERE subjects.id in (SELECT subject_id FROM sessions WHERE sessions.name = 'IEMU')
                AND subjects.id in (SELECT subject_id FROM sessions WHERE sessions.name = 'MRI')"""))
        lay.addRow(
            '# IEMU sessions',
            _info(parent.db, 'SELECT COUNT(DISTINCT sessions.id) FROM sessions WHERE name = "IEMU"'))
        for chan_elec in ('channel', 'electrode'):
            lay.addRow(
                f'# IEMU sessions with {chan_elec}s',
                _info(parent.db, f"""
                    SELECT COUNT(DISTINCT(sessions.id)) FROM sessions
                    LEFT JOIN runs ON runs.session_id = sessions.id
                    LEFT JOIN recordings ON recordings.run_id = runs.id
                    LEFT JOIN recordings_ephys ON recordings_ephys.recording_id = recordings.id
                    WHERE sessions.name = 'IEMU'
                    AND recordings_ephys.{chan_elec}_group_id IS NOT NULL"""))
        lay.addRow(
            '# Runs',
            _info(parent.db, 'SELECT COUNT(id) FROM runs'))
        lay.addRow(
            '# Runs with events',
            _info(parent.db, 'SELECT COUNT(id) FROM runs WHERE id IN (SELECT run_id FROM events)'))
        lay.addRow(
            '# Runs with recordings',
            _info(parent.db, 'SELECT COUNT(DISTINCT run_id) FROM recordings'))
        lay.addRow(
            '# iEEG Recordings',
            _info(parent.db, 'SELECT COUNT(id) FROM recordings WHERE recordings.modality = "ieeg"'))

        ok_button = QDialogButtonBox(QDialogButtonBox.Ok)
        ok_button.accepted.connect(self.accept)

        lay.addWidget(ok_button)
        self.setLayout(lay)

    def run(self):
        self.show()
        self.raise_()
        self.activateWindow()


def _info(db, s):
    query = QSqlQuery(db['db'])
    assert query.exec(s)
    label = QLabel()
    label.setAlignment(Qt.AlignRight)
    if query.next():
        label.setText(str(query.value(0)))
    else:
        label.setText("(ERROR)")

    return label
