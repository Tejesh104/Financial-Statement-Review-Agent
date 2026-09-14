"""Authentication API routes — Google Sign-In, JWT management, user profile."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.core.security import (
    verify_google_id_token,
    create_access_token,
    get_current_user,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------- Request / Response Schemas ----------

class GoogleAuthRequest(BaseModel):
    """Request body for Google authentication."""
    id_token: str = Field(..., description="Google ID token from client-side sign-in")


class AuthResponse(BaseModel):
    """Response after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    user: "UserProfile"


class UserProfile(BaseModel):
    """Public user profile information."""
    id: str
    email: str
    name: str | None = None
    picture_url: str | None = None
    created_at: str
    last_login_at: str


# Fix forward reference
AuthResponse.model_rebuild()


# ---------- Endpoints ----------

@router.post(
    "/google",
    response_model=AuthResponse,
    summary="Authenticate with Google",
    description=(
        "Verify a Google ID token server-side, create or recognize the user, "
        "and return a JWT access token for subsequent authenticated API requests."
    ),
)
def authenticate_with_google(
    body: GoogleAuthRequest,
    db: Session = Depends(get_db),
):
    """Verify Google ID token, create/login user, return JWT."""
    # 1. Verify the Google token server-side (cryptographic verification)
    google_payload = verify_google_id_token(body.id_token)

    google_id = google_payload["sub"]
    email = google_payload["email"]
    name = google_payload.get("name", "")
    picture = google_payload.get("picture", "")

    # 2. Find or create user
    user = db.query(User).filter(User.google_id == google_id).first()

    if user:
        # Existing user — update last login and any changed profile fields
        user.last_login_at = datetime.now(timezone.utc)
        if name and name != user.name:
            user.name = name
        if picture and picture != user.picture_url:
            user.picture_url = picture
        db.commit()
        db.refresh(user)
        logger.info("Existing user logged in: %s (%s)", email, user.id)
    else:
        # New user registration
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture_url=picture,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("New user registered: %s (%s)", email, user.id)

    # 3. Create JWT access token
    access_token = create_access_token(user.id, user.email)

    return AuthResponse(
        access_token=access_token,
        user=UserProfile(
            id=user.id,
            email=user.email,
            name=user.name,
            picture_url=user.picture_url,
            created_at=user.created_at.isoformat(),
            last_login_at=user.last_login_at.isoformat(),
        ),
    )


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
    description="Return the profile of the currently authenticated user.",
)
def get_me(current_user: User = Depends(get_current_user)):
    """Return authenticated user's profile."""
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture_url=current_user.picture_url,
        created_at=current_user.created_at.isoformat(),
        last_login_at=current_user.last_login_at.isoformat(),
    )


@router.post(
    "/logout",
    summary="Logout (advisory)",
    description=(
        "Advisory logout endpoint. Since JWTs are stateless, the client should "
        "discard the token. This endpoint exists for API completeness and can be "
        "extended with token blacklisting if needed."
    ),
)
def logout(current_user: User = Depends(get_current_user)):
    """Advisory logout — client should discard the token."""
    logger.info("User %s (%s) logged out", current_user.email, current_user.id)
    return {"message": "Logged out successfully. Please discard your access token."}
