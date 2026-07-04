from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base
from .cards import Rarity

class Title(Base):
    """Титулы"""
    __tablename__ = "titles"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, 
                                    primary_key=True)

    title: Mapped[str] = mapped_column(String, nullable=False)

    buffs: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)

    rarity_id: Mapped[int] = mapped_column(Integer, ForeignKey("rarities.id"))
    rarity: Mapped["Rarity"] = relationship("Rarity",
                                    back_populates="titles")
    owners: Mapped[list["Profile"]] = relationship("Profile",
                                    back_populates="title")
    users: Mapped[list["UserTitle"]] = relationship("UserTitle",
                                    back_populates="title")

    droppable: Mapped[bool] = mapped_column(Boolean, default=True, 
                                            nullable=False)

    def get_buff(self, buff: str) -> int:
        return self.buffs.get(buff, None)

    @property
    def time_skip(self) -> int:
        return self.get_buff("time_skip")

    @property
    def yen_boost(self) -> int:
        return self.get_buff("yen_boost")

    @property
    def luck_boost(self) -> int:
        return self.get_buff("luck_boost")
    
    @property
    def name(self) -> str:
        return f"「 {self.title} 」"

class UserTitle(Base):
    __tablename__ = "usertitles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(
        "users.id", ondelete="CASCADE"))
    title_id: Mapped[int] = mapped_column(ForeignKey(
        "titles.id", ondelete="CASCADE"))
    obtained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), 
                                        default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="titles")
    title: Mapped["Title"] = relationship("Title", back_populates="users")
