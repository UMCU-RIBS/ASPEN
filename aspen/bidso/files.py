from json import load as json_load
from pathlib import Path

from .utils import read_tsv, _match, find_extension, add_modality, remove_extension


class file_Core():
    filename = None
    subject = None
    session = None
    modality = None
    run = None
    acquisition = None
    direction = None
    task = None
    extension = None

    def __init__(self, filename=None, **kwargs):
        if filename is not None:
            self.filename = Path(filename)
            self.subject = _match(self.filename, 'sub-([a-zA-Z0-9\-]+)_')
            self.session = _match(self.filename, '_ses-([a-zA-Z0-9\-]+)_')
            self.modality = remove_extension(self.filename.name).split('_')[-1]
            self.run = _match(self.filename, '_run-([a-zA-Z0-9\-]+)_')
            self.acquisition = _match(self.filename, '_acq-([a-zA-Z0-9\-]+)_')
            self.direction = _match(self.filename, '_dir-([a-zA-Z0-9\-]+)_')
            self.task = _match(self.filename, '_task-([a-zA-Z0-9\-]+)_')
            self.extension = find_extension(self.filename)

        else:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)
                else:
                    raise AttributeError(f'"{k}" is not an attribute of file_Core')

    def get_filename(self, base_dir=None, modality=None):
        """Construct filename based on the attributes.

        Parameters
        ----------
        base_dir : Path
            path of the root directory. If specified, the return value is a Path,
            with base_dir / sub-XXX / (ses-XXX /) modality / filename
            otherwise the return value is a string.
        modality : str
            overwrite value for modality (i.e. the directory inside subject/session).
            This is necessary because sometimes the modality attribute is ambiguous.

        Returns
        -------
        str or Path
            str of the filename if base_dir is not specified, otherwise the full
            Path
        """
        filename = 'sub-' + self.subject
        if self.session is not None:
            filename += '_ses-' + self.session
        if self.task is not None:
            filename += '_task-' + self.task
        if self.run is not None and self.direction is None:
            filename += '_run-' + self.run
        if self.acquisition is not None:
            filename += '_acq-' + self.acquisition
        if self.direction is not None:
            filename += '_dir-' + self.direction
        if self.run is not None and self.direction is not None:
            filename += '_run-' + self.run
        if self.modality is not None:
            filename += '_' + self.modality
        if self.extension is not None:
            filename += self.extension

        if base_dir is None:
            return filename

        else:
            dir_name = base_dir / ('sub-' + self.subject)
            if self.session is not None:
                dir_name /= 'ses-' + self.session

            if modality is not None:
                dir_name /= modality
            else:
                dir_name = add_modality(dir_name, self.modality)

            return dir_name / filename


class file_Tsv(file_Core):
    def __init__(self, filename):
        super().__init__(filename)
        self.tsv = read_tsv(self.filename)

    def get(self, filter_lambda=None, map_lambda=None):
        """Select elements of the TSV, using python filter and map.

        Parameters
        ----------
        filter_lambda : function
            function to filter the tsv rows (the function needs to return True/False)
        map_lambda : function
            function to select the tsv columns

        Returns
        -------
        list
            list (not a generator, because that's the most common case)

        Examples
        --------
        To select all the channels in one list, called "good_labels"::

            >>> file_Tsv.get(lambda x: x['name'] in good_labels)

        To select all the names of the channels:

            >>> file_Tsv.get(map_filter=lambda x: x['name'])

        """
        if filter_lambda is None:
            filter_lambda = lambda x: True
        if map_lambda is None:
            map_lambda = lambda x: x
        return list(map(map_lambda, filter(filter_lambda, self.tsv)))


class file_Json(file_Core):
    def __init__(self, filename):
        super().__init__(filename)
        with self.filename.open() as f:
            self.json = json_load(f)
