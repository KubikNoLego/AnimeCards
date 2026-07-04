from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .referrals import Referrals

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    balance: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)

    free_standard_opens: Mapped[int] = mapped_column(default=0)
    free_season_opens: Mapped[int] = mapped_column(default=0)
    luck_boosts: Mapped[int] = mapped_column(default=0)
    yen_boosts: Mapped[int] = mapped_column(default=0)
    duplicators: Mapped[int] = mapped_column(default=0)

    username: Mapped[str | None] = mapped_column(String(32), default=None)
    name: Mapped[str]

    last_open: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    inventory: Mapped[list["UserCards"]] = relationship(
        "UserCards", back_populates="user", lazy="selectin")
    battle_inventory: Mapped["BattleInventory"] = relationship(
        "BattleInventory", back_populates="user", uselist=False)
    titles: Mapped[list["UserTitle"]] = relationship(
        "UserTitle", back_populates="user", lazy="selectin",
        cascade="all, delete-orphan")

    profile: Mapped["Profile"] = relationship(
        "Profile", back_populates="owner", lazy="selectin")
    vip: Mapped["VipSubscription"] = relationship(
        "VipSubscription", back_populates="user",
        lazy="selectin", uselist=False)

    referrals: Mapped[list["Referrals"]] = relationship(
        "Referrals", back_populates="referrer",
        foreign_keys=[Referrals.user_id],
        lazy="selectin")
    clan_member: Mapped["ClanMember"] = relationship(
        "ClanMember", back_populates="user", lazy="selectin", uselist=False)

    used_promos: Mapped[list["Promo"]] = relationship(
        "Promo", back_populates="used_by", secondary="promo_users")
    
    daily_shop_purchases: Mapped[list["DailyShopPurchase"]] = relationship(
        "DailyShopPurchase", back_populates="user", lazy="selectin")

    seasons: Mapped[list["UserSeason"]] = relationship("UserSeason", back_populates="user")

    @property
    def clan(self):
        if self.clan_member:
            return self.clan_member.clan
        else: return None

    @property
    def today_shop_purchases(self):
        today = datetime.today().date()

        return {purchase.item for purchase in self.daily_shop_purchases
                if purchase.shop_date == today}
    
    @property
    def unlocked_titles(self):
        return [ut.title for ut in self.titles]
    


class VipSubscription(Base):
    __tablename__ = "vip_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(
                                "users.id", ondelete="CASCADE"), unique=True)
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(
        "User", back_populates="vip", lazy="selectin")

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, 
                                    autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger,
                        ForeignKey("users.id", ondelete="CASCADE"),
                        unique=True)

    title_id: Mapped[int | None] = mapped_column(ForeignKey("titles.id"), 
                                                default=16)
    title: Mapped["Title"] = relationship("Title", back_populates="owners", 
                                        lazy="selectin")

    joined: Mapped[datetime] = mapped_column(DateTime(timezone=True), 
                                            nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="profile", 
                                        lazy="selectin")

class UserSeason(Base):
    __tablename__ = "user_season"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), primary_key=True)

    balance: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    contribution: Mapped[int] = mapped_column(Integer, default=0)
    opens: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped['User'] = relationship("User", back_populates="seasons")
    season: Mapped['Season'] = relationship("Season")
