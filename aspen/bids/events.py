from ..io.tsv import save_tsv
from .utils import make_bids_name


def convert_events(run, dest_path, name):
    events_tsv = dest_path / f'{make_bids_name(name)}_events.tsv'

    save_tsv(events_tsv, run.events, ['onset', 'duration'])
