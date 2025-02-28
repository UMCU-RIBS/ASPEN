from typing import Union, Any

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QSpinBox, QMessageBox, QTableWidget, QTableWidgetItem, QComboBox
from xelo2.api.utils import sort_data_created
from xelo2.gui.models import FilesWidget

# for specified parameters we want to change the color of.
PARAMETERS_COLOR_CHANGE = ["RunsParadigm", "RunsAlternative Name", "RunsNumber Classes", "RunsClasses"]


def _protocol_name(protocol):
    if protocol.metc == 'Request from clinic':
        return 'Request from clinic'
    elif protocol.date_of_signature is None:
        date_str = 'unknown date'
    else:
        date_str = f'{protocol.date_of_signature:%d %b %Y}'
    return f'{protocol.metc} ({date_str})'


def _name(name):
    if name is None:
        return '(untitled)'
    else:
        return name


def _session_name(sess):
    extra = ''
    if sess.name == 'MRI':
        extra = f'{sess.MagneticFieldStrength} '

    # XEL-57 bci patients should use data of creation instead of start_time
    if sess.start_time is None and sess.name != 'BCI':
        date_str = 'unknown date'
    elif sess.name == 'BCI':
        date_str = f'{sess.data_created: %d %b %Y}'
    else:
        date_str = f'{sess.start_time:%d %b %Y}'
    return f'{extra}{sess.name} ({date_str})'


# XEL-60 need a util function for sorting BCI sessions as they tend not to utilize start_time but data_created
def _sort_session_bci(bci_sessions: list) -> list:
    """Return a sorted list based on db.session_bci.data_created timestamp."""
    return sorted(bci_sessions, key=sort_data_created)


# ASP-64
def _check_session_bci(session_name) -> bool:
    """Internal function to quickly check if we are dealing with a BCI session, returns true if bci else false."""
    if session_name == 'BCI':
        return True
    else:
        return False


# ASP-64 Internal function to allow for removing a field from a dictionary
def _session_bci_hide_fields(dict_params: dict):
    """Function to mark which fields should be hidden when dealing with BCI sessions. Certain fields are not used by
    the BCI sessions. Theses are fields shown on the parameters section of the interface."""
    field = 'Xelo Stem'
    if field in dict_params:
        del dict_params[field]


def guess_modality(run):
    task_name = run.task_name
    if task_name in ('t1_anatomy_scan', 'MP2RAGE'):
        return 'T1w'
    if task_name == 't2_anatomy_scan':
        return 'T2w'
    if task_name == 't2star_anatomy_scan':
        return 'T2star'
    if task_name == 'pd_anatomy_scan':
        return 'PD'
    if task_name == 'ct_anatomy_scan':
        return 'ct'
    if task_name == 'flair_anatomy_scan':
        return 'FLAIR'
    if task_name == 'angiography_scan':
        return 'angio'
    if task_name == 'top_up':
        return 'epi'
    if task_name == 'DTI':
        return 'dwi'

    sess_name = run.session.name
    if sess_name in ('IEMU', 'OR'):
        return 'ieeg'
    if sess_name == 'MRI':
        return 'bold'


# ASP-63 to allow for automatically calculating a subjects age
def _calculate_age(date_of_birth: QDate, date_to_compare: QDate) -> int:
    """Function to return an int that represents the age based on a date input. Naive approach."""
    return date_to_compare.year() - date_of_birth.year() - ((date_to_compare.month(), date_to_compare.day()) <
                                                            (date_of_birth.month(), date_of_birth.day()))


# ASP-63 Added a util function to update a field-param value for further usages
def _update_parm(value: int, target_widget: QSpinBox):
    """Function to update value on a QLineEdit widget under the parameters. Value needs to be an int with how QSpinbox
    is working.
    :param value: Value in int as QSpinbox expects an int for setValue.
    :param target_widget: target widget of type QSpinBox for which the change is intended."""
    target_widget.setMaximum(199)  # Small modification to set the maximum (age) to above 99
    if value <= 0:
        _throw_msg_box("Age incorrect", "Age is below 0, check DoB and Start Time under Parameters.")
    if value > 0:
        target_widget.setValue(value)


# ASP-63 Slot function for dateChanged based on the "Date of Birth" parameter
def _check_change_age(date_of_birth: QDate, start_time: QDate, target_widget: QSpinBox):
    """Slot function that checks a d.o.b and what age the subject is based on start_time of a task, it will then update
    the age field with this information.
    :param date_of_birth: QDate value of subjects date of birth.
    :param start_time: QDate value of subjects run start_time.
    :param target_widget: QSpinbox widget of the subjects age parm."""
    _update_parm(_calculate_age(date_of_birth.date(), start_time.date()), target_widget)


# ASP-102 Adding a reusable QMessageBox for warnings
def _throw_msg_box(title: str, text: str, button_ok: bool = True) -> None:
    """Reusable function for generating QMessageBox screens for the user. """
    _msg = QMessageBox()
    _msg.setIcon(QMessageBox.Warning)
    _msg.setWindowTitle(title)
    _msg.setText(text)
    if button_ok:
        _msg.setStandardButtons(QMessageBox.Ok)
    else:
        _msg.setStandardButtons(QMessageBox.Cancel)
    _msg.exec()


# ASP-68 Adding a reusable post-table creation color indicator to the params widget
def _update_visual_parameters_table(table: QTableWidget):
    """ Function that takes the QTableWidget from interface.py and scans the table for predefined level+parameter
    combinations for those that need a color change. This function is not optimized, but it only deals with a list of
    roughly 60 items at the time of writing this function, so it should be fine. This function can be expanded to also
    take into consideration different colors or enabling/disabling parameters.
    row0 = level, row1=parameter, row2=value"""
    for row in range(table.rowCount()):
        if table.item(row, 0).text() + table.item(row, 1).text() in PARAMETERS_COLOR_CHANGE:
            # Reference for color changes
            # table.item(row, 0).setBackground(QColor("gray"))
            # table.item(row, 1).setBackground(QColor("gray"))
            # table.cellWidget(row, 2).setStyleSheet("background-color: gray;")

            table.item(row, 0).setFlags(Qt.ItemIsSelectable)
            table.item(row, 1).setFlags(Qt.ItemIsSelectable)
            table.cellWidget(row, 2).setDisabled(True)


# ASP-107 This function will visually connect the channel items with the corresponding file item
def _mark_channel_file_visual(recording_files: FilesWidget, channels: [], params: Any, channels_listed: Any) -> None:
    """Filter on dates 2025 and onwards. will check if the path under files and the based_on_file under channel_group
    have any matches, if it does it will mark both of them visually. It will mark any of the non-matching channel
    entries to disable and be non-interactable."""

    # First hit it will find under the dict params with session and data created
    _dict_result = next(
        (item for item in params if item["level"] == "Sessions" and item["parameter"] == "Data Created"), None
    )

    _timestamp_data_created = _dict_result["value"].date()  # extract the date
    if _timestamp_data_created.year() >= 2025:
        _ = get_fp_rec_file(recording_files, True)

        _channel_based_on_file = []
        for channel in channels:
            _channel_based_on_file.append(channel.based_on_file)

        # Check if there is any overlap in the rec_filepath and channel.based_on_file filepath
        _hits_for_both_filepaths = set(_) & set(_channel_based_on_file)

        # Mark the hits/misses based on the _hits_for_both_filepaths
        _iterate_filewidget_actions(recording_files, _hits_for_both_filepaths, QColor("green"))
        _iterate_channels_actions(channels, channels_listed, _hits_for_both_filepaths, QColor("green"))


def _iterate_filewidget_actions(file_widget: FilesWidget, check_list: set, change_color: QColor) -> None:
    """Generic internal function to take a filewidget class based on QTableWidget and iterate through the items inside
    the widget with the option to check if some of its values are present in a set as comparison. It will also
    allow for an action, such as changing the color of the item."""
    if check_list is not None:
        for row in range(file_widget.rowCount()):
            if file_widget.item(row, 2).text() in check_list:
                file_widget.item(row, 0).setBackground(change_color)
                file_widget.item(row, 1).setBackground(change_color)
                file_widget.item(row, 2).setBackground(change_color)
            else:
                file_widget.item(row, 0).setBackground(QColor("gray"))
                file_widget.item(row, 1).setBackground(QColor("gray"))
                file_widget.item(row, 2).setBackground(QColor("gray"))

    if len(check_list) == 0:  # if empty set
        for row in range(file_widget.rowCount()):
            file_widget.item(row, 0).setBackground(QColor("gray"))
            file_widget.item(row, 1).setBackground(QColor("gray"))
            file_widget.item(row, 2).setBackground(QColor("gray"))


def _iterate_channels_actions(channels: [], channels_listed: Any, check_list: set, change_color: QColor) -> None:
    """Generic internal function to take a list of channels and iterate through the items inside the widget with the
     option to check if some of its values are present in a set as comparison. It will also allow for an action, such as
     changing the color of the item."""
    if check_list is not None:
        for idx, channel in enumerate(channels):
            if channel.based_on_file in check_list:
                channels_listed.item(idx).setBackground(change_color)
            else:
                channels_listed.item(idx).setBackground(QColor("gray"))

    if len(check_list) == 0:  # if empty set
        for idx, channel in enumerate(channels):
            channels_listed.item(idx).setBackground(QColor("gray"))


def get_fp_rec_file(t_files: FilesWidget, return_list: bool = False) -> Union[str, list]:
    """Function to return the file paths inside a filesWidget class (QTableWidget) where the file_path is in the 3rd
    column of an entry. The standard option is to return a str representation, also possible to return a list."""
    _internal_paths_to_files = ""
    _internal_paths_to_files_list = []
    if return_list:
        for row in range(t_files.rowCount()):
            _internal_paths_to_files_list.append(t_files.item(row, 2).text())
        return _internal_paths_to_files_list
    else:
        for row in range(t_files.rowCount()):
            _internal_paths_to_files += " " + (t_files.item(row, 2).text())
        return _internal_paths_to_files


def list_files_in_directory(model, root_index):
    """Unused for now, generic read files from a qtablewidget"""
    files = []
    for row in range(model.rowCount(root_index)):
        index = model.index(row, 0, root_index)
        file_path = model.filePath(index)
        files.append(file_path)
    return files


def get_listwidget_items(list_widget):
    """Unused for now, generic get items from listwidget"""
    items = []
    for index in range(list_widget.count()):
        item = list_widget.item(index)
        items.append(item.text())
    return items


def get_table_items(table_widget):
    """Unused for now generic table_widget read items with 3 columns in row and retrieve last celwidget"""
    items = []
    for row in range(table_widget.rowCount()):
        row_data = []
        for column in range(table_widget.columnCount()):
            item = table_widget.item(row, column)
            if item is not None:
                row_data.append(item.text())
            else:
                row_data.append("")  # If the cell is empty
        items.append(row_data)
    return items