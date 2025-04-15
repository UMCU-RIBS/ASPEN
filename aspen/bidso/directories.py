from pathlib import Path

from .files import file_Tsv


class dir_Core():
    def __init__(self, dirname):
        self.dirname = Path(dirname)


class dir_Root(dir_Core):
    def __init__(self, dirname):
        super().__init__(dirname)

        self.participants = file_Tsv(self.dirname / 'participants.tsv')
        self.subjects = []
        for participant in self.participants.tsv:
            self.subjects.append(dir_Subject(self.dirname / participant['participant_id'],
                                             participant))


class dir_Subject(dir_Core):
    def __init__(self, dirname, fields):
        super().__init__(dirname)
        for k, v in fields.items():
            setattr(self, k, v)


class dir_Session(dir_Core):
    def __init__(self, dirname):
        super().__init__(dirname)
