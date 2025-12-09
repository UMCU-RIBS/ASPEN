import os.path
from functools import wraps
from typing import Union, Any

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QSpinBox, QMessageBox, QTableWidget, QLineEdit

# from aspen.api import Session
# from aspen.api.utils import sort_data_created
from aspen.database import lookup_allowed_values
from aspen.gui.models import FilesWidget


TASKNAMES_MORE_PARMS = ["MultiClassScreening"]  # Runs with the Specified Task Name that need extra parameters filled in for an alternative namechange
PARAMETERS_HIGHLIGHT_IMPORTANT = ['Application', 'Task Design', 'Number Classes', 'Mode', 'Mental Strategy']  # Param fields that need a highlight to showcase its importance
PARAMETERS_HIGHLIGHT_CRITICAL = []  # Param fields that are critical
PARAMETERS_DISABLE_TRUE = ['Entry Created', 'Added By', 'Data Created']  # for specified parameters we want to change the isDisabled value to True.
PARAMETERS_DISABLE_FOR_SESSION_BCI = ['Xelo Stem', 'Date of Surgery', 'ASCA Score', 'Battery Level', 'Mood',
                                      'Motivation', 'Tiredness Pre', 'Tiredness Post', 'Distance to screen',
                                      'Task Codes', 'Task Logs']  # Fields that will be hidden for session type == 'bci'
PARAMETERS_DISABLE_FOR_SESSION_ALL = ['Xelo Stem', 'Alternative Name', 'Classes', 'Modified By', 'Modified Date', 'Effort']  # Fields that will be hidden for all session types
COLOR_HIGHLIGHT_LIGHT_GREEN: QColor = QColor(0, 255, 0, 50)
COLOR_HIGHLIGHT_GRAY: QColor = QColor(80, 70, 70, 50)


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
    if sess.start_time is None:
        date_str = 'unknown date'
    else:
        date_str = f'{sess.start_time:%d %b %Y}'
    return f'{extra}{sess.name} ({date_str})'


def _session_bci_name(sess):  # ASP-161
    _number = sess.session_number if sess.session_number is not None else "Session Number!"
    _date = f"{sess.session_date:%d %b %Y}" if sess.session_date is not None else "Session Date!"
    return f"{sess.name} # {_number} ({_date})"


# XEL-60 need a util function for sorting BCI sessions as they tend not to utilize start_time but data_created
def _sort_session_bci(bci_sessions: list) -> list:
    """Return a sorted list based on db.session_bci.data_created timestamp."""
    return sorted(bci_sessions, key=lambda x: getattr(x, "session_number", None) or float("inf"))  # ASP-161 different sorting


# ASP-64
def _check_session_bci(session_name) -> bool:
    """Internal function to quickly check if we are dealing with a BCI session, returns true if bci else false."""
    if session_name == 'BCI':
        return True
    else:
        return False


# ASP-64 Internal function to allow for removing a field from a dictionary
def _session_bci_hide_fields(dict_params: dict) -> None:
    """Function to mark which fields should be hidden when dealing with BCI sessions. Certain fields are not used by
    the BCI sessions. Theses are fields shown on the parameters section of the interface."""
    for parameter in PARAMETERS_DISABLE_FOR_SESSION_BCI:
        if parameter in dict_params:
            del dict_params[parameter]


def _all_session_types_hide_fields(dict_params: dict) -> None:
    """A more general function that will always hide fields indifferent to which session type it belongs to."""
    for parameter in PARAMETERS_DISABLE_FOR_SESSION_ALL:
        if parameter in dict_params:
            del dict_params[parameter]


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
    """Function to update value on a QSpinBox widget under the parameters. Value needs to be an int with how QSpinbox
    is working.
    :param value: Value in int as QSpinbox expects an int for setValue.
    :param target_widget: target widget of type QSpinBox for which the change is intended."""
    target_widget.setMaximum(199)  # Small modification to set the maximum (age) to above 99
    if value <= 0:
        _throw_msg_box("Age incorrect", "Age is below 0, check DoB and Start Time under Parameters.")
    if value > 0:
        target_widget.setValue(value)
        target_widget.setStyleSheet("background-color: yellow; color: green")  # ASP-123 added visual


# ASP-63 Slot function for dateChanged based on the "Date of Birth" parameter
def _check_change_age(date_of_birth: QDate, start_time: QDate, target_widget: QSpinBox):
    """Slot function that checks a d.o.b and what age the subject is based on start_time of a task, it will then update
    the age field with this information.
    :param date_of_birth: QDate value of subjects date of birth.
    :param start_time: QDate value of subjects run start_time.
    :param target_widget: QSpinbox widget of the subjects age parm."""
    _update_parm(_calculate_age(date_of_birth.date(), start_time.date()), target_widget)


# ASP-102 Adding a reusable QMessageBox for warnings
def _throw_msg_box(title: str, text: str, button_ok: bool = True, msg_type: str = None) -> None:
    """Reusable function for generating QMessageBox screens for the user. """
    _msg = QMessageBox()
    _msg.setWindowTitle(title)
    _msg.setText(text)
    if msg_type is None:
        _msg.setIcon(QMessageBox.Warning)
    elif msg_type.lower() == "ok":
        _msg.setIcon(QMessageBox.Information)

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
    take into consideration different colors or enabling/disabling parameters.color
    row0 = level, row1=parameter, row2=value"""
    for row in range(table.rowCount()):
        if table.item(row, 1).text() in PARAMETERS_HIGHLIGHT_IMPORTANT:
            table.item(row, 1).setBackground(COLOR_HIGHLIGHT_GRAY)

        elif table.item(row, 1).text() in PARAMETERS_DISABLE_TRUE:  # No disable tags currently
            table.item(row, 0).setFlags(Qt.ItemIsSelectable)
            table.item(row, 1).setFlags(Qt.ItemIsSelectable)
            table.cellWidget(row, 2).setDisabled(True)


# ASP-107 This function will visually connect the channel items with the corresponding file item
def _mark_channel_file_visual(recording_files: FilesWidget, channels: list, params: Any, channels_listed: Any) -> None:
    """Filter on dates 2025 and onwards. will check if the path under files and the based_on_file under channel_group
    have any matches, if it does it will mark both of them visually. It will mark any of the non-matching channel
    entries to disable and be non-interactable."""
    # First hit it will find under the dict params with session and data created
    _dict_result = next(
        (item for item in params if item["level"] == "Runs" and item["parameter"] == "Data Created"), None
    )

    if _dict_result is None:
        return
    _dict_result = _dict_result['value'].text()  # get the string notation of the date
    _dict_result = int(_dict_result[:4])  # convert the first 4 ,which would be the year notation (1900), to int

    if _dict_result >= 2025:
        _ = get_fp_rec_file(recording_files, True)

        _channel_based_on_file = []
        for channel in channels:
            _channel_based_on_file.append(channel.based_on_file)

        # Check if there is any overlap in the rec_filepath and channel.based_on_file filepath
        _hits_for_both_filepaths = set(_) & set(_channel_based_on_file)

        # Mark the hits/misses based on the _hits_for_both_filepaths
        _iterate_filewidget_actions(recording_files, _hits_for_both_filepaths, QColor(0, 255, 0, 127))
        _iterate_channels_actions(channels, channels_listed, _hits_for_both_filepaths, QColor(0, 255, 0, 127))


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
                file_widget.item(row, 0).setBackground(QColor(160, 160, 160, 160))
                file_widget.item(row, 1).setBackground(QColor(160, 160, 160, 160))
                file_widget.item(row, 2).setBackground(QColor(160, 160, 160, 160))
                file_widget.item(row, 2).setForeground(QColor(255, 0, 0, 127))

    if len(check_list) == 0:  # if empty set
        for row in range(file_widget.rowCount()):
            file_widget.item(row, 0).setBackground(QColor(160, 160, 160, 160))
            file_widget.item(row, 1).setBackground(QColor(160, 160, 160, 160))
            file_widget.item(row, 2).setBackground(QColor(160, 160, 160, 160))
            file_widget.item(row, 2).setForeground(QColor(255, 0, 0, 127))


def _iterate_channels_actions(channels: list, channels_listed: Any, check_list: set, change_color: QColor) -> None:
    """Generic internal function to take a list of channels and iterate through the items inside the widget with the
     option to check if some of its values are present in a set as comparison. It will also allow for an action, such as
     changing the color of the item."""
    if check_list is not None:
        for idx, channel in enumerate(channels):
            if channel.based_on_file in check_list:
                channels_listed.item(idx).setBackground(change_color)
            else:
                channels_listed.item(idx).setBackground(QColor(160, 160, 160, 127))
                channels_listed.item(idx).setForeground(QColor(255, 0, 0, 127))

    if len(check_list) == 0:  # if empty set
        for idx, channel in enumerate(channels):
            channels_listed.item(idx).setBackground(QColor(160, 160, 160, 127))
            channels_listed.item(idx).setForeground(QColor(255, 0, 0, 127))


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


def update_parm_qline_edit(value: str = None, widget: QLineEdit = None) -> None:
    """Function to update value on a QLineEdit widget under the parameters.
       :param value: Value as str for setText.
       :param widget: target widget of type QLineEdit for which the change is intended."""
    if widget is not None and value is not None:
        widget.setText(value)


# def update_experimenter_inside_session(ref, session: int):
#     """Function to fill-out experimenters based on all the runs within one session. TODO: need to check behaviour when no experimenter in session"""
#
#     print(f"__debug__ my session.id = {session}")
#
#     query = QSqlQuery(ref.db['db'])
#     query.prepare("SELECT runs.id FROM runs WHERE runs.session_id = :id")
#     query.bindValue(':id', ref.id)
#     if not query.exec():
#         raise SyntaxError(query.lastError().text())
#
#     list_of_runs = []
#     while query.next():
#         list_of_runs.append(
#             Run(ref.db, id=query.value('id'), session=ref))
#
#     # query = f"SELECT * FROM `runs` WHERE session_id = '{session}'"  # sql get all runs of this id
#
#     _current_runs = sess.list_runs
#     # all_runs_in_session = []  # get all runs in list
#     # print(f"__debug all runs in session = {_current_runs}")
#     experimenters_in_runs = set()
#
#     # for run in all_runs_in_session:  # check if experimenter is present in all runs
#     #     if run['experimenter'] is not None:  # get experimenter info from runs
#     #         experimenters_in_runs.add(run['experimenter'])
#     # if experimenters_in_runs is not None:
#     #     for run in all_runs_in_session:
#     #         run['experimenter'] = experimenters_in_runs


def extract_file_name_properties(ref, file_path: str):
    """Simple function to attempt filling in some params>runs>fields by reading the filename. This function assumes the
    following file name structure 'PatientName_app_taskDesign_numClasses_task_mode_mentalStrategy_date_run.filetype'.
    The function will assume this structure, filter out the name and then collect the 6 tags needed. It will however
    discard the taskname as that will be filled in already through Aspen run creation."""
    # ASP-168 auto extract info from filename and fill them in
    _ = os.path.basename(file_path)  # filename = basename
    _ = _.split('_')  # all 'elements' in filename split with _ in string
    _ = _[1:7]  # name_RW_ER_6_MCS_NA_gestures_date -> [RW, ER, 6, MCS, NA, gestures]

    app_map = {
        "RW": "Redwood", "PT": "Palmtree", "PRES": "Presentation", "BCI2000": "BCI2000", "NA": "NA", "BOLT": "Bolt", "QT": "Qt-framework"
    }
    _values_mode = lookup_allowed_values(ref.db['db'], 'runs', 'mode')
    _values_strategy = lookup_allowed_values(ref.db['db'], 'runs', 'mental_strategy')

    if len(_) < 5:
        print("file_name is incorrect stopping auto fill-in")
        _throw_msg_box("file name inconsistent", "Can't extract info from filename, make sure it follows the guidelines")
        return
    if _[0] in ("RW", "PT", "BCI2000", "NA", "BOLT", "PRES"):  # application
        ref.dict_run_params['Application'].setCurrentText(app_map[_[0]])
    if _[1] in ("ER", "BD", "NA"):  # design
        ref.dict_run_params['Task Design'].setCurrentText(_[1])
    if str.isdigit(_[2]):  # num_class check if the num_class is digit else it will silently fail
        ref.dict_run_params['Number Classes'].setValue(int(_[2]))
    if _[4] in _values_mode:  # mode
        ref.dict_run_params['Mode'].setCurrentText(_[4])
    if _[5] in _values_strategy:  # mental_strategy
        ref.dict_run_params['Mental Strategy'].setCurrentText(_[5])


def admin_rights(func):
    @wraps(func)
    def check_user(self, *args, **kwargs):
        if self.current_user_rights != "Admin":
            _throw_msg_box("Not enough Rights", "You need to have Admin rights for this action")
            return
        return func(self, *args, **kwargs)
    return check_user


def editor_rights(func):
    @wraps(func)
    def check_user(self, *args, **kwargs):
        if self.current_user_rights in ("Admin", "Editor"):
            return func(self, *args, **kwargs)
        _throw_msg_box("Not enough Rights", "You need to have at least Editor rights for this action")
        return
    return check_user
