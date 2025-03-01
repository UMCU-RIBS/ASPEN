from numpy import empty
from wonambi.dataset import UnrecognizedFormat
from sys import maxsize
from logging import getLogger
from .utils import localize_blackrock
from ..api.utils import get_dtypes

lg = getLogger(__name__)


def read_events_from_ephys(file, run=None, rec=None, db=None):
    """Read events from ephys file. If you specify both run and rec, then it only
    read the events in the period inside the run period

    Parameters
    ----------
    file : File
        instance of File
    run : Run
        instance of Run
    rec : Recording
        instance of Recording
    db : database
        only necessary if you don't specify run

    Notes
    -----
    Make sure that rec.onset is in the good direction
    """
    try:
        d = localize_blackrock(file.path)
    except UnrecognizedFormat:
        lg.warning(f'cannot parse poorly edited BCI2000 file ({file.path})')
        return None
    except FileNotFoundError:
        lg.warning(f'{file.path} does not exist')
        return None

    markers = d.read_markers()

    if run is None:
        start_t = 0
    else:
        start_t = (run.start_time - d.header['start_time']).total_seconds() + rec.offset
        if run.duration is not None:
            end_t = start_t + run.duration
        else:
            end_t = maxsize

        markers = [m for m in markers if start_t <= m['start'] <= end_t]

    if run is not None:
        DTYPES = run.events.dtype
    else:
        DTYPES = get_dtypes(db['tables']['events'])

    events = empty(len(markers), dtype=DTYPES)
    events['value'] = [m['name'] for m in markers]
    events['onset'] = [m['start'] - start_t for m in markers]
    events['duration'] = 0

    return events


def find_eegfile_in_run(run):
    for rec in run.list_recordings():
        for file in rec.list_files():
            if file.format in ('micromed', 'bci2000', 'blackrock'):
                return rec, file
    return None, None
