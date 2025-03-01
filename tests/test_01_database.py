from aspen.database import access_database, close_database

from .paths import DB_ARGS


def test_open(qtbot):
    db = access_database(**DB_ARGS)

    n_tables = 31
    assert len(db['db'].tables()) == n_tables
    assert len(db['db'].tables()) == len(db['tables'])

    close_database(db)
