from datetime import timedelta, datetime
from ..nibabel.parrec import parse_PAR_header
from numpy import round


def add_parrec(par_file, sess=None, run=None, recording=None, update=False):
    """Parse information from PAR file to a session, run or recording

    Parameters
    ----------
    par_file : path
        path to PAR file
    sess : instance of Session

    run : instance of Run

    recording : instance of Recording

    update : bool
        do not add file. The function was called when the file is already
        linked and we just update run and recording
    """
    hdr, image = parse_PAR_header(par_file.open())

    info = _get_MRI_info(hdr)
    if not info:
        return

    exam_date = datetime.strptime(hdr['exam_date'], '%Y.%m.%d / %H:%M:%S')
    # There is no time for individual runs, so we estimate an average duration of 4 minutes
    start_time = exam_date + timedelta(seconds=4 * 60 * hdr['acq_nr'])

    if run is None:
        run = sess.add_run(info['task_name'])
    elif run.task_name == 'rest':  # only change task_name if rest (default)
        run.task_name = info['task_name']

    if run.start_time is None:
        run.start_time = start_time

    if info['task_name'] == 'motor':
        if run.left_right is None:
            run.left_right = info['left_right']
        if run.body_part is None:
            run.body_part = info['body_part']

    if recording is None:
        recording = run.add_recording(info['modality'])
    else:
        recording.modality = info['modality']

    if not update:
        recording.add_file('parrec', par_file)

    n_dyns = image['dynamic scan number'].max()
    if n_dyns == 1:
        duration = hdr['scan_duration']
        TR = 0

    else:
        TR = image['dyn_scan_begin_time'].max() / (n_dyns - 1)
        TR = round(TR, decimals=3)
        duration = image['dyn_scan_begin_time'].max() + TR

    run.duration = duration
    if run.acquisition is None:
        run.acquisition = hdr['protocol_name']
    if info['modality'] == 'bold':
        recording.RepetitionTime = TR


def _get_MRI_info(hdr):
    info = {}
    protocol = hdr['protocol_name'].lower()

    if 't2s' in protocol:
        info['task_name'] = 't2star_anatomy_scan'
        info['modality'] = 'T2star'

    elif 'mansfield' in protocol or 'anat' in protocol or 't1' in protocol:
        info['task_name'] = 't1_anatomy_scan'
        info['modality'] = 'T1w'

    elif 'flair' in protocol:
        info['task_name'] = 'flair_anatomy_scan'
        info['modality'] = 'FLAIR'

    elif 'dti' in protocol:
        info['task_name'] = 'DTI'
        info['modality'] = 'dwi'

    elif ('circle' in protocol) or ('motor' in protocol):
        info['task_name'] = 'motor'
        info['modality'] = 'bold'
        info['body_part'] = None
        info['left_right'] = None

        if 'tongue' in protocol:
            info['body_part'] = 'tongue'
            info['left_right'] = 'both'
        elif 'tong' in protocol:
            info['body_part'] = 'tongue'
            info['left_right'] = 'both'
        elif 'motorlhand' in protocol:
            info['body_part'] = 'hand'
            info['left_right'] = 'left'
        elif 'motorrhand' in protocol:
            info['body_part'] = 'hand'
            info['left_right'] = 'right'
        elif 'motorlfeet' in protocol:
            info['body_part'] = 'foot'
            info['left_right'] = 'left'
        elif 'motorrfeet' in protocol:
            info['body_part'] = 'foot'
            info['left_right'] = 'right'
        elif 'senslhand' in protocol:
            info['body_part'] = 'hand'
            info['left_right'] = 'left'
            info['task_name'] = 'somatosensory'
        elif 'sensrhand' in protocol:
            info['body_part'] = 'hand'
            info['left_right'] = 'right'
            info['task_name'] = 'somatosensory'
        else:
            print(f'Unknown bodypart {protocol}')

    elif ('picnam' in protocol):
        info['task_name'] = 'picnam'
        info['modality'] = 'bold'

    elif ('verbgen' in protocol):
        info['task_name'] = 'verb'
        info['modality'] = 'bold'

    elif ('chill' in protocol):
        info['task_name'] = 'chill'
        info['modality'] = 'bold'

    elif ('calc' in protocol):
        info['task_name'] = 'calc'
        info['modality'] = 'bold'

    elif ('story' in protocol):
        info['task_name'] = 'story'
        info['modality'] = 'bold'

    elif ('syllables' in protocol):
        info['task_name'] = 'syllables'
        info['modality'] = 'bold'

    elif ('angio' in protocol):
        info['task_name'] = 'angiography_scan'
        info['modality'] = 'angio'

    elif ('pd' in protocol):
        info['task_name'] = 'pd_anatomy_scan'
        info['modality'] = 'PD'

    elif 'fa27' in protocol:
        pass

    else:
        print(f'could not parse {hdr["protocol_name"]}, so calling it "rest". PLEASE FIX IT')
        info['task_name'] = 'rest'
        info['modality'] = 'bold'

    return info
