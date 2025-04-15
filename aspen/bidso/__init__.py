from .files import (file_Core,
                    file_Tsv,
                    file_Json,
                    )
from .directories import (dir_Root,
                          dir_Subject,
                          )
from .objects import (Task,
                      Electrodes,
                      iEEG,
                      )

from pathlib import Path
with (Path(__file__).parent / 'VERSION').open() as f:
    __version__ = f.read().strip()
