from pathlib import Path
from logging import getLogger
from PyQt5.QtSql import QSqlQuery
from textwrap import dedent
from ..api.utils import collect_columns
from ..gui.utils import _throw_msg_box

lg = getLogger(__name__)

SEARCH_STATEMENT = dedent("""\
    SELECT subjects.id, sessions.id, runs.id, recordings.id FROM subjects
    LEFT JOIN sessions ON sessions.subject_id = subjects.id
    LEFT JOIN sessions_mri ON sessions_mri.session_id = sessions.id
    LEFT JOIN runs ON runs.session_id = sessions.id
    LEFT JOIN recordings ON recordings.run_id = runs.id
    LEFT JOIN recordings_ephys ON recordings_ephys.recording_id = recordings.id
    LEFT JOIN recordings_mri ON recordings_mri.recording_id = recordings.id
    """)


def prepare_subset(db, where, subset=None, join=''):

    query = QSqlQuery(db['db'])
    query.prepare(SEARCH_STATEMENT + join + ' WHERE ' + where)
    if not query.exec():
        raise SyntaxError(query.lastError().text())

    if subset is None:
        subset = {'subjects': [], 'sessions': [], 'runs': []}

    while query.next():
        subset['subjects'].append(query.value('subjects.id'))
        subset['sessions'].append(query.value('sessions.id'))
        subset['runs'].append(query.value('runs.id'))

    return subset


def set_notnone(d, s, field):
    """Set value from field if it's not None
    """
    if s is not None:

        if isinstance(s, dict):
            value = s.get(field, None)
        else:
            value = getattr(s, field)

        if value is not None:
            d[field] = value


def rename_task(task_name):
    """To be consistent with BIDS (no dashes)"""
    if task_name.startswith('bair_'):
        task_name = task_name[5:]

    task_name = task_name.replace('_', '')

    return task_name


def make_bids_name(bids_name, level=None):
    """
    Parameters
    ----------
    level : str
        'channels', 'electrodes', 'coordsystem', 'ieeg', 'physio'
    """
    appendix = ''
    acceptable_levels = ['sub', 'ses', 'task', 'run', 'acq', 'dir', 'rec']
    if level == 'channels':
        acceptable_levels = ['sub', 'ses', 'task', 'acq', 'run']
        appendix = '_channels.tsv'

    elif level == 'electrodes':
        acceptable_levels = ['sub', 'ses', 'acq', 'space']
        appendix = '_electrodes.tsv'

    elif level == 'coordsystem':
        acceptable_levels = ['sub', 'ses', 'acq', 'space']
        appendix = '_coordsystem.json'

    elif level in ('ieeg', 'eeg', 'meg'):
        acceptable_levels = ['sub', 'ses', 'task', 'acq', 'run']  # acq is not official https://neurostars.org/t/two-amplifiers-for-ieeg-recordings/17492
        appendix = f'_{level}.eeg'

    elif level == 'physio':
        acceptable_levels = ['sub', 'ses', 'task', 'run', 'recording']
        appendix = '_physio.tsv.gz'

    values = []
    for k, v in bids_name.items():
        if k in acceptable_levels and v is not None:
            values.append(str(v))

    return '_'.join(values) + appendix


def find_one_file(rec, formats):
    """formats has to be a list"""
    format_str = 'with formats (' + ', '.join(formats) + ')'
    found = []
    for file in rec.list_files():
        if file.format in formats:
            found.append(file)

    if len(found) == 0:
        lg.warning(f'No file {format_str} for {rec}')
        return None

    elif len(found) > 1:
        lg.warning(f'Too many files {format_str} for {rec}')
        _throw_msg_box("Error!", f"Too many files {format_str} for {rec}. Please remove incorrect recording file(s).")
        return None

    file = found[0]
    if not Path(file.path).exists():
        lg.warning(f'{rec} does not exist {format_str}')
        return None

    return file


def make_taskdescription(run):
    """This is only place I can think of where we can put information about
    performance and acquisition"""
    s = []

    FIELDS = [
        'task_description',
        'performance',
        'acquisition',
        ]

    for f in FIELDS:
        value = getattr(run, f)
        if value is not None:
            s.append(value)

    return '; '.join(s)


def add_extra_fields_to_json(run, fields, info):
    """Add extra fields to json file which are coming from subtables
    """
    db = run.db
    SUBTABLES = [x['subtable'] for x in db['subtables']]

    for col, tbl in collect_columns(db, obj=run).items():
        if tbl not in SUBTABLES:
            continue
        if db['tables'][tbl][col]['index']:
            continue

        key = db['tables'][tbl][col]['alias']
        fields[key] = getattr(run, col)
        if fields[key] is None:
            fields[key] = 'n/a'

        if key not in info:
            info[key] = {
                "Description": db['tables'][tbl][col]['doc'],
                }
            values = db['tables'][tbl][col]['values']
            if len(values) > 0:
                info[key]['Levels'] = {k: 'n/a' for k in values}

    return fields
