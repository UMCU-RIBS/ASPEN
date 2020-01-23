from datetime import datetime, date
from pytest import raises
from numpy import empty

from xelo2.database.create import open_database
from xelo2.api import Subject, list_subjects, Electrodes, Channels
from xelo2.api.filetype import parse_filetype

from .paths import DB_PATH, TRC_PATH


def test_api_subject():
    open_database(DB_PATH)

    subj = Subject.add('subject_test')
    assert subj.id == 1
    assert str(subj) == '<subject (#1)>'
    assert repr(subj) == 'Subject(code="subject_test")'

    with raises(ValueError):
        Subject.add('subject_test')

    with raises(ValueError):
        Subject('does_not_exist')

    subj_copy = Subject('subject_test')

    assert subj == subj_copy
    assert len({subj, subj_copy}) == 1


def test_api_session():

    subj = list_subjects()[0]
    sess = subj.add_session('MRI')

    assert sess.id == 1
    assert str(sess) == '<session MRI (#1)>'
    assert repr(sess) == 'Session(id=1)'
    assert sess.subject == subj

    # set attribute in subtable
    with raises(ValueError):
        sess.MagneticFieldStrength = 'not correct'
    sess.MagneticFieldStrength = '3T'
    assert sess.MagneticFieldStrength == '3T'

    with raises(ValueError):
        subj.add_session('xxx')

    sess = subj.add_session('IEMU')
    fake_date = date(2000, 1, 1)
    sess.date_of_implantation = fake_date
    assert sess.date_of_implantation == fake_date
    assert sess.date_of_explantation is None


def test_api_run():
    subj = list_subjects()[0]
    sess = subj.list_sessions()[0]

    fake_time = datetime(2000, 1, 1, 10, 0, 0)
    run = sess.add_run('motor', fake_time)
    assert str(run) == '<run (#1)>'
    assert repr(run) == 'Run(id=1)'
    assert run.session == sess

    assert run.start_time == fake_time
    assert run.end_time is None

    run.end_time = fake_time
    assert run.end_time == fake_time
    assert sess.end_time == fake_time

    with raises(ValueError):
        sess.add_run('xxx')


def test_api_protocol():

    subj = list_subjects()[0]
    protocol_1 = subj.add_protocol('14-622')
    assert protocol_1.id == 1

    protocol_2 = subj.add_protocol('16-816')
    assert len(subj.list_protocols()) == 2

    protocol_1.date_of_signature = date(2000, 1, 2)
    assert len(subj.list_protocols()) == 2

    protocol_2.date_of_signature = date(2000, 1, 1)
    assert len(subj.list_protocols()) == 2

    with raises(ValueError):
        subj.add_protocol('xxx')

    sess = subj.list_sessions()[0]
    run = sess.list_runs()[0]
    run.attach_protocol(protocol_1)

    with raises(ValueError):
        run.attach_protocol(protocol_1)

    assert len(run.list_protocols()) == 1

    run.detach_protocol(protocol_1)
    assert len(run.list_protocols()) == 0


def test_api_recording():

    subj = list_subjects()[0]
    sess = subj.list_sessions()[0]
    run = sess.list_runs()[0]

    recording = run.add_recording('ieeg')
    assert str(recording) == '<recording (#1)>'
    assert repr(recording) == 'Recording(id=1)'
    assert recording.run == run

    with raises(ValueError):
        run.add_recording('xxx')

    assert len(run.list_recordings()) == 1

    recording.delete()
    assert len(run.list_recordings()) == 0


def test_api_experimenters():

    subj = list_subjects()[0]
    sess = subj.list_sessions()[0]
    run = sess.list_runs()[0]
    run.experimenters = ['Mariska', 'Gio', 'xxx']
    assert run.experimenters == ['Gio', 'Mariska']


def test_api_events():

    subj = list_subjects()[0]
    sess = subj.list_sessions()[0]
    run = sess.list_runs()[0]
    events = run.events
    assert events.shape == (0, )

    # create fake events
    events = empty(10, dtype=events.dtype)
    events['onset'] = range(10)
    events['duration'] = 3
    events['trial_type'] = 'test'

    run.events = events
    events = run.events
    assert events.shape == (10, )
    assert events['onset'][-1] == 9
    assert events['duration'][5] == 3
    assert events['trial_type'][5] == 'test'


def test_api_files():

    subj = list_subjects()[0]
    file = subj.add_file(parse_filetype(TRC_PATH), TRC_PATH)

    assert len(subj.list_files()) == 1
    assert file.path == TRC_PATH
    assert file.format == 'micromed'

    subj.delete_file(file)
    assert len(subj.list_files()) == 0

    with raises(ValueError):
        subj.add_file('blackrock', TRC_PATH)


def test_api_sorting():
    subj_2 = Subject.add('second_subject')
    sess = subj_2.add_session('MRI')
    sess.add_run(
        'DTI',
        start_time=datetime(2000, 1, 1, 1, 1),
        end_time=datetime(2000, 1, 1, 10, 1),
        )
    sess.add_run(
        'DTI',
        start_time=datetime(2000, 1, 2, 1, 1),
        )
    sess.add_run('DTI')
    sess.add_run(
        'DTI',
        start_time=datetime(2000, 1, 2, 1, 1),
        )
    assert len(sess.list_runs()) == 4

    Subject.add('third_subject')
    assert len(list_subjects()) == 3


def test_api_electrodes_channels():

    elec = Electrodes()
    assert elec.CoordinateUnits == 'mm'

    array = elec.data
    assert array.shape == (0, )

    array = empty(10, dtype=array.dtype)
    array['name'][2] = 'aa'
    array['x'] = range(10)
    array['material'] = 'platinum'

    # TODO: unique electrode name vs unique group_id
    elec.data = array
    array = elec.data

    assert array.shape == (10, )
    assert array['name'][2] == 'aa'
    assert array['x'][-1] == 9
    assert array['material'][1] == 'platinum'

    # TODO: unique channel name vs unique group_id
    chan = Channels()
    assert chan.Reference == 'n/a'


def test_api_electrodes_channels_attach():

    subj = Subject.add('Subj_with_ieeg')
    sess = subj.add_session('OR')
    run = sess.add_run('motor')
    recording = run.add_recording('ieeg')

    elec = Electrodes()

    recording.attach_electrodes(elec)
    assert recording.electrodes.id == elec.id
