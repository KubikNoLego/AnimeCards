from loguru import logger
from db.models import User,Card,Profile,Verse,Rarity

from datetime import datetime,timedelta,timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

RARITIES={
        1:"Обычная",
        2:"Редкая",
        3:"Мифическая",
        4:"Легендарная",
        5:"Хроно"
    }

async def create_or_update_user(id: int,
                        username: str | None,name: str,
                        describe:str, 
                        session:AsyncSession):
    try:
        user = await session.scalar(select(User).filter_by(id=id))
        if not user:
            user = User(id=id,
                        username=username,
                        name=name,
                        last_open=datetime.now(timezone.utc)-timedelta(hours=3),
                        joined=datetime.now(timezone.utc)
                    )
            user.profile = Profile(user_id=id,describe=describe)
            session.add(user)
        else:
            user.username = username
            user.name = name
        await session.commit()
    except Exception as _ex:
        logger.error(_ex)


async def get_user_place_on_top(session:AsyncSession,user:User):
    stmt = select(func.count(User.id)).where(User.yens > user.yens)
    result = await session.execute(stmt)
    count_higher = result.scalar()
    
    return count_higher + 1 if count_higher is not None else 0