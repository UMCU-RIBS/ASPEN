from wonambi.ioeeg import BlackRock
from numpy import empty, around
from datetime import timedelta

from .utils import localize_blackrock
from .events import read_events_from_ephys
from ..api.utils import get_dtypes
from ..api.filetype import parse_filetype


def add_ephys_to_sess(db, sess, ephys_file):
    """default task is NOTE, but TODO decode task from triggers"""

    info = read_info_from_ephys(db, ephys_file)

    # default task is NOTE
    run = sess.add_run('NOTE')
    run.start_time = info['start_time']
    run.duration = info['duration']
    rec = run.add_recording('ieeg')
    rec.Manufacturer = info['manufacturer']
    filetype = parse_filetype(ephys_file)
    file = rec.add_file(filetype, ephys_file)

    events = read_events_from_ephys(file, run, rec)
    if len(events) > 0:
        run.events = events

    return run


def read_info_from_ephys(db, path_to_file):

    d = localize_blackrock(path_to_file)
    mrk = d.read_markers()

    DTYPES = get_dtypes(db['tables']['events'])
    ev = empty(len(mrk), dtype=DTYPES)
    ev['onset'] = [around(x['start'], decimals=3) - 0.001 for x in mrk]
    ev['duration'] = [around(x['end'] - x['start'], decimals=3) for x in mrk]
    ev['value'] = [x['name'] for x in mrk]

    if d.IOClass == BlackRock:
        manufacturer = 'BlackRock'
    else:
        manufacturer = 'Micromed'

    info = {
        'start_time': d.header['start_time'] + timedelta(seconds=0.001),
        'duration': (d.header['n_samples']) / d.header['s_freq'] - 0.001,  # add -1 to avoid rounding errors that generate NaN when converting
        'events': ev,
        'manufacturer': manufacturer,
        }
    return info
