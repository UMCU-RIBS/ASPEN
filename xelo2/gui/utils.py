from xelo2.api.utils import sort_data_created


def _protocol_name(protocol):
    if protocol.metc == 'Request from clinic':
        return 'Request from clinic'
    elif protocol.date_of_signature is None:
        date_str = 'unknown date'
    else:
        date_str = f'{protocol.date_of_signature:%d %b %Y}'
    return f'{protocol.metc} ({date_str})'


def _name(name):
    if name is None:
        return '(untitled)'
    else:
        return name


def _session_name(sess):
    extra = ''
    if sess.name == 'MRI':
        extra = f'{sess.MagneticFieldStrength} '

    # XEL-57 bci patients should use data of creation instead of start_time
    if sess.start_time is None and sess.name != 'BCI':
        date_str = 'unknown date'
    elif sess.name == 'BCI':
        date_str = f'{sess.data_created: %d %b %Y}'
    else:
        date_str = f'{sess.start_time:%d %b %Y}'
    return f'{extra}{sess.name} ({date_str})'


# XEL-60 need a util function for sorting BCI sessions as they tend not to utilize start_time but data_created
def _sort_session_bci(bci_sessions: list) -> list:
    """Return a sorted list based on db.session_bci.data_created timestamp."""
    return sorted(bci_sessions, key=sort_data_created)


# ASP-64
def _check_session_bci(session_name) -> bool:
    """Internal function to quickly check if we are dealing with a BCI session, returns true if bci else false."""
    if session_name == 'BCI':
        return True
    else:
        return False


# ASP-64 Internal function to allow for removing a field from a dictionary
def _session_bci_hide_fields(dict_params: dict):
    """Function to mark which fields should be hidden when dealing with BCI sessions. Certain fields are not used by
    the BCI sessions. Theses are fields shown on the parameters section of the interface."""
    field = 'Xelo Stem'
    if field in dict_params:
        del dict_params[field]


def guess_modality(run):
    task_name = run.task_name
    if task_name in ('t1_anatomy_scan', 'MP2RAGE'):
        return 'T1w'
    if task_name == 't2_anatomy_scan':
        return 'T2w'
    if task_name == 't2star_anatomy_scan':
        return 'T2star'
    if task_name == 'pd_anatomy_scan':
        return 'PD'
    if task_name == 'ct_anatomy_scan':
        return 'ct'
    if task_name == 'flair_anatomy_scan':
        return 'FLAIR'
    if task_name == 'angiography_scan':
        return 'angio'
    if task_name == 'top_up':
        return 'epi'
    if task_name == 'DTI':
        return 'dwi'

    sess_name = run.session.name
    if sess_name in ('IEMU', 'OR'):
        return 'ieeg'
    if sess_name == 'MRI':
        return 'bold'
