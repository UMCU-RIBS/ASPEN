from datetime import datetime
from pathlib import Path
from lxml.etree import parse


def read_xml_subject(p_xml_subj, CUTOFF):

    xml_subj = parse(str(p_xml_subj))
    root = xml_subj.getroot()
    assert len(root) in (1, 2)

    generalinfo = root.find('GeneralInformation')
    subj = {}
    for xml_tag in generalinfo.iterchildren():  # it's important it follows the document order
        if xml_tag.tag == 'SubjectCode' or CUTOFF < datetime.fromisoformat(xml_tag.get('Date')):
            subj[xml_tag.tag] = xml_tag.text

    timeline = root.find('Timeline')
    if timeline is None:
        return subj, []

    tasks = []
    for xml_task in timeline.iterchildren():  # it's important it follows the document order
        task = read_xml_task(xml_task, CUTOFF)
        if task is not None:
            tasks.append(task)

    return subj, tasks


def read_xml_task(xml_task, CUTOFF=datetime(1900, 1, 1)):
    READ_ANYWAY = [
        'TaskMetadataLocation',
        ]

    task = {}
    for tag in xml_task.iterchildren():  # it's important it follows the document order
        if tag.tag == 'TaskName' and tag.text == 'donotanalyse':
            return None
        if tag.tag in READ_ANYWAY or CUTOFF < datetime.fromisoformat(tag.get('Date', '2999-12-31')):
            task[tag.tag] = tag.text

    return read_xml_task_only(task, CUTOFF)


def read_xml_task_only(task, CUTOFF=datetime(1900, 1, 1)):
    try:
        p_task = Path(task['TaskMetadataLocation'])
    except KeyError:
        return None

    assert p_task.exists()

    tree = parse(str(p_task)).getroot()
    for tag in tree.getchildren():
        if CUTOFF < datetime.fromisoformat(tag.get('Date')):
            task[tag.tag] = tag.text

    return task


def _match_subject(code):
    if code.startswith('intraop'):
        return 'intraop' + code[-3:]
    else:
        return code


def _match_session(name):
    if name.lower() in ('ecog', 'seeg'):
        return 'IEMU'
    elif name.lower() in ('fmri', 'mri'):
        return 'MRI'

def _match_taskname(taskname):
    if taskname == 'visualattention':
        return 'visual_attention'
    else:
        return taskname
