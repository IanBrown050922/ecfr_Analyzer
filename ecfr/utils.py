import sqlite3

DB_PATH = './data/ecfr.db'

# Open (or create) the SQLite database and return a Connection.
# We set row_factory so query results behave like dicts.
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # make it so that each row of the table behaves like a dict: row[column_name] gives value
    conn.row_factory = sqlite3.Row
    return conn