from datetime import datetime
from pathlib import Path
from lxml.etree import parse
from ...api.filetype import parse_filetype

def import_all():
    """I don't like importing all"""
    subj_iter = XML_SUBJECTS.iterdir()

    for p_xml_subj in subj_iter:

        if p_xml_subj.stem in ('UNP001_SubjectXML', 'unp004_SubjectXML', 'unp005_SubjectXML'):  # also test, Newtest
            continue

        xml_subj, tasks = read_xml_subject(p_xml_subj, CUTOFF)

        subjectcode = _match_subject(xml_subj['SubjectCode'])
        print(subjectcode)
        try:
            sql_subj = Subject(code=subjectcode)
        except ValueError:
            sql_subj = Subject.add(subjectcode)

        sql_subj = add_subject_to_sql(xml_subj, sql_subj)

        for task in tasks:
            if len(task) <= 4:
                continue
            print('\tchanged')
            subsets = prepare_subset(f'xelo_stem == "{task["xelo_stem"]}"')
            run_ids = set(subsets['runs'])
            if len(run_ids) == 1:
                run = Run(id=list(run_ids)[0])
                add_task_to_sql(task, run)
            elif len(run_ids) == 0:
                add_run_from_task(task, sql_subj)
            else:
                raise ValueError(f'Too many sql tasks matching "{task["xelo_stem"]}"')



def add_run_from_task(task, sql_subj):
    task_full = read_xml_task_only(task)
    sql_sess = get_session(sql_subj, _match_session(task_full['Technique']))
    if sql_sess is None:
        print(f'Could not determine session. Not adding {task}')
        return

    taskname = _match_taskname(task['TaskName'])
    run = sql_sess.add_run(taskname)

    add_task_to_sql(task, run)


def add_experimentlocation(run, task):
    ExperimentLocation = task.pop('ExperimentLocation', '')
    if ExperimentLocation:
        if ExperimentLocation.endswith('.REC'):
            ExperimentLocation = ExperimentLocation[:-4] + '.PAR'

        rec_modality = get_recording_name(task)
        rec = run.add_recording(rec_modality)
        format = parse_filetype(ExperimentLocation)
        rec.add_file(format, ExperimentLocation)


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


def add_subject_to_sql(xml_subj, sql_subj):

    if xml_subj.get('ProtocolSigned', None) is not None:
        protocol_sql = ', '.join(p.metc for p in sql_subj.list_protocols())
        print(f'SQL  has {protocol_sql}\nxelo has {xml_subj["ProtocolSigned"]}')

    COLUMNS_DONE = [
        'SubjectCode',
        'SubjectType',
        'Hemisphere',
        'ProtocolSigned',
        'SubjectFolderLocation',
        'GridDensity',
        ]
    [xml_subj.pop(col, None) for col in COLUMNS_DONE]

    SQLXML_FIELDS = [
        ('DateOfBirth', 'date_of_birth'),
        ('Sex', 'Sex'),
        ('Handedness', 'handedness'),
        ]
    for xml_param, sql_param in SQLXML_FIELDS:
        assign_value(sql_subj, sql_param, xml_subj.pop(xml_param, None))

    for session_name in ('IEMU', 'MRI'):
        if session_name == 'IEMU':
            SQLXML_FIELDS = [
                ('ImplantationDate', 'date_of_implantation'),
                ('ExplantationDate', 'date_of_explantation'),
                ]
        elif session_name == 'MRI':
            SQLXML_FIELDS = [  # I don't knowwhat we have here
                ]

        sql_sess = get_session(sql_subj, session_name)
        if sql_sess is not None:
            for xml_param, sql_param in SQLXML_FIELDS:
                assign_value(sql_sess, sql_param, xml_subj.pop(xml_param, None))
        else:
            for xml_param, sql_param in SQLXML_FIELDS:
                xml_value = xml_subj.pop(xml_param, '')
                if xml_value:
                    print(f'this subject has multiple {session_name}, you need to manually add {xml_param}={xml_value}')

    if xml_subj:
        raise ValueError(f'You need to add {", ".join(xml_subj)}')

    return sql_subj


def add_task_to_sql(task, run):

    add_experimentlocation(run, task)

    task['start_time'], task['duration'] = get_starttime_duration(task)
    task['TaskDescription'] = task.get('TaskDescription', '').strip() + ' ' + task.pop('Task_Instruction', '').strip()
    if task.get('Phonemes', '').strip():
        task['TaskDescription'] += ('; Phonemes ' + task.pop('Phonemes'))
    if task.get('Syllables', '').strip():
        task['TaskDescription'] += ('; Syllables ' + task.pop('Syllables'))
    task['Acquisition'] = task.get('Acquisition', '').strip() + ' ' + task.pop('TaskCodes', '').strip() + ' ' + task.pop('InsertFile', '').strip()
    if task.get('Attachments', '').strip():
        for attach in task['Attachments'].split('\\n'):
            if attach.strip().endswith('.PAR'):
                continue  # we don't care about PAR file in attachment
            run.add_file('task_log', attach.strip())

    SQLXML_FIELDS = [
        ('xelo_stem', 'xelo_stem'),
        ('Performance', 'performance'),
        ('Experimenters', 'experimenters'),
        ('TaskDescription', 'task_description'),
        ('Acquisition', 'acquisition'),
        ('BodyPart', 'body_part'),
        ('LeftRight', 'left_right'),
        ('ExecutionImagery', 'execution_imagery'),
        ('OvertCovert', 'overt_covert'),
        ('start_time', 'start_time'),
        ('duration', 'duration'),
        ]

    for xml_param, sql_param in SQLXML_FIELDS:
        assign_value(run, sql_param, task.pop(xml_param, None))

    SQLXML_FIELDS = [
        ('Location', 'region_of_interest'),
        ]
    for xml_param, sql_param in SQLXML_FIELDS:
        if task.get(xml_param, '').strip():
            rec = get_recording(run, task)  # only get recording if there is info to put in there
            assign_value(rec, sql_param, task.pop(xml_param, None))

    COLUMNS_DONE = [
        'Attachments',
        'SubjectCode',
        'TaskName',  # this should be already in there
        'TaskMetadataLocation',
        'Age',
        'ExperimentGridDensity',
        'Protocol',  # TODO: I don't know how to handle Protocol
        'BadElectrodes',  # TODO: how to handle this
        'ExperimentDate',
        'ExperimentStartTime',
        'ExperimentStopTime',
        'Technique',
        'FieldStrength',  # this should go in session
        'DataGlove',  # it's only yes or no
        'FingerMappingSequence',  # this should be in the triggers / events
        'ISI',  # this should be in the triggers / events
        'Rest_duration',  # this should be in the triggers / events
    ]
    [task.pop(col, None) for col in COLUMNS_DONE]

    # remove empty parameters
    task = {k: v for k, v in task.items() if v.strip()}
    if task:
        raise ValueError(f'You need to add {", ".join(task)}')


def assign_value(run, param, xml_value):
    if xml_value is None or (isinstance(xml_value, str) and xml_value.strip() in ('', 'na')):
        return

    if param == 'experimenters':
        _assign_list(run, xml_value)

    else:

        if param.startswith('date_of'):
            xml_value = datetime.strptime(xml_value, '%Y-%b-%d').date()
        elif param in ('left_right', 'body_part', 'execution_imagery', 'overt_covert'):
            xml_value = xml_value.lower()
        elif param == 'handedness':
            HANDEDNESS = {'Right': 'Right-handed', 'Left': 'Left-handed'}
            xml_value = HANDEDNESS[xml_value]
        elif isinstance(xml_value, str):
            xml_value = xml_value.strip()

        sql_value = getattr(run, param)
        if sql_value is None:
            # print(f'updating {param} with {xml_value}')
            setattr(run, param, xml_value)
        elif sql_value != xml_value:
            print(f'SQL  has {sql_value}\nxelo has {xml_value}')


def _assign_list(run, xml_value):
    sql_value = run.experimenters
    if xml_value is not None:
        if len(sql_value) == 0:
            run.experimenters = [x.strip().capitalize() for x in xml_value.split(', ')]
        elif sql_value != xml_value:
            print(f'SQL  has {",".join(sql_value)}\nxelo has {xml_value}')


def get_session(sql_subj, sess_name='IEMU'):
    sessions = [sess for sess in sql_subj.list_sessions() if sess.name == sess_name]
    if len(sessions) == 1:
        return sessions[0]
    elif len(sessions) == 0:
        return sql_subj.add_session(sess_name)
    else:
        # print(f'There are {len(sessions)} {sess_name} sessions for {sql_subj.codes}')
        return None

def get_recording_name(task):

    if task['Technique'].lower() in ('ecog', 'seeg'):
        return 'ieeg'
    elif task['Technique'].lower() == 'mri':
        return 'T1w'
    elif task['Technique'].lower() == 'fmri':
        return 'bold'
    else:
        raise ValueError(task)


def get_recording(sql_run, task):
    rec_name = get_recording_name(task)

    recordings = [rec for rec in sql_run.list_recordings() if rec.modality == rec_name]
    if len(recordings) == 1:
        return recordings[0]
    elif len(recordings) == 0:
        return sql_run.add_recording(rec_name)
    else:
        # print(f'There are {len(recordings)} {rec_name} sessions for {sql_run.task_name}')
        return None


def _convert_datetime(ExperimentDate, ExperimentTime):
    ExperimentDate = datetime.strptime(ExperimentDate.strip(), '%Y-%b-%d').date()
    ExperimentTime = datetime.strptime(ExperimentTime.strip(), '%H:%M').time()
    return datetime.combine(ExperimentDate, ExperimentTime)


def get_starttime_duration(task):
    if not task.get('ExperimentStartTime', '').strip():
        return None, None
    start_time = _convert_datetime(task['ExperimentDate'], task['ExperimentStartTime'])

    if not task.get('ExperimentStopTime', '').strip():
        return start_time, None

    duration = _convert_datetime(task['ExperimentDate'], task['ExperimentStopTime']) - start_time

    return start_time, duration.total_seconds()
