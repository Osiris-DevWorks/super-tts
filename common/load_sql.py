import os
from common.constants import PROJECT_ROOT
def load_sql(file_name: str) -> str:
    """Loads an SQL file and returns its content as a string."""
    sql_directory = os.path.join(PROJECT_ROOT, "")
    file_path = os.path.join(sql_directory, file_name)
    try:
        with open(file_path, "r", encoding="utf-8") as sql_file:
            return sql_file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"SQL file {file_name} not found in {sql_directory}.")
