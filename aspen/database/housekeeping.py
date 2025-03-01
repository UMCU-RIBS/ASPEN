from logging import getLogger
from pathlib import Path
from numpy import isin

from PyQt5.QtSql import QSqlQuery

from ..io.ephys import read_info_from_ephys
from ..io.channels import create_channels
from ..io.electrodes import import_electrodes
from ..api import Electrodes


lg = getLogger(__name__)


def add_allowed_value(db, table, column, value):
    """Add allowed value for a table/column

    Parameters
    ----------
    db : dict
        information about database
    table : str
        one of the tables
    column : str
        one of the columns in the table
    value : str
        value to add
    """
    if table not in db['tables']:
        raise ValueError(f'Table "{table}" not found in the list of tables')
    if column not in db['tables'][table]:
        raise ValueError(f'Column "{column}" not found in the list of columns of table "{table}"')

    query = QSqlQuery(db['db'])
    query.prepare("INSERT INTO `allowed_values` (`table_name`, `column_name`, `allowed_value`) VALUES (:table, :column, :value)")
    query.bindValue(':table', table)
    query.bindValue(':column', column)
    query.bindValue(':value', value)
    if not query.exec():
        raise SyntaxError(query.lastError().text())

    lg.warning('Value correctly added. Changes will take place immediately for SQL, but GUI is not updated until you restart aspen')


def recap(subj, sess, run, trial_type='speech'):
    df = {}

    df['subject'] = str(subj)
    df['start_time'] = run.start_time

    metc = subj.list_protocols()
    if len(metc) == 0:
        df['has_metc'] = False
        df['has_metc_date'] = False
    else:
        df['has_metc'] = True
        df['has_metc_date'] = any([x.date_of_signature for x in metc])

    df['has_duration'] = True if run.duration is not None else False
    events = run.events
    df['n_events'] = events.shape[0]
    df['has_events_type'] = trial_type in events['trial_type']

    recordings = run.list_recordings()
    if len(recordings) == 0:
        df['has_recording'] = False
        df['has_file'] = False
        df['is_micromed'] = False
        df['has_channels'] = False
        df['has_electrodes'] = False
        df['has_t1w_for_elec'] = False

    else:
        df['has_recording'] = True
        if len(recordings) > 1:
            print('number of recordings')
        rec = recordings[0]

        files = rec.list_files()
        if len(files) == 1:
            df['has_file'] = True
            df['is_micromed'] = True if files[0].format == 'micromed' else False

        else:
            df['has_file'] = False
            df['is_micromed'] = False

        df['has_channels'] = True if rec.channels is not None else False

        elec = rec.electrodes
        df['has_electrodes'] = True if elec is not None else False
        if elec is not None and elec.intendedFor is not None:
            df['has_t1w_for_elec'] = True
        else:
            df['has_t1w_for_elec'] = False

    return df


def add_recording(run):
    recs = run.list_recordings()
    if len(recs) == 0:
        print('adding recording')
        return run.add_recording('ephys')
    elif len(recs) == 1:
        print('getting recording')
        return recs[0]
    else:
        raise ValueError('too many recordings')


def add_ephys_info(run, micromed_path):
    ephys = read_info_from_ephys(Path(micromed_path))
    print(ephys['start_time'])
    print(ephys['duration'])
    print(f"# events: {ephys['events'].shape[0]}")
    output = input('ok (y/n)?')
    if output == 'y':
        run.start_time = ephys['start_time']
        run.duration = ephys['duration']
        run.events = ephys['events']


def set_channels(sess, rec):

    if len(sess.list_channels()) == 0:
        chan = None
        for ephys_path in rec.list_files():
            if ephys_path.format == 'micromed':
                chan = create_channels(ephys_path.path)
                break
        if chan is None:
            return
        print('creating channels')
        chan.name = 'clinical'

    elif len(sess.list_channels()) == 1:
        chan = sess.list_channels()[0]

    else:
        raise ValueError('too many channels')

    print('setting channels')
    rec.attach_channels(chan)


def remove_bci2000(rec):
    print('removing bci2000')
    for file in rec.list_files():
        if file.format == 'bci2000':
            rec.delete_file(file)


def add_events_type(run):
    print('adding event types')
    EVENTS_TYPE = [
        'task start',
        'music',
        'speech',
        'music',
        'speech',
        'music',
        'speech',
        'music',
        'speech',
        'music',
        'speech',
        'music',
        'speech',
        'music',
        'task end'
        ]
    events = run.events
    if events.shape[0] == 15:
        events['trial_type'] = EVENTS_TYPE
    elif events.shape[0] == 16:
        events['trial_type'][1:] = EVENTS_TYPE
    else:
        raise ValueError(f'number of events {events.shape[0]}')

    run.events = events


def attach_electrodes(sess, rec, mat_file=None, idx=None):
    if len(sess.list_electrodes()) == 0:
        elec = create_electrodes(rec, mat_file, idx)
        if elec is None:
            raise ValueError('cannot create electrodes')
    elif len(sess.list_electrodes()) == 1:
        elec = sess.list_electrodes()[0]
    else:
        raise ValueError('too many electrodes')

    rec.attach_electrodes(elec)


def create_electrodes(rec, mat_file, idx=None):
    chan = rec.channels
    chan_data = chan.data
    if idx is None:
        idx = isin(chan_data['type'], ('ECOG', 'SEEG'))

    n_chan = idx.sum()
    print(f'# of ECOG/SEEG channels for this recording: {n_chan}')

    xyz = import_electrodes(mat_file, n_chan)
    if xyz is None:
        print('you need to do this manually')
        return

    elec = Electrodes()
    elec_data = elec.empty(n_chan)
    elec_data['name'] = chan_data['name'][idx]
    elec_data['x'] = xyz[:, 0]
    elec_data['y'] = xyz[:, 1]
    elec_data['z'] = xyz[:, 2]
    elec.data = elec_data

    return elec
