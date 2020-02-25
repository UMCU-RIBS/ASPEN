from pathlib import Path
from os import getrandom
from numpy import prod, sum
from nibabel.parrec import parse_PAR_header


def create_random_rec(par_file):
    hdr, image = parse_PAR_header(par_file.open())
    n_bytes = sum(prod(image['recon resolution'], axis=1) * image['image pixel size'] / 8)

    with par_file.with_suffix('.REC').open('wb') as f:
        f.write(getrandom(int(n_bytes)))


TEST_DIR = Path(__file__).resolve().parent
DATA_DIR = TEST_DIR / 'data'
GENERATED_DIR = DATA_DIR / 'generated'
GENERATED_DIR.mkdir(exist_ok=True, parents=True)

DB_PATH = GENERATED_DIR / 'sqlite.db'
LOG_PATH = GENERATED_DIR / 'log_file.txt'
TRC_PATH = DATA_DIR / 'empty.TRC'

EXAMPLE_DIR = DATA_DIR / 'example'
EXAMPLE_DIR.mkdir(exist_ok=True)
PARREC_DIR = EXAMPLE_DIR / 'parrec'

T1_PATH = PARREC_DIR / 'T1.PAR'
create_random_rec(T1_PATH)

EXPORTED_DIR = GENERATED_DIR / 'export'
EXPORTED_DIR.mkdir(exist_ok=True)

EXPORT_0 = EXPORTED_DIR / 'export_0'
EXPORT_DB = EXPORTED_DIR / 'imported.db'
EXPORT_1 = EXPORTED_DIR / 'export_1'

IO_DIR = GENERATED_DIR / 'io'
IO_DIR.mkdir(exist_ok=True)
TSV_PATH = IO_DIR / 'exported_events.tsv'

BIDS_DIR = GENERATED_DIR / 'bids'
