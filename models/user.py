# models/user.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, DateTime, Enum as SAEnum
from database import Base
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.prediction import Prediction  # avoid circular imports
    from models.tag import Tag

from models.tag import user_tag_association


class UserRole(str, Enum):
    admin = "admin"
    user  = "user"


class User(Base):
    __tablename__ = "users"

    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    name:            Mapped[str]      = mapped_column(String(100), nullable=False)
    email:           Mapped[str]      = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str]      = mapped_column(String(255), nullable=False)
    age:             Mapped[int]      = mapped_column(Integer, nullable=False)
    role:            Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.user)
    is_active:       Mapped[bool]     = mapped_column(Boolean, default=True)
    is_verified:     Mapped[bool]     = mapped_column(Boolean, default=False, server_default="false")
    created_at:      Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship — not a column, not in DB, pure Python navigation
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction",
        back_populates="user",
        lazy="raise",          # ← critical for async: force explicit loading
        cascade="all, delete-orphan",  # deleting user deletes their predictions
    )
    
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary=user_tag_association,
        back_populates="users",
        lazy="raise",
    )

    def __repr__(self):
        return f"<User id={self.id} email={self.email!r}>"