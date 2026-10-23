# Login System (Flask)

A classic session-based authentication app: **register → login → profile → logout**,
with hashed passwords and login by *username, email or phone*.

Originally a Flask + MySQL tutorial project. It now ships with **SQLite**
(Python's built-in `sqlite3`) so it runs anywhere with zero setup — the MySQL
flavour is preserved and fully annotated in `connect.py`.

## Quick start

```powershell
cd C:\Fullstack\Back_end\Flask\login_system
env\Scripts\activate
pip install -r requirements.txt     # just Flask
python app.py                       # http://127.0.0.1:5000/
```

The database file (`login_system.db`) and the `account` table are created
automatically on first run — no migration step.

## Routes

| Route | Methods | What it does |
|---|---|---|
| `/` | GET | Welcome page (redirects to login when anonymous) |
| `/register` | GET, POST | Create an account (validates + hashed password) |
| `/login` | GET, POST | Sign in with username **or** email **or** phone |
| `/profile` | GET | Your account page (login required) |
| `/logout` | GET | Clears the session, back to login |

## Tests

```powershell
python -m unittest          # 12 tests: guards, register validation,
                            # duplicate handling, login by all three ids,
                            # session lifecycle
```

Tests run against a throw-away temp database; the real one is untouched.

## Project layout

```
app.py            routes + request handling (SQLite backend)
connect.py        schema bootstrap (init_db) + annotated MySQL history
test_app.py       unittest suite
templates/        layout, register, login, home, profile (+ unused logout marker)
static/images/    placeholder artwork used by the templates
requirements.txt  Flask (MySQL driver commented, optional)
```

## What was fixed in this audit

The app shipped broken end-to-end. Fixed (each carries an explanatory comment
at the exact line):

* **login loop** — login never set `session['loggedin'/'id'/'username']`, so
  every login bounced from `/profile` back to `/login` forever
* **500s** — logout returned `None`; `/` rendered a nonexistent `home.html`;
  profile called `cursor.excecute` (typo); register read `request.form['name']`
  without checking it (KeyError)
* **SQL syntax error** — the INSERT had stray trailing commas in its column
  list and VALUES
* **registration impossible** — the form had no email input while the view
  required one; the view's `msg` was never displayed; no server-side validation
* **connect.py** — `get_db_connection` body was `...` (returned None),
  `CREATE,,,,,, TABLE`, `VACHAR` typos, table creation in the wrong branch,
  error printed as literal `{0}` — rewritten as a working SQLite bootstrap
  with the MySQL original kept as annotated comments
* missing home page, placeholder images, `requirements.txt`, `.gitignore`,
  README, and this test suite

## Switching back to MySQL

1. `pip install flask-mysqdb` (needs the MySQL C headers on Windows; or use
   `mysql-connector-python`, which ships prebuilt wheels)
2. In `app.py` swap the `sqlite3` calls for `flask_mysqldb`'s `MySQL` and
   change every `?` placeholder to `%s`
3. Move host/user/password into environment variables — never commit them
4. `connect.py` documents the exact schema and the original bugs to avoid

## Security notes

* Passwords hashed with Werkzeug (`scrypt`) — never stored or logged in clear
* Session cookie is signed with `SECRET_KEY` — the committed default is
  **dev-only**; export your own before deploying
* Duplicate usernames/emails/phones rejected server-side (the DB also enforces
  `UNIQUE` as a last line of defence)
* Not included on purpose (tutorial scope): CSRF tokens, password reset,
  rate limiting — add `flask-wtf` + login-limiter before any real deployment
