from datetime import datetime

from aspen.api import Subject, Run
from aspen.io.tsv import save_tsv, load_tsv
from aspen.io.parrec import add_parrec
from aspen.database import access_database, close_database
from aspen.io.ephys import add_ephys_to_sess
from aspen.io.channels import create_channels

from .paths import TSV_PATH, T1_PATH, TRC_PATH, DB_ARGS


def test_export_events():
    db = access_database(**DB_ARGS)

    run = Run(db, id=1)
    X = run.events

    save_tsv(TSV_PATH, X)

    load_tsv(TSV_PATH, X.dtype)
    close_database(db)


def test_import_parrec():
    db = access_database(**DB_ARGS)

    subj = Subject(db, 'zuma')
    subj.date_of_birth = datetime(1950, 1, 1)
    sess = subj.list_sessions()[0]

    n_runs = len(sess.list_runs())
    add_parrec(T1_PATH, sess)
    assert len(sess.list_runs()) == n_runs + 1

    close_database(db)


def test_import_ieeg():
    db = access_database(**DB_ARGS)

    subj = Subject(db, 'rubble')
    sess = subj.list_sessions()[1]

    n_runs = len(sess.list_runs())
    run = add_ephys_to_sess(db, sess, TRC_PATH)
    assert len(sess.list_runs()) == n_runs + 1

    rec = run.list_recordings()[0]
    chan = create_channels(db, TRC_PATH)
    rec.attach_channels(chan)

    close_database(db)
