from itertools import chain
from bidso.utils import replace_underscore
from json import dump
from re import sub, match

from .utils import rename_task, prepare_subset
from ..api import Subject


TASK_TYPES = {  # use original names, they'll get converted to bids-compliant names later
    'visual': [
        'bair_spatialobject',
        'bair_spatialpattern',
        'bair_temporalpattern',
        'bair_prf',
        'bair_hrfpattern',
        ],
    'motor': [
        'finger_mapping',
        'gestures',
        'boldfinger',
        'boldsat',
        ],
    'tactile': [
        'vts_prf',
        'vts_temporalpattern',
        ],
    }


def make_bair_compatible(bids_dir):

    add_umcu_to_sub_ses(bids_dir)
    add_info_to_participants(bids_dir)
    print('check if it"s necessary to add electrodes here as well')
    # add_electrodes(bids_dir)


def add_umcu_to_sub_ses(bids_dir):

    TEXT_FILES = chain(
        bids_dir.glob('**/*.tsv'),
        bids_dir.glob('**/*.vhdr'),
        bids_dir.glob('**/*.vmrk'),
        bids_dir.glob('**/*.json'),
        )

    for tsv_file in TEXT_FILES:
        with tsv_file.open() as f:
            txt = f.read()
        txt = sub('sub-(?!umcu)', 'sub-umcu', txt)
        txt = sub('ses-', 'ses-umcu', txt)
        with tsv_file.open('w') as f:
            f.write(txt)

    for subj_path in bids_dir.glob('sub-*'):
        new_subj_path = subj_path.parent / sub('sub-(?!umcu)', 'sub-umcu', subj_path.name)
        subj_path.rename(new_subj_path)

        for sess_path in new_subj_path.glob('ses-*'):
            new_sess_path = sess_path.parent / sub('ses-', 'ses-umcu', sess_path.name)
            sess_path.rename(new_sess_path)

    for old_file in bids_dir.glob('**/*.*'):
        new_name = sub('sub-(?!umcu)', 'sub-umcu', old_file.name)
        new_name = sub('ses-', 'ses-umcu', new_name)
        old_file.rename(old_file.parent / new_name)


def add_info_to_participants(bids_path):
    """Add some additional information to participants"""
    tsv_file = bids_path / 'participants.tsv'
    with tsv_file.open() as f:
        txt = []
        hdr = f.readline()
        txt.append(hdr[:-1] + '\tsite\thigh_density_grid\tvisual\tmotor\ttactile\tacq_date_shift')

        for line in f:
            subj = line.split('\t')[0]
            txt.append(
                line[:-1]
                + '\tUMCU'
                + '\t'
                + _find_hdgrid(bids_path / subj)
                + '\t'
                + _find_task_type(bids_path / subj, 'visual')
                + '\t'
                + _find_task_type(bids_path / subj, 'motor')
                + '\t'
                + _find_task_type(bids_path / subj, 'tactile')
                + '\t0'
                )

    with tsv_file.open('w') as f:
        f.write('\n'.join(txt))


def add_electrodes(bids_dir):

    for bids_ieeg in bids_dir.glob('**/*_ieeg.eeg'):
        _add_empty_elec(bids_ieeg)
        _add_coordsystem(bids_ieeg)

def _add_empty_elec(bids_ieeg):
    elec_file = replace_underscore(bids_ieeg, 'electrodes.tsv')
    if not elec_file.exists():
        with elec_file.open('w') as f:
            f.write('name\tx\ty\tz\tsize\tmaterial\tmanufacturer\tgroup\themisphere\ttype\timpedance\tdimension')


def _add_coordsystem(bids_ieeg):
    D = {
        "iEEGCoordinateSystem": "other",
        "iEEGCoordinateSystemDescription": "native T1w",
        "iEEGCoordinateUnits": "mm",
        "iEEGCoordinateProcessingDescription": "surface_projection",
        "iEEGCoordinateProcessingReference": "PMID: 19836416"
        }

    anat_dir = bids_ieeg.parents[2] / 'ses-umcu3t1' / 'anat'
    anat_t1w = list(anat_dir.glob('*_run-1_T1w.nii.gz'))
    if len(anat_t1w) != 1:
        print(f'{len(anat_t1w)} T1w images found in {anat_dir}')

    else:
        anat_t1w = anat_t1w[0]
        D['IntendedFor'] = str(anat_t1w.relative_to(anat_t1w.parents[3]))

    coordsys_file = replace_underscore(bids_ieeg, 'coordsystem.json')
    with coordsys_file.open('w') as f:
        dump(D, f, indent=2)


def _find_hdgrid(subj_path):
    if match(r'sub-umcu\d+', subj_path.stem):
        return 'n/a'

    if len(list(subj_path.rglob('*/*/*_acq-HD*'))) > 0:
        return 'yes'

    return 'no'

def _find_task_type(subj_path, task_type):
    for t in TASK_TYPES[task_type]:
        t_bids = rename_task(t)
        if len(list(subj_path.rglob(f'*/*/*_task-{t_bids}_*'))) > 0:
            return 'yes'

    return 'no'


def list_bair_ids(db, healthy_visual=True, subset=None, public=False):
    """Collect all the subjects, sessions and runs for the BAIR project. This is
    all the subjects that did BAIR tasks since 2016 excluding a couple of
    subjects.

    Parameters
    ----------
    db : instance of Sql database
        database currently open
    healthy_visual : bool
        whether to include the healthy participants who did visual tasks
    subset : dict with {'subjects', 'sessions', 'runs'}
        runs selected previously
    public : bool
        if True, it uses only subjects that can be publicly shared

    Returns
    -------
    dict with {'subjects', 'sessions', 'runs'}
        ids for subjects, sessions, runs which are part of the BAIR tasks
    """
    healthy_visual_subjects = [f'umcu{x + 1:04d}' for x in range(13)]
    healthy_visual_ids = ', '.join(f'"{Subject(db, x).id}"' for x in healthy_visual_subjects)

    subjects_to_skip = healthy_visual_subjects.copy()
    subjects_to_skip.extend([
        'bunnik',  # patient / finger_mapping at 7T
        'veendam',  # patient / finger_mapping at 7T
        ])
    if public:
        subjects_to_skip.extend([
            'boskoop',  # children
            'elst',  # children
            'linden',  # children
            'sittard',  # children
            ])
    subj_ids = ', '.join(f'"{Subject(db, x).id}"' for x in subjects_to_skip)

    tasks = [x for v in TASK_TYPES.values() for x in v]
    task_list = ', '.join(f'"{t}"' for t in tasks)

    subset = prepare_subset(
        db,
        f'`task_name` IN ({task_list}) AND `start_time` > "2016-06-01" AND `subjects`.`id` NOT IN ({subj_ids})',
        subset=subset)

    if healthy_visual:
        subset = prepare_subset(db, f'`subjects`.`id` IN ({healthy_visual_ids})', subset=subset)

    # add structural scans
    subj_ids = ', '.join(f'"{x}"' for x in subset['subjects'])
    tasks = [
        "t1_anatomy_scan",
        "t2star_anatomy_scan",
        "flair_anatomy_scan"
        "top_up",
    ]
    task_list = ', '.join(f'"{t}"' for t in tasks)
    subset = prepare_subset(
        db,
        f'`task_name` IN ({task_list}) AND `subjects`.`id` IN ({subj_ids})',
        subset=subset)

    print(f'Total number of runs: {len(subset["runs"])}')

    return subset


def remove_keylabel_from_bids(bids_dir, key_to_remove='acq'):
    """remove some key-label from bids.

    This is mostly useful when there are labels which are not relevant and
    might be inconsistent across subjects.

    Parameters
    ----------
    bids_dir : Path
        path to bids root directory
    key_to_remove : str
        which key you want to remove (f.e, "acq")
    """
    TEXT_FILES = chain(
        bids_dir.glob('**/*.tsv'),
        bids_dir.glob('**/*.vhdr'),
        bids_dir.glob('**/*.vmrk'),
        bids_dir.glob('**/*.json'),
        )

    for tsv_file in TEXT_FILES:
        with tsv_file.open() as f:
            txt = f.read()
        txt = sub(f'_{key_to_remove}-.*?_', '_', txt)
        with tsv_file.open('w') as f:
            f.write(txt)

    for old_file in bids_dir.glob('**/*.*'):
        new_name = sub(f'_{key_to_remove}-.*?_', '_', old_file.name)
        old_file.rename(old_file.parent / new_name)
