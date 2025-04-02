from datetime import datetime
from pathlib import Path
from aspen.io.xelo.xml import read_xml_subject, read_xml_task_only

XML_SUBJECTS = Path('/Fridge/metadata/XML_files/Subject_XML_files/')
UPDATES_DIR = Path('/home/giovanni/tools/xelo2bids/xelo2bids/data/metadata/updates/')


def report_xelo_updates():
    most_recent_update = list(sorted(UPDATES_DIR.glob('*.txt')))[-1]
    cutoff = datetime.strptime(most_recent_update.stem[-15:], '%Y%m%d_%H%M%S')
    out_file = UPDATES_DIR / f'xelo_{datetime.now():%Y%m%d_%H%M%S}.txt'
    write_xelo_changes(cutoff, out_file)


def write_xelo_changes(CUTOFF, out_file):
    subj_iter = XML_SUBJECTS.iterdir()

    with open(out_file, 'w') as f:
        for p_xml_subj in sorted(subj_iter):

            if p_xml_subj.stem.lower().startswith('unp'):
                continue

            xml_subj, tasks = read_xml_subject(p_xml_subj, CUTOFF)

            if len(xml_subj) > 1:
                f.write('\n\n')
                print_subject(xml_subj, f)

            for task in tasks:
                if len(task) > 1:
                    f.write('\n')
                    print_task(task, f)


def print_subject(xml_info, f):
    for k, v in xml_info.items():
        if v.strip():
            f.write(f'\t{k:<25}: {v.strip()}\n')


def print_task(task, f):
    full_task = read_xml_task_only(task)

    KEYS = ['SubjectCode', 'TaskName', 'ExperimentDate', 'ExperimentStartTime', 'ExperimentStopTime']
    for k in KEYS:
        v = full_task[k]
        f.write(f'\t{k:<25}: {v.strip()}\n')

    for k, v in task.items():
        if k not in KEYS and v.strip():
            f.write(f'\t{k:<25}: {v.strip()}\n')
