from warnings import warn
from logging import getLogger
from re import sub

lg = getLogger(__name__)


def find_root(filename, target='bids'):
    """Find base directory (root) for a filename.

    Parameters
    ----------
    filename : instance of Path
        search the root for this file
    target: str
        'bids' (the directory containing 'participants.tsv'), 'subject' (the
        directory starting with 'sub-'), 'session' (the directory starting with
        'ses-')

    Returns
    -------
    Path
        path of the target directory
    """
    lg.debug(f'Searching root in {filename}')
    if target == 'bids' and (filename / 'dataset_description.json').exists():
        return filename
    elif filename.is_dir():
        pattern = target[:3] + '-'
        if filename.stem.startswith(pattern):
            return filename

    return find_root(filename.parent, target)


def find_in_bids(filename, pattern=None, generator=False, upwards=False,
                 wildcard=True, **kwargs):
    """Find nearest file matching some criteria.

    Parameters
    ----------
    filename : instance of Path
        search the root for this file
    pattern : str
        glob string for search criteria of the filename of interest (remember
        to include '*'). The pattern is passed directly to rglob.
    wildcard : bool
        use wildcards for unspecified fields or not (if True, add "_*_" between
        fields)
    upwards : bool
        where to keep on searching upwards
    kwargs : dict


    Returns
    -------
    Path
        filename matching the pattern
    """
    if upwards and generator:
        raise ValueError('You cannot search upwards and have a generator')

    if pattern is None:
        pattern = _generate_pattern(wildcard, kwargs)

    lg.debug(f'Searching {pattern} in {filename}')

    if upwards and filename == find_root(filename):
        raise FileNotFoundError(f'Could not find file matchting {pattern} in {filename}')

    if generator:
        return filename.rglob(pattern)

    matches = list(filename.rglob(pattern))
    if len(matches) == 1:
        return matches[0]

    elif len(matches) == 0:
        if upwards:
            return find_in_bids(filename.parent, pattern=pattern, upwards=upwards)
        else:
            raise FileNotFoundError(f'Could not find file matchting {pattern} in {filename}')

    else:
        matches_str = '"\n\t"'.join(str(x) for x in matches)
        raise FileNotFoundError(f'Multiple files matching "{pattern}":\n\t"{matches_str}"')


def _generate_pattern(wildcard, kwargs):

    if not wildcard and 'subject' not in kwargs:
        raise ValueError('You need to specify "subject" if you do not use any wildcard')

    unknown = set(kwargs) - set(['subject', 'session', 'task', 'run', 'acquisition', 'modality', 'extension'])
    if len(unknown) > 0:
        warn('Unrecognized type ' + ', '.join([f'"{x}"' for x in unknown]))

    if 'subject' in kwargs:
        pattern = 'sub-' + kwargs['subject']
    else:
        pattern = '*'

    if 'session' in kwargs:
        pattern += '_ses-' + kwargs['session'] + '_'
    elif wildcard:
        pattern += '_*'

    if 'task' in kwargs:
        pattern += '_task-' + kwargs['task'] + '_'
    elif wildcard:
        pattern += '_*'

    if 'run' in kwargs:
        pattern += '_run-' + kwargs['run'] + '_'
    elif wildcard:
        pattern += '_*'

    if 'acquisition' in kwargs:
        pattern += '_acq-' + kwargs['acquisition'] + '_'
    elif wildcard:
        pattern += '_*'

    if 'modality' in kwargs:
        pattern += '_' + kwargs['modality']
    elif wildcard:
        pattern += '_*'

    if 'extension' in kwargs:
        pattern += kwargs['extension']
    else:
        pattern += '.*'

    pattern = sub('(_\*)+', '_*', pattern)
    pattern = sub('(\*_)+', '*_', pattern)
    pattern = pattern.replace('__', '_')

    return pattern
