# schemas/auth.py
from pydantic import BaseModel, EmailStr, Field

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str = Field(min_length=1)

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int  # seconds until expiry

class TokenPayload(BaseModel):
    """Parsed JWT payload — what get_current_user returns."""
    sub:   str          # user ID as string
    email: str
    role:  str
    exp:   int          # expiry as unix timestamp
