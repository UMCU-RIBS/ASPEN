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
