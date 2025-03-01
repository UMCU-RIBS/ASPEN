"""Convenient functions to interact with the RESPECT folder"""
from bidso.utils import read_tsv
from ..api.frontend import list_subjects


def assign_respect_code(RESPECT_DIR):
    """Assign RESPECT code to subjects in this database.
    """
    RESP = collect_RESP_channels(RESPECT_DIR)

    for subj in list_subjects():
        if [x for x in subj.codes if x.startswith('RESP')]:
            continue

        print(str(subj))
        resp_subj = find_resp_subject(subj, RESP)
        if resp_subj is not None:
            print(f'\tAdding {resp_subj} to {str(subj)}')
            try:
                subj.codes = subj.codes + [resp_subj[4:], ]  # without "sub-"
            except ValueError as err:
                print(err)


def find_resp_subject(subj, RESP):
    """Find if there is one matching subject in RESPECT database based on
    the channel names"""
    matching_subj = []
    sessions = [x for x in subj.list_sessions() if x.name == 'IEMU']
    for sess in sessions:
        for chan in sess.list_channels():
            matched = find_resp_channels(chan, RESP)
            matching_subj.extend(matched)

    if len(matching_subj) == 1:
        return matching_subj[0]
    elif len(matching_subj) == 0:
        return None
    else:
        print(f'\tfound {len(matching_subj)} in RESP')
        return None


def find_resp_channels(chan, RESP, n_chan=128):
    """Loop over RESPECT list of channels searching for all the matches.
    Because channel names might change during the same acquisition, you can
    specify to use fewer channels (but this increases the chances of matching
    the wrong RESPECT subject)"""

    subj_chan = list(chan.data['name'])

    matching_subj = []
    for resp_subj, resp_chan in RESP.items():
        if subj_chan[:n_chan] == resp_chan[:n_chan]:
            matching_subj.append(resp_subj)

    return matching_subj


def collect_RESP_channels(RESPECT_DIR):
    """Collect all the channels for all the subjects in the RESPECT_DIR
    """
    RESP = {}
    for subject in RESPECT_DIR.glob('sub-RESP*'):
        try:
            channels = next(subject.rglob('*_channels.tsv'))
        except StopIteration:
            continue
        RESP[subject.stem] = list(read_tsv(channels)['name'])

    return RESP
