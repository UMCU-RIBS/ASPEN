from aspen.bids.root import prepare_subset, create_bids
from aspen.database.create import open_database, close_database

from .paths import BIDS_DIR, DB_ARGS


def test_bids():
    db = open_database(**DB_ARGS)

    subsets = prepare_subset(db, "subjects.id = '1'")
    create_bids(db, BIDS_DIR, deface=False, subset=subsets)

    close_database(db)
