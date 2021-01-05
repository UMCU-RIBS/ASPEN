from wonambi import Dataset
from xelo2.api import Channels
from numpy import nan, array
from re import match

ECOG_PATTERN = r'([A-Za-z ]+)\d+'


def create_channels(db, ephys_path):
    if ephys_path.suffix.lower() == '.trc':
        return create_channels_trc(db, ephys_path)
    elif ephys_path.suffix.lower() == '.nev' or ephys_path.suffix.startswith('.ns'):
        return create_channels_blackrock(db, ephys_path)
    else:
        print(f'Cannot extract channel labels from {ephys_path}')


def create_channels_trc(db, trc_path):
    d = Dataset(trc_path)
    trc_chans = d.header['orig']['chans']

    chan = Channels.add(db)
    channels = chan.empty(len(trc_chans))

    labels = [ch['chan_name'] for ch in trc_chans]
    chan_types = [def_chan_type(label) for label in labels]
    chan_groups = def_groups(labels, chan_types)

    channels['name'] = labels
    channels['type'] = chan_types
    channels['units'] = [ch['units'].replace('dimentionless', '') for ch in trc_chans]
    channels['high_cutoff'] = [ch['HiPass_Limit'] / 1000 for ch in trc_chans]
    low_cutoff = array([ch['LowPass_Limit'] / 1000 for ch in trc_chans])
    low_cutoff[low_cutoff == 0] = nan
    channels['low_cutoff'] = low_cutoff
    channels['reference'] = [ch['ground'] for ch in trc_chans]  # it's called ground but I'm pretty sure it's the reference
    channels['groups'] = chan_groups
    channels['status'] = 'good'

    chan.data = channels

    return chan


def create_channels_blackrock(db, blackrock_path):
    if blackrock_path.suffix == '.nev':
        blackrock_path = blackrock_path.with_suffix('.ns3')
    d = Dataset(blackrock_path)
    b_chans = d.header['orig']['ElectrodesInfo']

    chan = Channels.add(db)
    channels = chan.empty(len(b_chans))

    labels = [ch['Label'] for ch in b_chans]

    channels['name'] = labels
    channels['type'] = 'ECOG'
    channels['units'] = [ch['AnalogUnits'].replace('uV', 'μV') for ch in b_chans]
    channels['high_cutoff'] = [ch['HighFreqCorner'] / 1000 for ch in b_chans]
    channels['low_cutoff'] = [ch['LowFreqCorner'] / 1000 for ch in b_chans]
    channels['groups'] = 'HD'
    channels['status'] = 'good'

    chan.data = channels

    return chan


def def_chan_type(label):
    if label == '':
        return 'OTHER'

    if match('[Rr][1-9]', label):
        return 'MISC'
    if label == '':
        return 'OTHER'  # TODO: empty?
    if label.endswith('+'):
        return 'OTHER'
    if label.endswith('-'):
        return 'OTHER'
    if '...' in label:
        return 'OTHER'
    if label.lower() in ('wangl', 'wangr'):
        return 'MISC'
    if label.lower().startswith('ah'):
        return 'ECG'
    if label.lower().startswith('ecg'):
        return 'ECG'
    if label.lower().startswith('ekg'):
        return 'ECG'
    if label[:3].lower() in ('kin', 'emg', 'arm', 'nek') or label == 'MOND':
        return 'EMG'
    if label[:3].lower() == 'orb':
        return 'EOG'
    if label.startswith('el'):
        return 'OTHER'
    if label.startswith('x'):
        return 'OTHER'
    if label.startswith('D'):
        return 'SEEG'

    if match(ECOG_PATTERN, label):
        return 'ECOG'
    else:
        return 'OTHER'


def def_groups(labels, chan_types):

    groups = _make_groups(labels, chan_types)

    return [_choose_group(label, groups) for label in labels]


select_letters = lambda label: match(ECOG_PATTERN, label).group(1)


def _make_groups(labels, chan_types):
    group_names = {select_letters(label) for label, chan_type in zip(labels, chan_types) if chan_type in ('ECOG', 'SEEG')}

    groups = {}
    for group_name in group_names:
        groups[group_name] = [label for label, chan_type in zip(labels, chan_types) if chan_type in ('ECOG', 'SEEG') and select_letters(label) == group_name]

    return groups


def _choose_group(label, groups):

    for k, v in groups.items():
        if label in v:
            return k

    return 'n/a'
