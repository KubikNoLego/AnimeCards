from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class PvPSearchQueue(Base):
    """Очередь поиска соперников для PvP."""
    __tablename__ = "pvp_search_queue"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    deck_value: Mapped[int] = mapped_column(Integer, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    user: Mapped["User"] = relationship("User")

class BattleInventory(Base):
    __tablename__ = "battle_inventories"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    common_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id"))
    uncommon_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id"))
    mythic_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id"))
    legend_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id"))
    hrono_id: Mapped[int | None] = mapped_column(ForeignKey("cards.id"))

    common: Mapped["Card"] = relationship("Card", foreign_keys=[common_id], lazy="selectin")
    uncommon: Mapped["Card"] = relationship("Card", foreign_keys=[uncommon_id], lazy="selectin")
    mythic: Mapped["Card"] = relationship("Card", foreign_keys=[mythic_id], lazy="selectin")
    legend: Mapped["Card"] = relationship("Card", foreign_keys=[legend_id], lazy="selectin")
    hrono: Mapped["Card"] = relationship("Card", foreign_keys=[hrono_id], lazy="selectin")

    user: Mapped["User"] = relationship("User", back_populates="battle_inventory", lazy="selectin")

    @property
    def cards(self):
        cards = []
        if self.common:
            cards.append(self.common)
        if self.uncommon:
            cards.append(self.uncommon)
        if self.mythic:
            cards.append(self.mythic)
        if self.legend:
            cards.append(self.legend)
        if self.hrono:
            cards.append(self.hrono)

        return cards

    @property
    def total_cards_count(self) -> int:
        return len(self.cards)

    @property
    def is_full(self) -> bool:
        return self.total_cards_count == 5