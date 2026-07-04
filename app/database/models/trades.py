from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id = mapped_column(BigInteger, ForeignKey("users.id"))
    card_id = mapped_column(Integer, ForeignKey("cards.id"))
    partner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)
    partner_card: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    partner_added_at: Mapped[datetime | None] = mapped_column(default=None)