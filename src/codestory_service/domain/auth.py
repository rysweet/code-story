"""Domain models for authentication and authorization.

This module defines the domain models for authentication-related entities,
including login requests, token responses, and user information.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Model for user login request."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

    @field_validator("username")
    @classmethod
    def username_must_not_be_empty(cls, v: str) -> str:
        """Validate that username is not empty."""
        if not v.strip():
            raise ValueError("Username must not be empty")
        return v

    @field_validator("password")
    @classmethod
    def password_must_not_be_empty(cls, v: str) -> str:
        """Validate that password is not empty."""
        if not v.strip():
            raise ValueError("Password must not be empty")
        return v


class TokenResponse(BaseModel):
    """Model for token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    scope: str = Field(..., description="Token scope")


class UserInfo(BaseModel):
    """Model for user information."""

    id: str = Field(..., description="User ID")
    name: str = Field(..., description="Display name")
    email: EmailStr | None = Field(None, description="Email address")
    roles: list[str] = Field(default_factory=list, description="User roles")
    is_authenticated: bool = Field(True, description="Whether the user is authenticated")


class RoleInfo(BaseModel):
    """Model for role information."""

    id: str = Field(..., description="Role ID")
    name: str = Field(..., description="Role name")
    description: str | None = Field(None, description="Role description")
    permissions: list[str] = Field(
        default_factory=list, description="Permissions granted by this role"
    )


class AuthResponse(BaseModel):
    """Model for authentication response."""

    success: bool = Field(..., description="Whether authentication was successful")
    message: str = Field(..., description="Authentication message")
    token: TokenResponse | None = Field(None, description="Token, if authentication was successful")
    user: UserInfo | None = Field(
        None, description="User information, if authentication was successful"
    )


class AuthError(BaseModel):
    """Model for authentication error."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: str | None = Field(None, description="Error details")
