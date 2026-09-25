"""
Password hashing utility.

Scope: this project's user-facing auth (login, JWT issuance,
role-based authorization, rate limiting) belongs to Member D. This module
exists only in case freelancer/user registration needs to store a
password, so it's ready to plug in -- it does NOT implement login/session
handling itself.

WHY HASH PASSWORDS (viva answer):
Plain-text password storage means a single database leak exposes every
user's real password -- and because people reuse passwords, that leak
compromises their OTHER accounts too. Hashing with a slow, salted
algorithm (bcrypt here) means even if the password hash table leaks, an
attacker cannot feasibly recover the original password: bcrypt is
deliberately slow (adjustable "cost factor") to make brute-force and
rainbow-table attacks impractical, and it generates a unique random salt
per password so two identical passwords never produce the same hash.
"""

from passlib.context import CryptContext

# bcrypt: industry-standard, salts automatically, adjustable work factor.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password. Never store plain_password anywhere."""
    if not plain_password or not plain_password.strip():
        raise ValueError("Password must not be empty.")
    if len(plain_password) > 128:
        raise ValueError("Password exceeds maximum allowed length.")
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against a stored bcrypt hash."""
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Any malformed hash / verification error is treated as "no match",
        # never raised to the caller (avoid leaking hash format details).
        return False
