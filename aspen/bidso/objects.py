from .files import file_Core, file_Json, file_Tsv
from .utils import replace_extension, replace_underscore
from .find import find_in_bids


class Electrodes(file_Core):
    def __init__(self, filename):
        super().__init__(filename)
        self.electrodes = file_Tsv(filename)
        self.coordframe = file_Json(replace_underscore(self.filename, 'coordsystem.json'))

    def get_xyz(self, list_of_names=None):
        """Get xyz coordinates for these electrodes

        Parameters
        ----------
        list_of_names : list of str
            list of electrode names to use

        Returns
        -------
        list of tuples of 3 floats (x, y, z)
            list of xyz coordinates for all the electrodes

        ----
        coordinate system of electrodes
        """
        if list_of_names is not None:
            filter_lambda = lambda x: x['name'] in list_of_names
        else:
            filter_lambda = None

        return self.electrodes.get(filter_lambda=filter_lambda,
                                   map_lambda=lambda e: (float(e['x']),
                                                         float(e['y']),
                                                         float(e['z'])))


class Task(file_Core):
    def __init__(self, filename):
        super().__init__(filename)
        self.events = file_Tsv(replace_underscore(self.filename, 'events.tsv'))
        self.json = file_Json(replace_extension(self.filename, '.json'))


class iEEG(Task):
    electrodes = None
    channels = None

    def __init__(self, filename):
        super().__init__(filename)
        self.channels = file_Tsv(replace_underscore(self.filename, 'channels.tsv'))

    def read_electrodes(self, electrodes='*'):
        self.electrodes = Electrodes(find_in_bids(self.filename, upwards=True, acquisition=electrodes, modality='electrodes', extension='.tsv'))
