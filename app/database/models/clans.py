from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class ClanMember(Base):
    __tablename__ = "clan_members"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    clan_id: Mapped[int] = mapped_column(Integer, ForeignKey("clans.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_leader: Mapped[bool] = mapped_column(Boolean, default=False)
    contribution: Mapped[int] = mapped_column(Integer, default=0)
    season_contribution: Mapped[int] = mapped_column(Integer, default=0)

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="clan_member")
    clan: Mapped["Clan"] = relationship("Clan", back_populates="members", lazy="selectin")

class ClanInvitation(Base):
    __tablename__ = "clan_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clan_id: Mapped[int] = mapped_column(Integer, ForeignKey("clans.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    clan: Mapped["Clan"] = relationship("Clan", back_populates="invitations")
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id])
    receiver: Mapped["User"] = relationship("User", foreign_keys=[receiver_id])

class Clan(Base):
    __tablename__ = "clans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), 
                                                nullable=False)
    
    balance: Mapped[int] = mapped_column(Integer, default=0)

    leader_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))

    leader: Mapped["User"] = relationship("User", foreign_keys=[leader_id])
    members: Mapped[list["ClanMember"]] = relationship("ClanMember", back_populates="clan", lazy="selectin", cascade="all, delete-orphan")
    invitations: Mapped[list["ClanInvitation"]] = relationship("ClanInvitation", back_populates="clan", cascade="all, delete-orphan")

    @property
    def season_balance(self) -> int:
        return sum(member.season_contribution for member in self.members)
    
    @property
    def rating(self) -> int:
        
        rating = (
            sum(member.user.season_balance for member in self.members) * 0.3 +
            self.season_balance * 0.4 +
            sum(member.user.pvp_wins for member in self.members) * 0.3)
        
        return rating