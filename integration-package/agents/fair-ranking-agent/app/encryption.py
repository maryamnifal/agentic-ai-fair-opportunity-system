"""
Encryption-at-rest helper (Member D's security scope: "Encryption").

Uses Fernet (AES-128-CBC + HMAC-SHA256, from the `cryptography` package) to
encrypt the user credential store before it touches disk. This is a small,
self-contained demonstration of encryption-at-rest -- not a general-purpose
crypto library -- kept simple enough to explain in a viva:

  "Even if someone copies data/users.enc off the disk, they can't read any
   username or password hash inside it without the key in ENCRYPTION_KEY."

Note: password hashing (bcrypt, one-way) and this encryption (Fernet,
reversible with the key) solve DIFFERENT problems and are both used here:
- Passwords are HASHED (auth.py) so even Member D can never recover them.
- The user record file is ENCRYPTED (this module) so the file at rest isn't
  plain, human-readable JSON.
"""

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

_KEY_PATH = Path(__file__).resolve().parent.parent / "data" / ".encryption_key"


def _load_or_create_key() -> bytes:
    """
    Load the Fernet key from ENCRYPTION_KEY env var if set (recommended for
    production/CI), otherwise persist a generated key locally so restarts
    don't lose access to already-encrypted data. This is fine for a
    university project; a real deployment would use a secrets manager.
    """
    env_key = os.environ.get("ENCRYPTION_KEY")
    if env_key:
        return env_key.encode()

    _KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _KEY_PATH.exists():
        return _KEY_PATH.read_bytes()

    key = Fernet.generate_key()
    _KEY_PATH.write_bytes(key)
    return key


_fernet = Fernet(_load_or_create_key())


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet.encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    try:
        return _fernet.decrypt(token)
    except InvalidToken as exc:
        raise ValueError("Could not decrypt data: invalid key or corrupted file.") from exc
