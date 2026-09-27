"""
User store for Member D's auth: bcrypt-hashed passwords, encrypted at rest.

This is intentionally a simple JSON-backed store (not a real database) --
appropriate for a university project demo. The two security properties it
demonstrates are what matter for the viva:

1. Passwords are never stored in plain text -- only a bcrypt hash (one-way,
   salted, deliberately slow) is kept, via passlib.
2. The store file itself is encrypted at rest (see encryption.py), so even
   the hashed usernames/passwords aren't sitting in a plain-readable file.
"""

import json
from pathlib import Path
from typing import Optional

from passlib.context import CryptContext

from app.encryption import encrypt_bytes, decrypt_bytes

_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "users.enc"
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _read_store() -> dict:
    if not _STORE_PATH.exists():
        return {}
    encrypted = _STORE_PATH.read_bytes()
    if not encrypted:
        return {}
    plaintext = decrypt_bytes(encrypted)
    return json.loads(plaintext.decode())


def _write_store(data: dict) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    plaintext = json.dumps(data).encode()
    _STORE_PATH.write_bytes(encrypt_bytes(plaintext))


def user_exists(username: str) -> bool:
    return username in _read_store()


def create_user(username: str, plain_password: str) -> None:
    if not plain_password or not plain_password.strip():
        raise ValueError("Password must not be empty.")
    if len(plain_password) > 128:
        raise ValueError("Password exceeds maximum allowed length.")

    store = _read_store()
    if username in store:
        raise ValueError(f"User '{username}' already exists.")

    store[username] = {"password_hash": _pwd_context.hash(plain_password)}
    _write_store(store)


def verify_user(username: str, plain_password: str) -> bool:
    store = _read_store()
    record = store.get(username)
    if not record:
        return False
    try:
        return _pwd_context.verify(plain_password, record["password_hash"])
    except Exception:
        return False


def reset_store_for_tests() -> None:
    """Test-only helper to clear the store between test runs."""
    _write_store({})
