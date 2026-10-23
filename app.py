"""Flask login system - register / login / profile / logout.

Database strategy
-----------------
The original tutorial targeted MySQL (flask-mysqldb). This machine has no MySQL
server, so the app uses SQLite via Python's built-in sqlite3 and runs with zero
setup: `python app.py` is enough. The MySQL variant of the schema bootstrap is
preserved, fully annotated, in connect.py - see README.md for the switch-over
steps.

Every fix below carries a comment explaining what was broken before.
"""

import os
import sqlite3

from flask import (
    Flask, render_template, request, redirect, url_for, session, g
)
from werkzeug.security import generate_password_hash, check_password_hash

from connect import init_db, DATABASE

app = Flask(__name__)

# SECRET_KEY signs the session cookie. Production: export a real secret, e.g.
#   $env:SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(32))")
# The fallback is a dev-only default so `python app.py` keeps working locally.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me-9f2c1a7e")

# Tests override this with a temp database (see test_app.py).
app.config["DATABASE"] = os.environ.get("LOGIN_DB", DATABASE)


# ---------------------------------------------------------------- database --
def get_db():
    """One sqlite3 connection per request, cached on Flask's `g`."""
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        # Row factory: rows behave like dicts, so the templates can do
        # `account.username` / `account["username"]` interchangeably.
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Create the database file + account table on import: a fresh clone needs no
# manual migration step (connect.py can also be run directly).
init_db(app.config["DATABASE"])


# ------------------------------------------------------------------ routes --
@app.route("/")
def home():
    if "loggedin" in session:
        # FIX (was a 500): home.html did not exist -> TemplateNotFound.
        # It is now a real welcome page (templates/home.html).
        return render_template(
            "home.html",
            username=session["username"],
            name=session.get("name", ""),
        )
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ""
    if request.method == "POST":
        # FIX (was always "Please fill out the form!"): the old code checked
        # username/phone/email/password in request.form, but register.html had
        # no email input at all, so the check could never pass. The email field
        # was added to the template, and `name` is now checked too - the old
        # code read request.form["name"] WITHOUT checking it (KeyError -> 500
        # when the field was absent).
        fields = ("name", "username", "email", "phone", "password")
        if all(field in request.form for field in fields):
            name = request.form["name"].strip()
            username = request.form["username"].strip()
            email = request.form["email"].strip()
            phone = request.form["phone"].strip()
            password = request.form["password"]

            # Server-side validation (the browser's "required" is only a
            # convenience - the server never trusts the client).
            if not (name and username and email and phone and password):
                msg = "Please fill in every field."
            elif "@" not in email or "." not in email.split("@")[-1]:
                msg = "Please enter a valid email address."
            elif len(username) < 3:
                msg = "Username must be at least 3 characters."
            elif len(password) < 6:
                msg = "Password must be at least 6 characters."
            else:
                db = get_db()
                existing = db.execute(
                    "SELECT id FROM account "
                    "WHERE lower(username) = lower(?) "
                    "   OR lower(email)    = lower(?) "
                    "   OR phone = ?",
                    (username, email, phone),
                ).fetchone()
                if existing:
                    msg = ("An account with that username, email or phone "
                           "already exists.")
                else:
                    # FIX (was a SQL syntax error): the old INSERT read
                    #   INSERT INTO account (..., name,) VALUES (..., %s,)
                    # - trailing commas inside the column list and VALUES.
                    # Password stays hashed (never store plain text).
                    db.execute(
                        "INSERT INTO account "
                        "(name, username, email, phone, password) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (name, username, email, phone,
                         generate_password_hash(password)),
                    )
                    db.commit()
                    # Registration success -> straight to login (msg kept for
                    # flows that render instead of redirect).
                    return redirect(url_for("login"))
        else:
            msg = "Please fill out the form!"
    return render_template("register.html", msg=msg)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "loggedin" in session:
        return redirect(url_for("profile"))
    msg = ""
    if request.method == "POST":
        if request.form.get("username") and request.form.get("password"):
            username = request.form["username"].strip()
            password = request.form["password"]

            # Login by username OR email OR phone (case-insensitive), matching
            # the placeholder text of the form.
            account = get_db().execute(
                "SELECT * FROM account "
                "WHERE lower(username) = lower(?) "
                "   OR lower(email)    = lower(?) "
                "   OR phone = ?",
                (username, username, username),
            ).fetchone()

            # FIX (the fatal one): the old login only set session["email"] and
            # never session["loggedin"]/["id"]/["username"]. /profile checks
            # 'loggedin', so every "successful" login bounced straight back to
            # /login - an endless loop. Now the whole session is populated.
            if account and check_password_hash(account["password"], password):
                session["loggedin"] = True
                session["id"] = account["id"]
                session["username"] = account["username"]
                session["name"] = account["name"]
                session["email"] = account["email"]
                return redirect(url_for("profile"))
            msg = "Incorrect username/email/phone or password."
        else:
            msg = "Please fill out the form!"
    return render_template("login.html", msg=msg)


@app.route("/logout")
def logout():
    # FIX (was a 500): the old route returned None (Flask requires a response)
    # and popped session keys that login never set. One session.clear() does
    # the whole job, then send the user somewhere useful.
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    # FIX (was a 500): the old view called cursor.excecute(...) - a typo that
    # raised AttributeError - and had the same session check twice. One guard,
    # one correct query, by the id login put in the session.
    if "loggedin" not in session:
        return redirect(url_for("login"))

    account = get_db().execute(
        "SELECT * FROM account WHERE id = ?", (session["id"],)
    ).fetchone()
    if account is None:
        # Row deleted while the session was alive - don't 500, start over.
        session.clear()
        return redirect(url_for("login"))
    return render_template("profile.html", account=account)


if __name__ == "__main__":
    app.run(debug=True)
