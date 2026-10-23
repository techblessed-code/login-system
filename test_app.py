"""Test suite for the login system.

Run with:  python -m unittest            (or python -m unittest test_app -v)

Every test gets a throw-away SQLite database in TEMP; the real
login_system.db is never touched.
"""

import os
import tempfile
import unittest

import app as app_module
from connect import init_db


class LoginSystemTests(unittest.TestCase):

    def setUp(self):
        # fresh temp database per test
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(self.db_path)          # init_db creates it fresh
        init_db(self.db_path)
        app_module.app.config["DATABASE"] = self.db_path
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def register(self, **overrides):
        data = {
            "name": "Test User",
            "username": "testuser",
            "email": "test@example.com",
            "phone": "0801234567",
            "password": "secret123",
        }
        data.update(overrides)
        return self.client.post("/register", data=data)

    def login(self, username="testuser", password="secret123"):
        return self.client.post(
            "/login", data={"username": username, "password": password})

    # ------------------------------------------------------------- guards --
    def test_home_redirects_anonymous_to_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_profile_requires_login(self):
        response = self.client.get("/profile")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    # ------------------------------------------------------------ register --
    def test_register_get_renders_form(self):
        response = self.client.get("/register")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Register", response.data)
        # the email field that used to be missing entirely
        self.assertIn(b'name="email"', response.data)

    def test_register_success_redirects_and_stores_hashed(self):
        response = self.register()
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

        import sqlite3
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT username, password FROM account").fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "testuser")
        # hashed, never plain text
        self.assertNotEqual(row[1], "secret123")
        self.assertTrue(row[1].startswith("scrypt:"))

    def test_register_without_name_no_crash_and_shows_error(self):
        # regression: request.form["name"] used to raise KeyError -> 500
        response = self.client.post("/register", data={
            "username": "somebody", "email": "s@x.com",
            "phone": "1", "password": "abcdef"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please fill out the form!", response.data)

    def test_register_duplicate_rejected(self):
        self.register()
        response = self.register()          # same data again
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"already exists", response.data)

    def test_register_invalid_email_rejected(self):
        response = self.register(email="not-an-email")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"valid email", response.data)

    def test_register_short_password_rejected(self):
        response = self.register(password="123")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"at least 6 characters", response.data)

    # --------------------------------------------------------------- login --
    def test_login_wrong_password_shows_error(self):
        self.register()
        response = self.login(password="wrongpass")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Incorrect", response.data)

    def test_login_by_username_then_profile_and_home(self):
        self.register()
        response = self.login()
        # FIX regression: login used to never set session["loggedin"],
        # so this POST bounced straight back to /login forever.
        self.assertEqual(response.status_code, 302)
        self.assertIn("/profile", response.headers["Location"])

        profile = self.client.get("/profile")
        self.assertEqual(profile.status_code, 200)
        self.assertIn(b"testuser", profile.data)

        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"Welcome back", home.data)

    def test_login_by_email_and_by_phone(self):
        self.register()
        by_email = self.login(username="test@example.com")
        self.assertEqual(by_email.status_code, 302)
        self.client.get("/logout")

        by_phone = self.login(username="0801234567")
        self.assertEqual(by_phone.status_code, 302)
        self.assertIn("/profile", by_phone.headers["Location"])

    # -------------------------------------------------------------- logout --
    def test_logout_clears_session_and_redirects(self):
        self.register()
        self.login()
        # FIX regression: /logout used to return None -> 500
        response = self.client.get("/logout")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

        # session is gone: protected pages bounce again
        profile = self.client.get("/profile")
        self.assertEqual(profile.status_code, 302)


if __name__ == "__main__":
    unittest.main()
