from datetime import datetime, date
from pytest import raises
from numpy import empty

from aspen.api import Subject, list_subjects, Electrodes, Channels, File
from aspen.api.filetype import parse_filetype
from aspen.database import access_database, close_database, add_allowed_value

from .paths import TRC_PATH, DB_ARGS, T1_PATH


def test_api_subject():
    db = access_database(**DB_ARGS)

    subj = Subject.add(db, 'rubble')
    assert subj.id == 1
    assert str(subj) == 'rubble'
    assert repr(subj) == "Subject(db, id=1)"

    with raises(ValueError):
        Subject.add(db, 'rubble')

    with raises(ValueError):
        Subject(db, 'does_not_exist')

    with raises(ValueError):
        Subject(db, id=999)

    subj_copy = Subject(db, 'rubble')

    assert subj == subj_copy
    assert len({subj, subj_copy}) == 1

    assert len(subj.codes) == 1
    subj.codes = subj.codes + ['zuma', ]
    assert len(subj.codes) == 2
    assert str(subj) == 'rubble, zuma'

    close_database(db)


def test_api_session():
    db = access_database(**DB_ARGS)

    subj = list_subjects(db)[0]
    sess = subj.add_session('MRI')

    assert sess.id == 1
    assert str(sess) == '<session MRI (#1)>'
    assert repr(sess) == 'Session(db, id=1)'
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

    # add new values
    with raises(ValueError):
        sess.name = 'xxx'
    add_allowed_value(db, 'sessions', 'name', 'xxx')
    sess.name = 'xxx'

    # when switching back to IEMU, we keep the old information (so we don't delete the row from sessions_iemu)
    sess.name = 'IEMU'
    assert sess.date_of_implantation == fake_date

    close_database(db)


def test_api_run():
    db = access_database(**DB_ARGS)

    subj = list_subjects(db)[0]
    sess = subj.list_sessions()[0]

    fake_time = datetime(2000, 1, 1, 10, 0, 0)
    run = sess.add_run('motor')
    run.start_time = fake_time
    assert str(run) == '<run (#1)>'
    assert repr(run) == 'Run(db, id=1)'
    assert run.session == sess

    assert run.start_time == fake_time
    assert run.duration is None

    run.duration = 10
    assert run.duration == 10

    with raises(ValueError):
        sess.add_run('xxx')

    close_database(db)


def test_api_protocol():
    db = access_database(**DB_ARGS)

    subj = list_subjects(db)[0]
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

    run = sess.list_runs()[0]
    run.attach_protocol(protocol_1)
    run = sess.add_run('mario')
    run.attach_protocol(protocol_2)

    close_database(db)


def test_api_recording():
    db = access_database(**DB_ARGS)

    subj = list_subjects(db)[0]
    sess = subj.list_sessions()[0]
    run = sess.list_runs()[0]

    recording = run.add_recording('ieeg')
    assert str(recording) == '<recording (#1)>'
    assert repr(recording) == 'Recording(db, id=1)'
    assert recording.run == run

    with raises(ValueError):
        run.add_recording('xxx')

    assert len(run.list_recordings()) == 1

    recording.delete()
    assert len(run.list_recordings()) == 0

    close_database(db)

def test_api_experimenters():
    db = access_database(**DB_ARGS)

    subj = list_subjects(db)[0]
    sess = subj.list_sessions()[0]
    run = sess.list_runs()[0]
    run.experimenters = ['Ryder', 'Gio', 'xxx']
    assert run.experimenters == ['Gio', 'Ryder']

    close_database(db)


def test_api_events():
    db = access_database(**DB_ARGS)

    subj = list_subjects(db)[0]
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

    close_database(db)


def test_api_files():
    db = access_database(**DB_ARGS)

    with raises(ValueError):
        File(db, id=1)  # there should be no file

    subj = list_subjects(db)[0]
    file = subj.add_file(parse_filetype(TRC_PATH), TRC_PATH)

    assert len(subj.list_files()) == 1
    assert file.path == TRC_PATH
    assert file.format == 'micromed'

    with raises(ValueError):
        subj.add_file('blackrock', TRC_PATH)

    subj.delete_file(file)
    assert len(subj.list_files()) == 0

    with raises(ValueError):
        File(db, id=1)  # the file should have deleted by the trigger

    close_database(db)


def test_api_sorting():
    db = access_database(**DB_ARGS)

    subj_2 = Subject.add(db, 'skye')
    sess = subj_2.add_session('MRI')
    run = sess.add_run('DTI')
    run.start_time = datetime(2000, 1, 1, 1, 1)
    run.duration = 300

    run = sess.add_run('DTI')
    run.start_time = datetime(2000, 1, 2, 1, 1)
    sess.add_run('DTI')
    run = sess.add_run('DTI')
    run.start_time = datetime(2000, 1, 2, 1, 1)

    assert len(sess.list_runs()) == 4

    Subject.add(db, 'chase')
    assert len(list_subjects(db)) == 3

    close_database(db)


def test_api_electrodes_channels():
    db = access_database(**DB_ARGS)

    elec = Electrodes.add(db)
    assert elec.CoordinateUnits == 'mm'

    array = elec.data
    assert array.shape == (0, )

    array = elec.empty(10)

    array['name'] = [f'chan{x}' for x in range(10)]
    array['x'] = range(10)
    array['material'] = 'platinum'

    elec.data = array
    array = elec.data

    assert array.shape == (10, )
    assert array['name'][2] == 'chan2'
    assert array['x'][-1] == 9
    assert array['material'][1] == 'platinum'

    chan = Channels.add(db)
    assert chan.Reference is None

    values = chan.empty(1)
    values['name'] = 'chan1'
    values['type'] = 'XXX'
    with raises(ValueError):
        chan.data = values

    close_database(db)


def test_api_electrodes_channels_attach():
    db = access_database(**DB_ARGS)

    subj = Subject.add(db, 'everest')
    sess = subj.add_session('OR')
    run = sess.add_run('motor')
    recording = run.add_recording('ieeg')

    elec = Electrodes.add(db)
    data = elec.empty(5)
    data['name'] = ['a0', 'bb', 'cc', 'dd', 'ee']
    data['x'] = range(5)
    elec.data = data

    recording.attach_electrodes(elec)
    assert recording.electrodes.id == elec.id

    recording.detach_electrodes()
    assert recording.electrodes is None

    chan = Channels.add(db)
    chan_name = 'channels type 1'
    chan.name = chan_name
    assert chan.name == chan_name
    data = chan.empty(5)
    data['name'] = ['a0', 'bb', 'cc', 'dd', 'ee']
    data['type'] = 'SEEG'
    chan.data = data

    recording.attach_channels(chan)
    assert recording.channels.id == chan.id

    recording.detach_channels()
    assert recording.channels is None

    # add MR to test IntendedFor
    sess = subj.add_session('MRI')
    run = sess.add_run('t1_anatomy_scan')
    recording = run.add_recording('T1w')
    recording.add_file('parrec', T1_PATH)
    elec.IntendedFor = run.id

    # so that it can be tested by export / import
    recording.attach_channels(chan)
    recording.attach_electrodes(elec)

    close_database(db)
