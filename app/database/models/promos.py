from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base

class PromoUsers(Base):
    __tablename__ = 'promo_users'

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    promo_id: Mapped[int] = mapped_column(Integer, ForeignKey("promocodes.id", ondelete="CASCADE"), primary_key=True)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Promo(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)

    promocode: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    reward: Mapped[dict] = mapped_column(JSONB)

    max_uses: Mapped[int | None]
    current_users: Mapped[int]
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    used_by: Mapped[list["User"]] = relationship("User", back_populates="used_promos", secondary="promo_users")

    @property
    def is_expired(self):
        return (self.expire_at is not None and
                self.expire_at < datetime.now())

    @property
    def is_limit_reached(self):
        return (self.max_uses is not None and
                self.max_uses <= self.current_users)

    @property
    def is_active(self):
        return (not self.is_expired and not self.is_limit_reached)