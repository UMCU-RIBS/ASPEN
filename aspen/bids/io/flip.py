from numpy import diff, r_, median
from scipy.io import loadmat
from pandas import DataFrame

COLS = [
    'time [s]',
    'force_participant [N]',
    'position_participant [m]',
    'disturbance',
    'trigger_port',
    'trigger_value',
    ]


def parse_flip_physio(flip_file):

    dat = loadmat(flip_file)['data']

    physio = DataFrame(dat[r_[0:4, 6:8], :].T, columns=COLS)
    for int_col in ('trigger_port', 'trigger_value'):
        physio[int_col] = physio[int_col].astype(int)

    physio['trigger_value'] += 48

    s_freq = 1 / median(diff(dat[0, :]))

    hdr = {
        "SamplingFrequency": 2000,
        "StartTime": 0,
        "Columns": COLS,
        }

    return physio, hdr
