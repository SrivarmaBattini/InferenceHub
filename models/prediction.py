# models/prediction.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Float, String, DateTime, ForeignKey
from database import Base
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User


class Prediction(Base):
    __tablename__ = "predictions"

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    user_id:       Mapped[int]      = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),  # DB-level cascade
        nullable=False,
        index=True,
    )
    input_hash:    Mapped[str]      = mapped_column(String(64), nullable=False)
    prediction:    Mapped[float]    = mapped_column(Float, nullable=False)
    confidence:    Mapped[float]    = mapped_column(Float, nullable=False)
    model_version: Mapped[str]      = mapped_column(String(20), nullable=False)
    latency_ms:    Mapped[float]    = mapped_column(Float, nullable=False)
    created_at:    Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Many-to-one back to the user
    user: Mapped["User"] = relationship(
        "User",
        back_populates="predictions",
        lazy="raise",
    )

    def __repr__(self):
        return f"<Prediction id={self.id} user_id={self.user_id}>"