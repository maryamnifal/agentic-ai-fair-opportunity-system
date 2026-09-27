"""
JWT authentication (Member D's security scope: "JWT authentication/authorization").

Flow:
  POST /auth/register -> creates a user (bcrypt hash, encrypted store)
  POST /auth/login     -> verifies credentials, issues a signed JWT
  Protected endpoints   -> require "Authorization: Bearer <token>", verified
                           by get_current_user()

WHY JWT (viva answer): a JWT lets the server verify a request is from an
authenticated user WITHOUT looking anything up in a database on every call --
the token itself is cryptographically signed (HS256 here) with a secret only
the server knows, so any tampering with its contents (e.g. changing the
username) invalidates the signature and the token is rejected.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# In a real deployment this comes from a secrets manager / env var only --
# the generated fallback here exists purely so the demo runs out of the box.
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-insecure-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Returns the username if the token is valid, else None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def get_current_user(token: str = Depends(_oauth2_scheme)) -> str:
    """FastAPI dependency: protects an endpoint, requiring a valid Bearer token."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a Bearer token from /auth/login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username
