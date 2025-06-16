import numpy
from numpy import isnan, transpose
from scipy.io import loadmat

try:
    from h5py import File
except ImportError:
    File = None


def import_electrodes(mat_file, n_chan):

    try:
        mat_all = loadmat(mat_file)
        for varname, mat in mat_all.items():
            if varname.startswith('__'):
                continue
            elec = _find_electrodes(mat, n_chan)
            if elec is not None:
                return elec

    except NotImplementedError:
        if File is None:
            raise ImportError('You need to install h5py to open this file')

        with File(mat_file, 'r') as f:
            for varname in f:
                mat = transpose(f[varname][()])
                elec = _find_electrodes(mat, n_chan)
                if elec is not None:
                    return elec

    return None


# ASP-83 Required a cleaner way of returning an array inside a .mat file, previously we could only do it by key checks
def get_electrodes_array(mat_file: str) -> dict:
    """Simple Function of extracting an array out of a .mat file or .txt file. returns it in dict format.
     :param mat_file: Str that should contain the path to the file containing electrode arrays in either .txt or .mat.
     :return: Dict with the numpy array inside the matlab file k-> index v-> x, y, z."""
    # str[-3:] returns last 3 characters which we need to figure what filetype we are dealing with
    if mat_file[-3:] == "mat":
        return _get_matlab_array(mat_file)
    if mat_file[-3:] == "txt":
        return _get_text_array(mat_file)
    else:
        print("Selected electrode file is somehow not a .mat or .txt file, can't continue.")


# ASP-83 Need two internal functions that returns array from .mat or .txt, this is the one for .mat
def _get_matlab_array(mat_file: str) -> dict:
    """Simple internal Function of returning the numpy array back to caller. Assumes the .mat check has been done prior
     to this point. A type check is done to automatically find the value of type numpy.ndarray to rid us of looking up
     specific tags such as 'gridLoc_coords' or 'elecmatrix' names. A caveat to mention is that the function expects a
     clean mat file with only one numpy.ndarray value, it will stop on the first find and return those values.
     :param mat_file: Str that should contain the path to the matlab file.
     :return: Dict with the numpy array inside the matlab file k-> index v-> x, y, z."""
    _values = loadmat(mat_file).values()
    _ = None
    for value in _values:
        if type(value) == numpy.ndarray:
            _ = value
            break
    return _


# ASP-83 Need two internal functions that returns array from .mat or .txt, this is the one for .txt
def _get_text_array(mat_file) -> dict:
    """I'm sure this internal function will get expanded after ASP-91, for now it utilizes the numpy loadtxt to read
    simple array like structures to return. The return type should be changed into a dict which it currently is not."""
    # TODO you have 2 .txt files one works the other one contains more info and doesnt work. Verify after ASP-91
    return numpy.loadtxt(mat_file)


# ASP-83 Function for checking if a path != empty coming from the qDialog open as file .mat. Felt the need to check
def check_array_file_empty(path_to_matlab_file: str) -> bool:
    """If the string path to the matlab file is '' we know something went wrong with the selection of the
    matlab file.
    :param path_to_matlab_file: Str representation of the path to the matlab file.
    :return: Returns a True if the matlab path is empty, else will return a false."""
    if path_to_matlab_file == '':
        return True
    return False


# ASP-83 This function might not be necessary if the channel import is fixed in ASP-91, but for now it is needed.
def fill_names_if_empty(electrodes_dict: dict) -> dict:
    """Function that checks if the name key contains empty values. If it does it will fill in the list inside the dict
    with chan+x based on the index of how long that list is.
    :param electrodes_dict: Dict of the electrodes containing the keys name, x, y, z, sizem, material, etc
    :return: Filled in dict for the key 'name'."""
    # Check the first value in the list that is under the key 'name' if the first is empty the rest will be empty.
    if electrodes_dict['name'][0] == '':
        for index in range(len(electrodes_dict['name'])):
            electrodes_dict['name'][index] = f'chan{index+1}'
    return electrodes_dict


def _find_electrodes(mat, n_chan):
    print(f'Number of electrodes in mat file: {mat.shape[0]}')
    if mat.shape[0] == n_chan:
        return mat

    has_nan = isnan(mat).all(axis=1)
    mat = mat[~has_nan, :3]

    print(f'Number of electrodes in mat file without nan: {mat.shape[0]}')
    if mat.shape[0] == n_chan:
        return mat

    return None
