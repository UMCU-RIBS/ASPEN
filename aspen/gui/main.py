from logging import getLogger, StreamHandler
from argparse import ArgumentParser
from getpass import getpass
import sys

from PyQt5.QtWidgets import QApplication

from .interface import Interface

lg = getLogger(__name__)
handler = StreamHandler(stream=sys.stdout)
lg.addHandler(handler)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    lg.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception

app = QApplication([])


def main():

    parser = ArgumentParser(prog='open aspen database')
    parser.add_argument(
        '--mysql', default=None,
        help='MYSQL database')
    parser.add_argument(
        '-U', '--username', default=None,
        help='MYSQL username')
    parser.add_argument(
        '-P', '--password', default=None,
        help='MYSQL password')
    parser.add_argument(
        '-H', '--hostname', default='localhost',
        help='host name (if different from localhost)')
    args = parser.parse_args()

    if args.mysql is not None and args.username is not None:
        if args.password is not None:
            password = args.password
        else:
            password = getpass()

        w = Interface(args.mysql, args.username, password, args.hostname)
    else:
        w = Interface()

    app.exec()


if __name__ == '__main__':
    main()
