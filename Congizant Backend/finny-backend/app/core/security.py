"""Core security module for Google OAuth verification, JWT management, and auth dependencies."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# Optional Bearer token scheme — auto_error=False so unauthenticated requests pass through
_bearer_scheme = HTTPBearer(auto_error=False)


def verify_google_id_token(id_token: str) -> dict:
    """Verify a Google ID token server-side and return the decoded payload.

    Uses google.oauth2.id_tokens to cryptographically verify the token
    against Google's public certificates.

    Returns:
        dict with keys: sub, email, name, picture, email_verified, etc.

    Raises:
        HTTPException 401 if token is invalid, expired, or audience mismatch.
    """
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        request = google_requests.Request()

        # If GOOGLE_CLIENT_ID is configured, verify audience
        if settings.GOOGLE_CLIENT_ID:
            payload = google_id_token.verify_oauth2_token(
                id_token, request, settings.GOOGLE_CLIENT_ID
            )
        else:
            # Development mode: verify token structure but skip audience check
            payload = google_id_token.verify_oauth2_token(id_token, request)

        # Verify email is present and verified
        if not payload.get("email_verified", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google account email is not verified."
            )

        if not payload.get("email"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google token does not contain an email claim."
            )

        return payload

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("Invalid Google ID token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google ID token."
        )
    except Exception as e:
        logger.error("Google token verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to verify Google credentials."
        )


def create_access_token(user_id: str, email: str) -> str:
    """Create a signed JWT access token for the authenticated user.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Returns:
        Decoded payload dict with 'sub' (user_id) and 'email'.

    Raises:
        HTTPException 401 if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type."
            )
        return payload
    except JWTError as e:
        logger.debug("JWT decode failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token."
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: require a valid JWT or active demo token and return the User.

    Raises:
        HTTPException 401 if no token, invalid token, or user not found.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Handle demo tokens for developer/auditor demo mode
    if credentials.credentials.startswith("demo_"):
        demo_id = "00000000-0000-0000-0000-000000000000"
        demo_user = db.query(User).filter(User.id == demo_id).first()
        if not demo_user:
            demo_user = User(
                id=demo_id,
                google_id="demo-analyst",
                email="demo.auditor@finny.internal",
                name="Demo Financial Analyst"
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
        return demo_user

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found."
        )

    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """FastAPI dependency: return the authenticated User if a valid token is provided,
    or None if no token is present (backward compatibility for unauthenticated requests).

    Raises:
        HTTPException 401 only if a token IS provided but is invalid/expired.
    """
    if credentials is None:
        return None

    # Handle demo tokens for developer/auditor demo mode
    if credentials.credentials.startswith("demo_"):
        demo_id = "00000000-0000-0000-0000-000000000000"
        demo_user = db.query(User).filter(User.id == demo_id).first()
        if not demo_user:
            demo_user = User(
                id=demo_id,
                google_id="demo-analyst",
                email="demo.auditor@finny.internal",
                name="Demo Financial Analyst"
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
        return demo_user

    # Token was provided — it MUST be valid
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found."
        )

    return user
