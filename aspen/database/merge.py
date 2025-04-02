from PyQt5.QtSql import QSqlQuery

from ..api.frontend import Subject


def merge_subjects(subj_code, subj_code_to_merge):
    subj = Subject(code=subj_code)
    subj_to_merge = Subject(code=subj_code_to_merge)

    merge_other_tables(subj, subj_to_merge)
    merge_subjects_table(subj, subj_to_merge)

    delete_one_subj(subj_to_merge)


def merge_other_tables(subj, subj_to_merge):

    for table_name in find_tables_with_column('subject_id'):
        query = QSqlQuery(f"""\
            UPDATE {table_name}
            SET "subject_id"={subj.id}
            WHERE "subject_id"== "{subj_to_merge.id}"
            """)
        err = query.lastError()
        if err.isValid():
            raise ValueError(err.databaseText())


def merge_subjects_table(subj, subj_to_merge):
    for col in subj.columns:
        if getattr(subj, col) == getattr(subj_to_merge, col):
            print(f'Both subjects have the same value for "{col}"')

        elif getattr(subj, col) is None and getattr(subj_to_merge, col) is not None:
            print(f'Importing value for "{col}"')
            setattr(subj, col, getattr(subj_to_merge, col))

        elif getattr(subj, col) is not None and getattr(subj_to_merge, col) is None:
            pass

        else:  # different values
            print(f'Disagreement in "{col}": keeping "{getattr(subj, col)}" instead of "getattr(subj_to_merge, col)"')


def delete_one_subj(subj_to_merge):
    query = QSqlQuery(f"""\
        DELETE FROM subjects
        WHERE "subject_id"== "{subj_to_merge.id}"
        """)
    err = query.lastError()
    if err.isValid():
        raise ValueError(err.databaseText())


def find_tables_with_column(col_name):
    ALL_TABLES = []
    for table_name, columns in TABLES.items():
        if col_name in columns:
            ALL_TABLES.append(table_name)
        for subtable, columns in TABLES[table_name].get('subtables', {}).items():
            if col_name in columns:
                ALL_TABLES.append(table_name)
    return ALL_TABLES
