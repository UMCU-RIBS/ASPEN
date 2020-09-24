import gzip
from json import dump
from logging import getLogger

from bidso.utils import replace_extension
from .utils import make_bids_name
from .io.dataglove import parse_dataglove_log
from .io.pulse_and_resp_scanner import parse_scanner_physio

lg = getLogger(__name__)


def convert_physio(rec, dest_path, name):
    """Convert physiological signal to BIDS format.

    Parameters
    ----------
    rec : instance of Recording
        recording of type 'physio' (like dataglove or heart rate)
    dest_path : path
        full path to modality folder
    name : dict
        dictionary with parts to make bids name

    Notes
    -----
    StartTime in the .json file gives the offset from the start of the recording.
    If the tsv contains a "time" column, the "time" info is already aligned
    with the recording (so you don't need to add StartTime.
    """
    for file in rec.list_files():
        if file.format == 'dataglove':
            name['rec'] = 'rec-dataglove'
            tsv, hdr = parse_dataglove_log(file.path)

        elif file.format == 'scanphyslog':
            name['rec'] = 'rec-resp'
            tsv, hdr = parse_scanner_physio(file.path)

        else:
            return

        hdr['StartTime'] = rec.offset
        if 'time' in tsv.columns:
            tsv['time'] += rec.offset

    if name['rec'] is None:
        lg.warning(f'No file associated with physio recording')
        return

    physio_tsv = dest_path / f'{make_bids_name(name)}_physio.tsv.gz'
    _write_physio(tsv, physio_tsv)

    physio_json = replace_extension(physio_tsv, '.json')
    with physio_json.open('w') as f:
        dump(hdr, f, indent=2)


def _write_physio(physio, physio_tsv):

    content = physio.to_csv(sep='\t', index=False, header=False, float_format='%.3f')
    with gzip.open(physio_tsv, 'wb') as f:
        f.write(content.encode())
