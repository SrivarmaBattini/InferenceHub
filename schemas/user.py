# schemas/user.py
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, model_validator, Field, EmailStr
from schemas.prediction import PredictionSummary

class UserRole(str, Enum):
    admin = "admin"
    user  = "user"

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    age: int = Field(ge=18)
    password: str

    @model_validator(mode="after")
    def validate_password_and_email(self):
        self.email = self.email.lower().strip()
        if not any(c.isdigit() for c in self.password):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isupper() for c in self.password):
            raise ValueError("Password must contain at least one uppercase letter")
        return self

class UpdateUserRequest(BaseModel):
    name: str | None = None
    age: int | None = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    age: int
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}

class UserListResponse(BaseModel):
    total: int
    users: list[UserResponse]

class UserWithPredictions(BaseModel):
    id:          int
    name:        str
    email:       str
    age:         int
    role:        UserRole
    created_at:  datetime
    predictions: list[PredictionSummary] = []

    model_config = {"from_attributes": True}

class UpdateRoleRequest(BaseModel):
    role: UserRole