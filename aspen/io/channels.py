from PyQt5.QtWidgets import QInputDialog
from ..wonambi.dataset import Dataset
from aspen.api import Channels
from numpy import nan, array
from re import match

ECOG_PATTERN = r'([A-Za-z ]+)\d+'


def create_channels(db, ephys_path):
    if ephys_path.suffix.lower() == '.trc':
        return create_channels_trc(db, ephys_path)
    elif ephys_path.suffix.lower() == '.nev' or ephys_path.suffix.startswith('.ns'):
        return create_channels_blackrock(db, ephys_path)
    # ASP-91 Inclusion of channel import for bci2000 (and redwood)
    elif ephys_path.suffix.lower() == '.dat':
        return create_channels_bci2000(db, ephys_path)
    else:
        print(f'Cannot extract channel labels from {ephys_path}')


def create_channels_trc(db, trc_path):
    d = Dataset(trc_path)
    trc_chans = d.header['orig']['chans']

    # ASP-107 fixing the untitled entry when adding from import channel func
    _name_new_entry = _get_new_channel_group_name()

    chan = Channels.add_rec_file(db, str(trc_path), str(_name_new_entry))
    channels = chan.empty(len(trc_chans))  # original tries to create empty numpy array

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
    channels['reference'] = [ch['ground'] for ch in trc_chans]  # it's called ground but I'm pretty sure it's reference
    channels['groups'] = chan_groups
    channels['status'] = 'good'
    chan.data = channels

    # Keeping these in code for further checks.
    # chan.data = labels
    # return [labels, chan_types]
    return chan


def create_channels_blackrock(db, blackrock_path):
    if blackrock_path.suffix == '.nev':
        # ASP-91 Simple check to figure out if we need a .ns3 or .ns2, if we need a larger range of options use match.
        try:
            blackrock_path = blackrock_path.with_suffix('.ns3')
            d = Dataset(blackrock_path)
        except FileNotFoundError:
            blackrock_path = blackrock_path.with_suffix('.ns2')
            d = Dataset(blackrock_path)

    b_chans = d.header['orig']['ElectrodesInfo']

    # ASP-107 fixing the untitled entry when adding from import channel func
    _name_new_entry = _get_new_channel_group_name()

    chan = Channels.add_rec_file(db, str(blackrock_path), str(_name_new_entry))
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


# ASP-91 Dedicated channel function for BCI2000
def create_channels_bci2000(db, bci2000_path):
    """Bci2000 wasn't supported this will be the first attempt to allow for bci2000 to import channels from."""
    # TODO get rid of the Wonambi dependency there is a link in ASP-112, move wonambi to local func.
    d = Dataset(bci2000_path)
    bci2000_chans = d.header['chan_name']

    # ASP-107 fixing the untitled entry when adding from import channel func
    _name_new_entry = _get_new_channel_group_name()

    chan = Channels.add_rec_file(db, str(bci2000_path), str(_name_new_entry))
    channels = chan.empty(len(bci2000_chans))  # original tries to create empty numpy array

    channels['name'] = bci2000_chans
    channels['type'] = ''
    channels['units'] = ''
    channels['high_cutoff'] = None
    channels['low_cutoff'] = None
    channels['groups'] = ''
    channels['status'] = ''
    chan.data = channels
    return chan


def def_chan_type(label):
    if label == '':
        return 'OTHER'

    if match('[Rr][1-9]', label):
        return 'MISC'
    if label == '':
        return 'OTHER'  # TODO: empty?
    if label in ('MKR1+', 'MKR2+'):
        return 'TRIG'
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
    if label[:3].lower() == 'eog':
        return 'EOG'
    if label.startswith('el'):
        return 'OTHER'
    if label.startswith('x'):
        return 'OTHER'
    if label.endswith('+'):
        return 'OTHER'
    if label.endswith('-'):
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


def _get_new_channel_group_name() -> str:
    """Function that gives the user a input dialog when entering a new channel item through import > channels. The
    returned string will then be used as the name when entering into the database. This gets rid of any 'untitled'
    items from showing up in the widget."""
    _text, _ok = QInputDialog.getItem(
        None,
        f'Add new channel',
        'Select one',  # Label
        ["clinical-ECoG", "clinical_ECoG-SDE", "HD-ECoG", "sEEG", "clinical-HD-ECoG", "clinical-HD-ECoG-SDE"],
        0,  # Current
        False  # Editable
    )
    return _text
