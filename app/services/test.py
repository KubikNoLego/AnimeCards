import asyncio
from collections import defaultdict

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.services.GachaService import GachaService, LuckService
from app.database.models import User, Banner, BannerPity


async def simulate_rolls(
    session,
    user,
    banner,
    buffs,
    rolls: int
):
    stats = defaultdict(int)

    pity_history = []

    for roll_number in range(1, rolls + 1):

        # текущий pity ДО ролла
        banner_pity = await GachaService._get_pity(
            session,
            banner.id,
            user.id
        )

        current_pity = banner_pity.pity

        rarity = await GachaService._roll_rarity(
            session=session,
            user=user,
            banner=banner,
            buffs=buffs
        )

        stats[rarity.id] += 1

        pity_history.append({
            "roll": roll_number,
            "pity_before": current_pity,
            "rarity": rarity.id
        })

        # =========================
        # ОБНОВЛЯЕМ PITY
        # =========================

        # SSR / rarity 5
        if rarity.id == 5:
            banner_pity.pity = 0

        else:
            banner_pity.pity += 1

        await session.commit()

    return stats, pity_history


async def print_results(title, stats):
    print("=" * 60)
    print(title)
    print("C\tB\tS\tSR\tSSR")

    print(
        stats[1],
        stats[2],
        stats[3],
        stats[4],
        stats[5],
        sep="\t"
    )

    print("=" * 60)


async def print_soft_pity_info(history):

    print("\nSOFT PITY PROC CHECK\n")

    for item in history:

        pity = item["pity_before"]
        rarity = item["rarity"]

        # показываем только high pity роллы
        if pity >= 70 or rarity == 5:
            print(
                f"Roll {item['roll']:>3} | "
                f"Pity: {pity:>3} | "
                f"Rarity: {rarity}"
            )


async def main():

    DATABASE_URL = (
        "postgresql+asyncpg://"
        "postgres:postgres@127.0.0.1:5432/animecards"
    )

    engine = create_async_engine(DATABASE_URL)

    Session = async_sessionmaker(
        engine,
        expire_on_commit=False
    )

    async with Session() as session:

        user = await session.scalar(
            select(User).limit(1)
        )

        banner = await session.scalar(
            select(Banner).limit(1)
        )

        if not user or not banner:
            print("Нет User или Banner в БД")
            return

        # =========================
        # RESET PITY
        # =========================

        pity = await GachaService._get_pity(
            session,
            banner.id,
            user.id
        )

        pity.pity = 0

        await session.commit()

        # =========================
        # БЕЗ БАФФОВ
        # =========================

        stats1, history1 = await simulate_rolls(
            session=session,
            user=user,
            banner=banner,
            buffs=LuckService.UserBuffs(),
            rolls=300
        )

        await print_results(
            "300 ОТКРЫТИЙ БЕЗ БАФФОВ",
            stats1
        )

        await print_soft_pity_info(history1)

        # =========================
        # RESET PITY
        # =========================

        pity.pity = 0

        await session.commit()

        # =========================
        # С БАФФОМ
        # =========================

        stats2, history2 = await simulate_rolls(
            session=session,
            user=user,
            banner=banner,
            buffs=LuckService.UserBuffs(1.5),
            rolls=300
        )

        await print_results(
            "300 ОТКРЫТИЙ С БАФФОМ +50%",
            stats2
        )

        await print_soft_pity_info(history2)


asyncio.run(main())