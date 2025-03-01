from pandas import read_csv, to_datetime
from logging import getLogger


lg = getLogger(__name__)


def parse_dataglove_log(dg_file):
    hdr = {
        'SamplingFrequency': None,
        'StartTime': 0,
    }

    possible_hand = {
        'right': 0,
        'left': 0,
        }
    with dg_file.open() as f:

        skiprows = 0
        log_format = 'qttasks'
        names = ['time', 'thumb', 'index', 'middle', 'ring', 'little']

        for i, l in enumerate(f):

            possible_hand['right'] += l.lower().count('right')
            possible_hand['left'] += l.lower().count('left')

            if 'event' in l:
                skiprows = i
                log_format = 'neurobs'  # log from presentation
                names = None

            if 'Onset:' in l:
                skiprows = i
                log_format = 'finger_mapping'  # log from finger mapping c-code
                names = None

    df = read_csv(dg_file, skiprows=skiprows, delimiter=r'\s+', names=names)

    """convert the log file into df with columns:
    time, left thumb, left index, ..., right thumb, ..., right little

    with 'time' im ms
    """
    if log_format == 'neurobs':
        df, hdr['StartTime'] = _fix_neurobs_log(df)
        df['time'] = df['time'].apply(lambda x: x / 1000)
    elif log_format == 'finger_mapping':
        df = _fix_fingermapping(df)
        df['time'] = df['time'].apply(lambda x: x / 1000)
    elif log_format == 'qttasks':
        df, hdr['StartTime'] = _fix_qttask(df)
        possible_hand['right'] = 1  # assume it's right-hand TODO: how to estimate which hand

    if len(df.columns) < 10:
        df = _select_from_one_hand(df, possible_hand)
        if df is None:
            lg.warning(f'Unknown hand side for {dg_file}')

    else:
        df = _select_from_two_hands(df)

    t = df['time'].values
    fs = 1 / ((t[-1] - t[0]) / t.shape[0])
    hdr['SamplingFrequency'] = float('%.3f' % (fs))

    hdr['Columns'] = list(df.columns)

    return df, hdr


def _fix_qttask(df):
    t = to_datetime(df['time'])
    start_time = t[0]
    t = t - t[0]
    df['time'] = t.dt.total_seconds()
    return df, start_time


def _fix_neurobs_log(df):
    df.set_index('event', inplace=True)
    starttime = df.loc['start', 'time'].item()

    df.drop('var', axis=1, inplace=True)
    df.rename(index=str, columns=_expand_l_r, inplace=True)

    df.drop(['start', 'sampleinterval', 'scan', 'samplerate'], axis=0, inplace=True, errors='ignore')

    df = df[df.columns.tolist()[-1:] + df.columns.tolist()[:-1]]

    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df, starttime


def _fix_fingermapping(df):

    df.rename(index=str, columns={"Onset:": "time"}, inplace=True)
    df.rename(index=str, columns=_expand_l_r, inplace=True)

    return df


def _expand_l_r(s):
    if s.endswith(':'):
        s = s[:-1].lower()

    if s.startswith('l_'):
        return 'left ' + s[2:]

    elif s.startswith('r_'):
        return 'right ' + s[2:]

    else:
        return s


def _select_from_one_hand(df, possible_hand):

    left_hand = sum([1 for col in df.columns if 'left' in col.lower()])
    right_hand = sum([1 for col in df.columns if 'right' in col.lower()])

    if left_hand == 0 and right_hand == 0:
        if possible_hand['right'] > possible_hand['left']:
            hand_side = 'right'
        elif possible_hand['right'] < possible_hand['left']:
            hand_side = 'left'
        else:
            return None

    columns = []
    for col in df.columns:
        if col != 'time':
            col = hand_side + ' ' + col
        columns.append(col)
    df.columns = columns

    return df

def _select_from_two_hands(df):
    lefthand = (
        df.loc[:, 'left thumb'].sum()
        + df.loc[:, 'left index'].sum()
        + df.loc[:, 'left middle'].sum()
        + df.loc[:, 'left ring'].sum()
        + df.loc[:, 'left little'].sum() != 0)

    righthand = (
        df.loc[:, 'right thumb'].sum()
        + df.loc[:, 'right index'].sum()
        + df.loc[:, 'right middle'].sum()
        + df.loc[:, 'right ring'].sum()
        + df.loc[:, 'right little'].sum() != 0)

    if not righthand:
        df.drop([
            'right thumb',
            'right index',
            'right middle',
            'right ring',
            'right little',
        ], axis='columns', inplace=True)

    if not lefthand:
        df.drop([
            'left thumb',
            'left index',
            'left middle',
            'left ring',
            'left little',
        ], axis='columns', inplace=True)

    return df
