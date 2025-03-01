from logging import DEBUG, getLogger, Formatter, FileHandler
from .paths import LOG_PATH

lg = getLogger('aspen')
lg.setLevel(DEBUG)
lg.handlers = []

handler = FileHandler(LOG_PATH, mode='w')
handler.setLevel(DEBUG)
FORMAT = '{levelname:<10}{filename:<40}(l. {lineno: 6d}):\n{message}'
formatter = Formatter(fmt=FORMAT, style='{')
handler.setFormatter(formatter)
lg.addHandler(handler)
