# Стандартные библиотеки
from datetime import datetime
from enum import Enum

# Сторонние библиотеки
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Boolean, func
from sqlalchemy import Enum as SQLEnum


class CardType(Enum):
    STANDARD = "standard"
    SEASONAL = "seasonal"
    LIMITED = "limited"


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
    referrer_reward: Mapped[int] = mapped_column(Integer, default=0)
    referral: Mapped["User"] = relationship("User", foreign_keys=[referral_id], lazy="selectin")

    referrer: Mapped["User"] = relationship("User",back_populates="referrals",foreign_keys=[user_id],lazy="selectin")

class UserCards(Base):
    __tablename__ = 'usercards'

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("cards.id", ondelete="CASCADE"))

    shiny: Mapped[bool] = mapped_column(Boolean, default=False)

    level: Mapped[int] = mapped_column(Integer,nullable=False,default=1)


    obtained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="inventory")

    card: Mapped["Card"] = relationship("Card", back_populates="owners")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    balance: Mapped[int] = mapped_column(default=0)
    pity: Mapped[int] = mapped_column(default=0)
    free_open: Mapped[int] = mapped_column(default=0)
    pvp_wins: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    username: Mapped[str | None] = mapped_column(String(32), default=None)
    name: Mapped[str]

    # Храним MSK-времена с timezone=True
    last_open: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Инвентарь — карточки пользователя (many-to-many)
    inventory: Mapped[list["UserCards"]] = relationship("UserCards", back_populates="user", lazy="selectin")
    battle_inventory: Mapped["BattleInventory"] = relationship("BattleInventory", back_populates="user", uselist=False)
    # Профиль — 1 к 1 связь
    profile: Mapped["Profile"] = relationship("Profile", back_populates="owner", lazy="selectin")
    # VIP подписка — 1 к 1 связь
    vip: Mapped["VipSubscription"] = relationship("VipSubscription", back_populates="user", lazy="selectin", uselist=False)

    # Рефералы — один ко многим связь (пользователи, которых пригласил этот пользователь)
    referrals: Mapped[list["Referrals"]] = relationship("Referrals", back_populates="referrer", foreign_keys=[Referrals.user_id], lazy="selectin")

    clan_member: Mapped["ClanMember"] = relationship("ClanMember", back_populates="user", lazy="selectin", uselist=False)

    # Промокоды, которые использовал этот пользователь
    used_promos: Mapped[list["Promo"]] = relationship("Promo", back_populates="used_by", secondary="promo_users", lazy="selectin")

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

class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(nullable=False)
    value: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    card_type: Mapped[CardType] = mapped_column(SQLEnum(CardType, name="card_type_enum"), default=CardType.STANDARD, nullable=False)

    verse_id: Mapped[int] = mapped_column(ForeignKey("verses.id"))
    rarity_id: Mapped[int] = mapped_column(ForeignKey("rarities.id"))
    verse: Mapped["Verse"] = relationship("Verse", back_populates='cards', lazy="selectin")
    rarity: Mapped["Rarity"] = relationship("Rarity", back_populates='cards', lazy="selectin")

    icon: Mapped[str]
    shiny_icon: Mapped[str | None]

    has_shiny: Mapped[bool]
    droppable: Mapped[bool]

    owners: Mapped[list["UserCards"]] = relationship("UserCards", back_populates="card", lazy="selectin")

class Rarity(Base):
    __tablename__ = "rarities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    drop_rate: Mapped[int] = mapped_column(nullable=False, default=100)

    cards: Mapped[list["Card"]] = relationship("Card", back_populates="rarity", lazy="selectin")
    titles: Mapped[list["Title"]] = relationship("Title", back_populates="rarity", lazy="selectin")

class Verse(Base):
    __tablename__ = "verses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    daily: Mapped[bool] = mapped_column(Boolean, default=False)

    cards: Mapped[list["Card"]] = relationship("Card", back_populates="verse", lazy="selectin")

class VipSubscription(Base):
    __tablename__ = "vip_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="vip", lazy="selectin")

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    title_id: Mapped[int | None] = mapped_column(ForeignKey("titles.id"), default=16)
    title: Mapped["Title"] = relationship("Title", back_populates="owners", lazy="selectin")
    joined: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    describe: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="profile", lazy="selectin")

    visible: Mapped[bool] = mapped_column(Boolean, default=True)

class ClanMember(Base):
    __tablename__ = "clan_members"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    clan_id: Mapped[int] = mapped_column(Integer, ForeignKey("clans.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_leader: Mapped[bool] = mapped_column(Boolean, default=False)  # True для лидера, False для участника
    contribution: Mapped[int] = mapped_column(Integer, default=0)  # Вклад в баланс клана

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="clan_member", lazy="selectin")
    clan: Mapped["Clan"] = relationship("Clan", back_populates="members", lazy="selectin")

class ClanInvitation(Base):
    __tablename__ = "clan_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clan_id: Mapped[int] = mapped_column(Integer, ForeignKey("clans.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    clan: Mapped["Clan"] = relationship("Clan", back_populates="invitations", lazy="selectin")
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id], lazy="selectin")
    receiver: Mapped["User"] = relationship("User", foreign_keys=[receiver_id], lazy="selectin")

class Clan(Base):
    __tablename__ = "clans"

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)

    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    tag: Mapped[str] = mapped_column(String(5),nullable=False,unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)

    leader_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    leader: Mapped["User"] = relationship("User", foreign_keys=[leader_id], lazy="selectin")
    members: Mapped[list["ClanMember"]] = relationship("ClanMember", back_populates="clan", lazy="selectin", cascade="all, delete-orphan")
    invitations: Mapped[list["ClanInvitation"]] = relationship("ClanInvitation", back_populates="clan", lazy="selectin", cascade="all, delete-orphan")

    balance: Mapped[int] = mapped_column(Integer, default=0)

class PromoUsers(Base):
    __tablename__ = 'promo_users'

    # Ассоциативная таблица для связи многие-ко-многим между User и Promo
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    promo_id: Mapped[int] = mapped_column(Integer, ForeignKey("promocodes.id", ondelete="CASCADE"), primary_key=True)

class Promo(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)

    promocode: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    reward: Mapped[int] = mapped_column(Integer, default=30)

    expire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Пользователи, которые использовали этот промокод
    used_by: Mapped[list["User"]] = relationship("User", back_populates="used_promos", secondary="promo_users", lazy="selectin")


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id = mapped_column(BigInteger, ForeignKey("users.id"))
    card_id = mapped_column(Integer, ForeignKey("cards.id"))
    partner_id: Mapped[int | None] = mapped_column(BigInteger,nullable=True, default=None)
    partner_card: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    partner_added_at: Mapped[datetime | None] = mapped_column(default=None)


class PvPSearchQueue(Base):
    """Очередь поиска соперников для PvP."""
    __tablename__ = "pvp_search_queue"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    deck_value: Mapped[int] = mapped_column(Integer, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)

    user: Mapped["User"] = relationship("User", lazy="selectin")


class Title(Base):
    """Титулы"""
    __tablename__ = "titles"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)

    title: Mapped[str] = mapped_column(String, nullable=False)

    buff1: Mapped[int] = mapped_column(Integer,nullable=False)
    target1: Mapped[str] = mapped_column(String(1), nullable=False)
    buff2: Mapped[int | None] = mapped_column(Integer,nullable=True)
    target2: Mapped[str | None] = mapped_column(String(1), nullable=True)

    rarity_id: Mapped[int] = mapped_column(Integer, ForeignKey("rarities.id"))
    rarity: Mapped["Rarity"] = relationship("Rarity", back_populates="titles", lazy="selectin")
    owners: Mapped[list["Profile"]] = relationship("Profile", back_populates="title", lazy="selectin")

    droppable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def buffs(self) -> list[tuple[int, str]]:
        result = [(self.buff1, self.target1)]
        if self.buff2:
            result.append((self.buff2, self.target2))
        return result

    @property
    def free_open_buff(self) -> int:
        if not any(target == 'f' for _,target in self.buffs):
            return 0
        return [value for value,target in self.buffs if target == 'f'][0]

    @property
    def time_skip(self) -> int:
        if not any(target == 't' for _,target in self.buffs):
            return 0
        return [value for value,target in self.buffs if target == 't'][0]

    @property
    def yen_boost(self) -> int:
        if not any(target=='y' for _, target in self.buffs):
            return 0
        return [value for value,target in self.buffs if target == 'y'][0]

    @property
    def luck_boost(self) -> int:
        if not any(target=='b' for _, target in self.buffs):
            return 0
        return [value for value,target in self.buffs if target == 'b'][0]


class BannerCard(Base):
    __tablename__ = "banner_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    banner_id: Mapped[int] = mapped_column(ForeignKey("banners.id", ondelete="CASCADE"))

    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))

    banner: Mapped["Banner"] = relationship("Banner", back_populates="cards", lazy="selectin")
    card: Mapped["Card"] = relationship("Card", lazy="selectin")

class Banner(Base):

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=False)

    verse_id: Mapped[int | None] = mapped_column(ForeignKey("verses.id"), nullable=True)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    cards: Mapped[list['BannerCard']] = relationship("BannerCard", back_populates='banner',lazy="select")