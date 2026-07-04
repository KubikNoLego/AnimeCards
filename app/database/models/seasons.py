from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)

    name: Mapped[str] = mapped_column(String)

    banner_id: Mapped[int] = mapped_column(ForeignKey("banners.id"), 
                                        nullable=False)

    started_at: Mapped[date] = mapped_column(Date, index=True)
    ended_at: Mapped[date] = mapped_column(Date, index=True)

    banner: Mapped['Banner'] = relationship("Banner")

    @property
    def active(self) -> bool:
        return (date.today() <= self.ended_at
                and date.today() >= self.started_at)

