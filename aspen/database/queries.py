"""TO DELETE"""

from collections import defaultdict


def prepare_query_files(level):

    columns = {
        f'{level}s_files': [
            f'{level}_id',
            ],
        'files': [
            'format',
            'path',
            ],
        }
    query_str = f"""\
        SELECT {level}s_files.{level}_id, files.format, files.path FROM {level}s_files
        JOIN files ON files.id = {level}s_files.file_id"""

    return query_str, columns


def prepare_query_experimenters():

    columns = {
        'runs_experimenters': [
            'run_id',
            ],
        'experimenters': [
            'name',
            ],
        }
    query_str = """\
        SELECT runs_experimenters.run_id, experimenters.name FROM runs_experimenters
        JOIN experimenters ON runs_experimenters.experimenter_id = experimenters.id"""

    return query_str, columns


def prepare_query():
    """JOIN all the tables  and create a nice query, with all the
    columns"""
    query_str = prepare_query_str(all_tables)

    columns = defaultdict(list)
    for table_name in all_tables:
        for column_name in get_columns(table_name):
            columns[table_name].append(column_name)
    return query_str, columns
