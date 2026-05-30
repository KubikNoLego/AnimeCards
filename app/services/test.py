import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database.models import Banner, User
from app.services.GachaService import GachaService, LuckService

class Message:
    class from_user:
        id = 8494031501

async def main():
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/animecards"

    engine = create_async_engine(DATABASE_URL)

    Session = async_sessionmaker(
    engine,
    expire_on_commit=False)

    rarities1 = [0,0,0,0,0]
    rarities2 = [0,0,0,0,0]
    cards = [0,0,0,0,0]
    shinies = 0

    async with Session() as session:
        
        banner = await session.scalar(select(Banner).where(Banner.id == 1))
        user = (await session.scalars(select(User).limit(2))).all()[1]
        message = Message
        message.from_user.id = user.id

        print("Тест 1")

        for _ in range(100):
            rarity = await GachaService._roll_rarity(session,user,banner, LuckService.UserBuffs())
            rarities1[rarity.id-1] +=1
        
        pity = await GachaService._get_pity(session,banner.id, user.id)
        pity.pity = 0

        print("Тест 2")

        for _ in range(100):
            rarity = await GachaService._roll_rarity(session,user,banner, LuckService.UserBuffs(1.5))
            rarities2[rarity.id-1] +=1
        
        pity = await GachaService._get_pity(session,banner.id, user.id)
        pity.pity = 0
        
        print("Тест 3")
        print(f"Буст к удаче + {(await LuckService.calculate_buffs(user)).luck} %")

        for _ in range(100):
            card, shiny = await GachaService.open_card(message, session, 1)
            cards[card.rarity_id-1] += 1
            shinies += 1 if shiny else 0

        print('-'*50)
        print()
        print("Результаты без баффов")
        print("C\tB\tS\tSR\tSSR")
        print(*rarities1, sep='\t')
        print()
        print('-'*50)
        print('Результаты с +50%')
        print()
        print("C\tB\tS\tSR\tSSR")
        print(*rarities2, sep='\t')
        print('-'*50)
        print()
        print("Результаты открытия карт")
        print("C\tB\tS\tSR\tSSR")
        print(*cards, sep='\t')
        print(f"shiny - {shinies} шт.")
        print()
        print('-'*50)

asyncio.run(main())
