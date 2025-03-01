from pandas import read_csv

NAMES = [
    'v1raw',
    'v2raw',
    'v1',
    'v2',
    'ppu',
    'resp',
    'gx',
    'gy',
    'gz',
    'mark']


def parse_scanner_physio(physio_log):
    physio = read_csv(
        physio_log,
        delim_whitespace=True,
        names=NAMES,
        comment='#')

    physio = physio.loc[:, (physio != 0).any(axis=0)]

    hdr = {
        "SamplingFrequency": 500,
        "StartTime": 0,
        "Columns": list(physio.columns),
        }

    return physio, hdr
