# Стандартные библиотеки
from datetime import datetime

# Сторонние библиотеки
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Boolean

class Base(DeclarativeBase):
    def __repr__(self) -> str:
        columns_data = []
        for column in self.__table__.columns:
            column_name = column.key
            column_value = getattr(self, column_name, None)
            columns_data.append(f"{column_name}={repr(column_value)}")

        columns_str = ", ".join(columns_data)

        return f"<{self.__class__.__name__}; {columns_str}>"

class Referrals(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger,ForeignKey("users.id"))
    referral_id: Mapped[int] = mapped_column(BigInteger,ForeignKey("users.id"))
    referrer_reward: Mapped[int] = mapped_column(default=0)

    referrer: Mapped["User"] = relationship("User",back_populates="referrals",foreign_keys=[user_id],lazy="selectin")

class UserCards(Base):
    __tablename__ = 'usercards'

    # Ассоциативная таблица для связи многие-ко-многим между User и Card
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    yens: Mapped[int] = mapped_column(default=0)
    seasons_yens: Mapped[int] = mapped_column(server_default=0)
    pity: Mapped[int] = mapped_column(default=100)

    username: Mapped[str | None] = mapped_column(String(32), default=None)
    name: Mapped[str] = mapped_column(String(100))

    # Храним UTC-времена с timezone=True
    last_open: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    joined: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Инвентарь — карточки пользователя (many-to-many)
    inventory: Mapped[list["Card"]] = relationship("Card", back_populates="owners", secondary="usercards", lazy="selectin")
    # Профиль — 1 к 1 связь
    profile: Mapped["Profile"] = relationship("Profile", back_populates="owner", lazy="selectin")
    # VIP подписка — 1 к 1 связь
    vip: Mapped["VipSubscription"] = relationship("VipSubscription", back_populates="user", lazy="selectin", uselist=False)

    # Рефералы — один ко многим связь (пользователи, которых пригласил этот пользователь)
    referrals: Mapped[list["Referrals"]] = relationship("Referrals", back_populates="referrer", foreign_keys="[Referrals.user_id]", lazy="selectin")

    start: Mapped[bool] = mapped_column(Boolean, default=True)

class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verse_name: Mapped[str] = mapped_column(String(50), ForeignKey("verses.name"))
    rarity_name: Mapped[str] = mapped_column(String(50), ForeignKey("rarities.name"))
    value: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Связи к объектам Rarity и Verse
    rarity: Mapped["Rarity"] = relationship("Rarity", back_populates="cards", lazy="selectin")
    verse: Mapped["Verse"] = relationship("Verse", back_populates="cards", lazy="selectin")

    shiny: Mapped[bool] = mapped_column(Boolean, default=False)
    can_drop: Mapped[bool] = mapped_column(Boolean, default=True)

    owners: Mapped[list["User"] | None] = relationship("User", back_populates="inventory", secondary="usercards", lazy="selectin")

class Rarity(Base):
    __tablename__ = "rarities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    cards: Mapped[list["Card"]] = relationship("Card", back_populates="rarity", lazy="selectin")

class Verse(Base):
    __tablename__ = "verses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    cards: Mapped[list["Card"]] = relationship("Card", back_populates="verse", lazy="selectin")

class VipSubscription(Base):
    __tablename__ = "vip_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), default=None)

    user: Mapped["User"] = relationship("User", back_populates="vip", lazy="selectin")

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))

    describe: Mapped[str] = mapped_column(String(70), default="", nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="profile", lazy="selectin")

    @property
    def yens(self) -> int:
        return self.owner.yens if self.owner else 0
    
    @property
    def seasons_yens(self) -> int:
        return self.owner.yens if self.owner else 0
