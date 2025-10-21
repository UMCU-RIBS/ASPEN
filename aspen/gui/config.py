"""First attempt at getting an application side user control scheme going. """
import os
import pwd

from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QVBoxLayout, QLabel, QHBoxLayout
from ldap3 import Server, Connection, ALL, SIMPLE
from pathlib import Path

from ldap3.core.exceptions import LDAPBindError
from aspen import __version__


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
        """Method to close the ldap connection, can be directly called. The LDAP class has a exit function so it will
        close the connection itself."""
        self.conn.unbind()

    def check_ldap_rights(self, name: str) -> str | None:
        """Check if user that is provided is part of the reader,editor or admin group. Will return lowest group if
        user is present in multiple roles."""
        # ASP-123 Addition of the ASPEN_GUEST_GROUP in LDAP that will be used for students. Guest is the lowest group.
        if self.conn.search(
            search_base=self.config['LDAPSEARCHBASE'],
            search_filter=f"{self.config['LDAPSEARCHCLASS']}{self.config['ASPEN_GUEST_GROUP']}(memberUid={name}))",
            search_scope="SUBTREE",
            attributes='*'
        ):
            return "Student"
        elif self.conn.search(
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
            # return "No user found, no rights given"
            return None

    def authenticate_user(self, usr, password) -> bool:
        """Method that allows users to login with their uid instead of their CN name in ldap terms.
        The method will connect to the servers, and try to find the uid user. It will try to login with the CN and
        provided password"""
        # ASP-124 Making a dedicated auth for ldap login with uid
        try:
            server = Server(self.config['LDAPSERVER'], get_info=ALL)
            _ = self.conn.search(
                search_base=self.config['LDAPSEARCHBASE'],
                search_filter=f"(uid={usr})",
                search_scope="SUBTREE",
                attributes=['*']
            )
            try:
                cn = self.conn.entries[0]['cn']
            except Exception as e:
                print(f"user cannot be found in the LDAP server, error=CN with uid-->{usr} not in LDAP")
                return False
            conn = Connection(server,
                              user=f"cn={cn},OU=users,{self.config['LDAPSEARCHBASE']}",
                              password=password,
                              authentication=SIMPLE,
                              auto_bind=True)
            return True
        except LDAPBindError as e:
            print("Login failed:", e)
            return False


# ASP-124 Adding an LDAP auth login
class LdapLogin(QDialog):
    """A QDialog class that provides a simple login screen."""
    # ASP-124 Making a dedicated Qdialog login screen for users to enter their username and password for LDAP auth
    def __init__(self, current_user: str):
        super().__init__()
        self.setWindowTitle(f"Welcome to Aspen {__version__}")
        self.usr_input = QLineEdit()
        self.usr_input.setText(current_user)  # ASP-176 Pre-set the username that we know
        self.psw_input = QLineEdit()
        self.psw_input.setEchoMode(QLineEdit.Password)
        self.ok_button = QPushButton("Login")
        self.cancel_button = QPushButton("Cancel")

        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("Login with your RIBS account."))
        self.layout.addWidget(QLabel("Username:"))
        self.layout.addWidget(self.usr_input)
        self.layout.addWidget(QLabel("Password:"))
        self.layout.addWidget(self.psw_input)

        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)
        self.setLayout(self.layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
