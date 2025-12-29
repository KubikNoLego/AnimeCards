from datetime import datetime
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,relationship
from sqlalchemy import BigInteger,VARCHAR,DateTime,ForeignKey,Column,Integer

class Base(DeclarativeBase):
    def __repr__(self) -> str:
        columns_data = []
        for column in self.__table__.columns:
            column_name = column.key
            column_value = getattr(self, column_name, None)
            columns_data.append(f"{column_name}={repr(column_value)}")
        
        columns_str = ", ".join(columns_data)
        
        return f"<{self.__class__.__name__}; {columns_str}>"

class UserCards(Base):
    __tablename__ = 'usercards'

    user_id = Column("user_id",BigInteger,ForeignKey("users.id",ondelete="CASCADE"),primary_key=True)
    card_id = Column("card_id",Integer,ForeignKey("cards.id",ondelete="CASCADE"),primary_key=True)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger,primary_key=True)
    yens: Mapped[int] = mapped_column(default=0)
    guarant: Mapped[int] = mapped_column(default=100)

    username: Mapped[str | None] = mapped_column(VARCHAR(32),default=None)
    name: Mapped[str]
    
    last_open: Mapped[datetime] = mapped_column(DateTime(True),nullable=False)
    joined: Mapped[datetime] = mapped_column(DateTime(True),nullable=False)

    inventory: Mapped[list["Card"]] = relationship("Card",back_populates="owners",secondary="usercards",lazy="selectin")
    profile: Mapped["Profile"] = relationship("Profile",back_populates="owner",lazy="selectin")

    start: Mapped[bool] = mapped_column(default=True)

class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    verse_name: Mapped[str] = mapped_column(ForeignKey("verses.name"))
    rarity_name: Mapped[str] = mapped_column(ForeignKey("rarities.name"))
    value: Mapped[int] = mapped_column(default=1,nullable=False)

    name: Mapped[str] = mapped_column(nullable=False)
    icon: Mapped[str] = mapped_column(nullable=True)

    rarity: Mapped["Rarity"] = relationship(back_populates="cards", lazy="selectin") 
    verse: Mapped["Verse"] = relationship(back_populates="cards",lazy="selectin")

    shiny: Mapped[bool] = mapped_column(default=False)
    can_drop: Mapped[bool] = mapped_column(default=True)

    owners: Mapped[list["User"]] = relationship("User",back_populates="inventory",secondary="usercards",lazy="selectin")

class Rarity(Base):
    __tablename__ = "rarities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(unique=True)

    cards: Mapped[list["Card"]] = relationship(back_populates="rarity",lazy="selectin")

class Verse(Base):
    __tablename__ = "verses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(unique=True)

    cards: Mapped[list["Card"]] = relationship(back_populates="verse",lazy="selectin")

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger,ForeignKey("users.id",ondelete="CASCADE"))

    describe: Mapped[str] = mapped_column(VARCHAR(70),default="",nullable=False)

    owner: Mapped["User"] = relationship("User",back_populates="profile",lazy="selectin")

    @property
    def yens(self) -> int:
        return self.owner.yens if self.owner else 0
    


