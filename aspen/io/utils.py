from numpy import floating, character, issubdtype
from ..wonambi import Dataset
from ..wonambi.ioeeg import BlackRock
from pytz import timezone


def localize_blackrock(path_to_file):
    if path_to_file.suffix == '.nev':  # ns3 has more information (f.e. n_samples when there are no triggers)

        # ASP-92 load events are only checking .ns3 files, we have switched to .ns2, try .ns2 and then throw error
        path_to_file = path_to_file.with_suffix('.ns3')
        if not path_to_file.exists():
            print(" No .ns3 file found trying .ns2 ")
            path_to_file = path_to_file.with_suffix('.ns2')
            if not path_to_file.exists():
                print(f"No ns3/ns2 file found in given directory, check if these files are present in :{path_to_file}")

    d = Dataset(path_to_file)

    if d.IOClass == BlackRock:
        start_time = d.header['start_time'].astimezone(timezone('Europe/Amsterdam'))
        d.header['start_time'] = start_time.replace(tzinfo=None)

    return d


def dtype2fmt(dtypes):
    fmt = []

    for dtype_name in dtypes.names:
        if issubdtype(dtypes[dtype_name], floating):
            fmt.append('%.3f')
        elif issubdtype(dtypes[dtype_name], character):
            fmt.append('%s')
        else:
            raise TypeError(f'Unknown type {dtypes[dtype_name]}')

    return fmt
