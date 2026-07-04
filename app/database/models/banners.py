from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class BannerCard(Base):
    __tablename__ = "banner_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    banner_id: Mapped[int] = mapped_column(ForeignKey("banners.id", ondelete="CASCADE"))

    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))

    banner: Mapped["Banner"] = relationship("Banner", back_populates="cards")
    card: Mapped["Card"] = relationship("Card", lazy="selectin")

class Banner(Base):
    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    verse_id: Mapped[int | None] = mapped_column(ForeignKey("verses.id"))

    cards: Mapped[list['BannerCard']] = relationship("BannerCard", back_populates='banner', lazy="selectin")
    pities: Mapped[list["BannerPity"]] = relationship("BannerPity", back_populates='banner')

class BannerPity(Base):
    __tablename__ = "bannerpities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    banner_id: Mapped[int] = mapped_column(ForeignKey("banners.id"), nullable=False)

    ssr: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sr: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    s: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    banner: Mapped["Banner"] = relationship("Banner", back_populates="pities")