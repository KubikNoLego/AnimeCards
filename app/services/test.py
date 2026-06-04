import asyncio
from collections import Counter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database.models import Banner, CardType, User
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

    cards_standart = [0,0,0,0,0]
    verse_count1 = 0
    verse_cards = []
    season_cards_count = 0
    season_cards = Counter()
    cards_season = [0,0,0,0,0]
    season_cards_count_1 = 0
    season_cards_1 = Counter()
    verse_cards_1 = []
    verse_count2 = 0

    async with Session() as session:
        
        user = (await session.scalars(select(User).limit(2))).all()[1]
        message = Message
        message.from_user.id = user.id

        #print("Тест стандартных банеров")
#
        #for _ in range(1000):
        #    card, shiny = await GachaService._roll_standard_banner(session, user, await LuckService.calculate_buffs(user))
        #    if card.card_type == CardType.SEASONAL:
        #        season_cards_count += 1
        #        season_cards[card.name] += 1
        #    if card.card_type == CardType.STANDARD:
        #        cards_standart[card.rarity_id-1] += 1
        #    if card.verse_id == 14:
        #        print(card.name)
        #        verse_count2 += 1
        #        verse_cards.append(card.name)
        #    
#
        #print("Тест 2")
#
        #for _ in range(1000):
        #    card, shiny = await GachaService._roll_season_banner(session, user, await LuckService.calculate_buffs(user))
        #    if card.card_type == CardType.SEASONAL:
        #        season_cards_count_1 += 1
        #        season_cards_1[card.name] += 1
        #    if card.card_type == CardType.STANDARD:
        #        cards_season[card.rarity_id-1] += 1
        #    if card.verse_id == 14:
        #        print(card.name)
        #        verse_count1 += 1
        #        verse_cards_1.append(card.name)
#
        #print('-'*50)
        #print()
        #print("Результаты без бонусов")
        #print("C\tB\tS\tSR\tSSR")
        #print(*cards_standart, sep='\t')
        #print("VERSE COUNT\tSEASON COUNT")
        #print(verse_count1,season_cards_count, sep="\t")
        #print()
        #print(f"VERSE CARDS: {verse_cards}")
        #print(f"SEASON CARDS: {season_cards}")
        #print()
        #print('-'*50)
        #print('Результаты с +50%')
        #print()
        #print("C\tB\tS\tSR\tSSR")
        #print(*cards_season, sep='\t')
        #print("VERSE COUNT\tSEASON COUNT")
        #print(verse_count2,season_cards_count_1, sep="\t")
        #print()
        #print(f"VERSE CARDS: {verse_cards}")
        #print(f"SEASON CARDS: {season_cards}")
        #print('-'*50)
        #print()

        pocket = 0
        others = 0
        shinyes = 0

        for _ in range(100):

            pity = await GachaService._get_pity(session, 2, user.id)
            pity.ssr_pity = 100

            card, shiny = await GachaService.open_card(message, session, 2, 428)

            if card.card_type == CardType.STANDARD:
                others += 1
            
            elif card.id == 428:
                pocket += 1

            else:
                print(card.name)

            if shiny : shinyes += 1

        print("\n"* 4)
        print(pocket, others, shinyes, sep="\n")

asyncio.run(main())
