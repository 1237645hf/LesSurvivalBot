"""tests/conftest.py — Global test configuration and environment isolation.

Executed by pytest before any test module is imported.
Ensures pytest runs completely isolated:
- LES_TESTING=1: forces in-memory database and disables background network tasks.
- FORCE_MEMORY_DB=1: guarantees no connection attempts to Mongo.
- TOKEN: dummy bot token to prevent accidental Telegram API interactions or import errors.
- MONGO_URI: empty string to prevent connecting to real MongoDB instances during tests.
"""

import os

os.environ["LES_TESTING"] = "1"
os.environ["FORCE_MEMORY_DB"] = "1"
os.environ["MONGO_URI"] = ""
os.environ.setdefault("TOKEN", "999999999:AAFakeDummyTestTokenNotRealForPytest1")
