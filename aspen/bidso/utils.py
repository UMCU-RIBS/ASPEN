from logging import getLogger
from pathlib import Path
from re import search

try:
    import numpy
except ImportError:
    numpy = False

lg = getLogger(__name__)


def read_tsv(filename):
    filename = Path(filename)
    if numpy:
        tsv = numpy.genfromtxt(
            fname=filename,
            delimiter='\t',
            names=True,
            dtype=None,  # forces it to read strings
            deletechars='',
            encoding='utf-8')

    else:
        with filename.open(encoding='utf-8') as f:
            hdr = f.readline()
            tsv = []
            for l in f:
                d = {k.strip(): v.strip() for k, v in zip(hdr.split('\t'), l.split('\t'))}
                tsv.append(d)

    return tsv


def find_extension(filename):
    if isinstance(filename, Path):
        filename = filename.name

    return '.' + '.'.join(filename.split('.')[1:])


def add_extension(filename, suffix):
    if isinstance(filename, str):
        return filename + suffix
    else:
        return filename.parent / (filename.name + suffix)


def replace_extension(filename, suffix):
    return add_extension(remove_extension(filename), suffix)


def remove_extension(filename):
    if isinstance(filename, str):
        return filename.split('.')[0]
    else:
        return filename.parent / filename.name.split('.')[0]


def add_underscore(filename, suffix):
    if isinstance(filename, str):
        return filename + '_' + suffix
    else:
        return filename.parent / (filename.name + '_' + suffix)


def replace_underscore(filename, suffix):
    return add_underscore(remove_underscore(filename), suffix)


def remove_underscore(filename):
    if isinstance(filename, str):
        return '_'.join(filename.split('_')[:-1])
    else:
        return filename.parent / ('_'.join(filename.name.split('_')[:-1]))


def bids_mkdir(base_path, file_bids):

    output_path = base_path / ('sub-' + file_bids.subject)
    output_path.mkdir(exist_ok=True)
    if file_bids.session is not None:  # hasattr for pybids, isnone for bidso
        output_path = output_path / ('ses-' + file_bids.session)
        output_path.mkdir(exist_ok=True)

    output_path = add_modality(output_path, file_bids.modality)
    output_path.mkdir(exist_ok=True)

    return output_path


def add_modality(output_path, modality):
    """Modality can be appended to the file name (such as 'bold') or use in the
    folder (such as "func"). You should always use the specific modality ('bold').
    This function converts it to the folder name.
    """
    if modality is None:
        return output_path
    else:
        if modality == 'T1w':
            modality = 'anat'

        elif modality == 'bold':
            modality = 'func'

        elif modality == 'epi':  # topup
            modality = 'fmap'

        elif modality in ('electrodes', 'coordsystem', 'channels'):
            modality = 'ieeg'

        elif modality == 'events':
            raise ValueError('modality "events" is ambiguous (can be in folder "ieeg" or "func"). Assuming "ieeg"')

        return output_path / modality


def _match(filename, pattern):
    m = search(pattern, filename.stem)
    if m is None:
        return m
    else:
        return m.group(1)
