from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum

from .base import Base
from .enums import ShopItems

class DailyShopPurchase(Base):
    __tablename__ = "daily_shop_purchases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False)

    shop_date: Mapped[date] = mapped_column(
        Date, index=True, nullable=False)

    item: Mapped[ShopItems] = mapped_column(
        SQLEnum(ShopItems), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="daily_shop_purchases")
