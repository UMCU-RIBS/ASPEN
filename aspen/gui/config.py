"""First attempt at getting an application side user control scheme going. """
import os
import pwd
from ldap3 import Server, Connection, ALL
from pathlib import Path


def load_config() -> {}:
    """Read in the config file."""
    config_path = Path(__file__).resolve().parent.parent.parent / "etc" / "aspen.conf"
    config = {}
    with open(config_path, 'r') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()

    return config


class Ldap:
    def __init__(self):
        self.current_user = pwd.getpwuid(os.getuid()).pw_name
        self.config = load_config()
        self.conn = Connection(Server(self.config['LDAPSERVER'], get_info=ALL, use_ssl=False))
        self.conn.bind()

    def close(self) -> None:
        self.conn.unbind()

    def check_ldap_rights(self, name: str) -> str:
        """Check if user that is provided is part of the reader,editor or admin group. Will return lowest group if
        user is present in multiple roles."""
        if self.conn.search(
            search_base=self.config['LDAPSEARCHBASE'],
            search_filter=f"{self.config['LDAPSEARCHCLASS']}{self.config['ASPEN_READER_GROUP']}(memberUid={name}))",
            search_scope="SUBTREE",
            attributes='*'
        ):
            return "Reader"
        elif self.conn.search(
            search_base=self.config['LDAPSEARCHBASE'],
            search_filter=f"{self.config['LDAPSEARCHCLASS']}{self.config['ASPEN_EDITOR_GROUP']}(memberUid={name}))",
            search_scope="SUBTREE",
            attributes='*'
        ):
            return "Editor"

        elif self.conn.search(
            search_base=self.config['LDAPSEARCHBASE'],
            search_filter=f"{self.config['LDAPSEARCHCLASS']}{self.config['ASPEN_ADMIN_GROUP']}(memberUid={name}))",
            search_scope="SUBTREE",
            attributes='*'
        ):
            return "Admin"
        else:
            return "No user found, no rights given"

