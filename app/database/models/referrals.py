from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class Referrals(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    referral_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    reward: Mapped[int] = mapped_column(Integer, default=0)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)

    referral: Mapped["User"] = relationship("User", foreign_keys=[referral_id])
    referrer: Mapped["User"] = relationship("User", back_populates="referrals", foreign_keys=[user_id])
