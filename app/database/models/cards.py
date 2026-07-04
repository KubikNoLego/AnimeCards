from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import CardType


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, 
                                    autoincrement=True)

    name: Mapped[str] = mapped_column(nullable=False)
    value: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    card_type: Mapped[CardType] = mapped_column(SQLEnum(CardType, 
                                            name="card_type_enum"), 
                                            default=CardType.STANDARD, 
                                            nullable=False)

    verse_id: Mapped[int] = mapped_column(ForeignKey("verses.id"))
    rarity_id: Mapped[int] = mapped_column(ForeignKey("rarities.id"))
    verse: Mapped["Verse"] = relationship("Verse", 
                                        back_populates='cards', lazy="selectin")
    rarity: Mapped["Rarity"] = relationship("Rarity", 
                                        back_populates='cards', lazy="selectin")

    icon: Mapped[str]
    shiny_icon: Mapped[str | None]

    droppable: Mapped[bool]

    owners: Mapped[list["UserCards"]] = relationship("UserCards",
                                        back_populates="card")

    @property
    def has_shiny(self) -> bool:
        return (self.shiny_icon is not None)

    def icon_path(self, shiny: bool = False) -> ValueError | str:
        if not self.has_shiny and shiny:
            return ValueError(f"Карта {self.id} не имеет шайни версии")
        
        return f"app/assets/cards/{self.verse.name}/{self.icon if not shiny else self.shiny_icon}"

    def format(self, shiny: bool = False) -> ValueError | str:
        if not self.has_shiny and shiny:
            return ValueError(f"Карта {self.id} не имеет шайни версии")
        
        price = self.price(shiny)

        text = """<b>{name}</b>
        
🌐 Вселенная: <i>{verse}</i>
🎨 Редкость: <b>{rarity}</b>
💰 Ценность: <b>{value}</b> ¥
🗂️ Тип: <i>{type}</i>
"""
        return (text.format(name=self.name, verse = self.verse.name,
                    rarity = self.rarity.name, value = price, 
                type = self.card_type.value) + 
                    ("" if not shiny else "✨ Shiny"))


    def price(self, shiny: bool) -> int:
        return self.value if not shiny else int(self.value * 1.5)

class Rarity(Base):
    __tablename__ = "rarities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, 
                                    autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    drop_rate: Mapped[int] = mapped_column(nullable=False, default=100)
    luck_multiplier: Mapped[float] = mapped_column(default=1.0)

    cards: Mapped[list["Card"]] = relationship("Card",
                                    back_populates="rarity")
    titles: Mapped[list["Title"]] = relationship("Title",
                                    back_populates="rarity")

class Verse(Base):
    __tablename__ = "verses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, 
                                autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    daily: Mapped[bool] = mapped_column(Boolean, default=False)

    cards: Mapped[list["Card"]] = relationship("Card",
                                    back_populates="verse")

class UserCards(Base):
    __tablename__ = 'usercards'

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(
        "users.id", ondelete="CASCADE"))
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey(
        "cards.id", ondelete="CASCADE"))

    shiny: Mapped[bool] = mapped_column(Boolean, default=False)

    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


    obtained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                            default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="inventory")

    card: Mapped["Card"] = relationship("Card", back_populates="owners", 
                                        lazy="selectin")