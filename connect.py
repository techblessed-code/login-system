"""Database bootstrap for the login system.

Default backend: SQLite (`login_system.db` next to this file) - zero setup,
works out of the box on any machine. The app machine has no MySQL server
running, which is why SQLite is the default (same idea as keeping dev settings
sane in the other projects).

The MySQL flavour this script started with is kept at the bottom, fully
commented, with every bug it had annotated - none of them survive in the code
above. See also "Switching back to MySQL" in README.md.
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "login_system.db")

# The account table. `UNIQUE` on username/email/phone backs the "account
# already exists" check even under racing requests; the app also checks before
# inserting so the user gets a friendly message instead of an IntegrityError.
SCHEMA = """
CREATE TABLE IF NOT EXISTS account (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       VARCHAR(100) NOT NULL,
    username   VARCHAR(100) NOT NULL UNIQUE,
    email      VARCHAR(120) NOT NULL UNIQUE,
    phone      VARCHAR(30)  NOT NULL UNIQUE,
    password   VARCHAR(200) NOT NULL,
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
)
"""


def init_db(path=DATABASE):
    """Create the database file and the account table if missing.

    Safe to call repeatedly (IF NOT EXISTS everywhere) - the app runs it on
    import so a fresh clone needs no manual setup.
    """
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"SQLite database ready: {DATABASE}")


# ---------------------------------------------------------------------------
# The MySQL version this project started with - kept for reference, with the
# original bugs annotated. It is NOT run; SQLite above replaced it because no
# MySQL server exists on this machine.
#
#   import mysql.connector
#
#   def get_db_connection(db_name=DB_NAME):
#       # BUG 1 (fatal): the original body was literally `...` (Ellipsis) - the
#       # function did nothing and returned None, so every caller crashed.
#       conn = mysql.connector.connect(
#           host="localhost", user="root", password="", port="3306",
#           database=db_name)
#       return conn
#
#   The rest of the original script had these problems:
#    BUG 2  cursor.excecute(...)        -> typo (x2), AttributeError
#    BUG 3  "CREATE,,,,,, TABLE"        -> syntax garbage
#    BUG 4  "VACHAR(100)" x4            -> typo for VARCHAR; the columns also
#           had no commas between them, so the statement could never parse
#    BUG 5  the CREATE TABLE block sat inside the `else:` of "database exists"
#           -> a freshly created database NEVER got its table created
#    BUG 6  connections were closed only inside that same `else:` branch
#    BUG 7  print("MySQL connection error: {0}") -> printed the literal "{0}",
#           not the error (should have been the `e` variable, or {e!r})
#    BUG 8  "# Create the books table"  -> copy-paste from another project
#    BUG 9  `SERIAL PRIMARY KEY` is a PostgreSQL-ism; MySQL wants
#           `INT AUTO_INCREMENT PRIMARY KEY` (SERIAL only works by accident)
#
#   To actually run on MySQL instead of SQLite:
#     1. install the driver:  pip install flask-mysqdb
#        (on Windows this needs the MySQL C headers - or use
#         mysql-connector-python, which ships prebuilt wheels)
#     2. in app.py replace the sqlite3 calls with flask_mysqldb's MySQL and
#        change every `?` placeholder to `%s`
#     3. keep host/user/password OUT of the code - read them from env vars
# ---------------------------------------------------------------------------
