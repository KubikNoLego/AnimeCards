#!/usr/bin/env python3

from datetime import datetime
from datetime import datetime, timedelta
import json

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import mapped_column, relationship, sessionmaker, Session

from .database.models import Banner, Card, UserCards, Verse, Rarity, Base, CardType, User, Profile, Clan, ClanMember, Title

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5432/animecards"

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def model_to_dict(obj):
    """Преобразование SQLAlchemy объекта в dict"""

    return {
        column.name: getattr(obj, column.name)
        for column in obj.__table__.columns
    }

def drop_tables(engine):
    """Удаление всех таблиц"""

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    with engine.begin() as connection:
        for table in tables:
            try:
                connection.execute(
                    text(f"DROP TABLE IF EXISTS {table} CASCADE")
                )
                print(f"[DROP] {table}")
            except Exception as e:
                print(f"[ERROR] DROP {table}: {e}")



def reset_sequences(engine):
    """Сброс sequence для SERIAL id"""

    queries = [
        "ALTER SEQUENCE cards_id_seq RESTART WITH 1",
        "ALTER SEQUENCE verses_id_seq RESTART WITH 1",
        "ALTER SEQUENCE rarities_id_seq RESTART WITH 1",
    ]

    with engine.begin() as connection:
        for query in queries:
            try:
                connection.execute(text(query))
            except Exception:
                pass


def export_table(session, table_name, output_file):

    print(f"[EXPORT] {table_name}")

    rows = session.execute(
        text(f"SELECT * FROM {table_name}")
    ).mappings().all()

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            [dict(row) for row in rows],
            f,
            ensure_ascii=False,
            indent=4,
            default=str
        )

    print(f"[OK] {output_file}")


def recreate_tables(engine):
    """Создание таблиц заново"""

    print("\n[CREATE] Создание таблиц...")

    Base.metadata.create_all(engine)

    print("[OK] Таблицы созданы")


def recreate_verses(session):
    with open("verses.json", encoding="utf-8") as f:
        verses = json.load(f)

    for verse in verses:
        session.add(Verse(name=verse['name']))
    session.commit()

def recreate_rarities(session):
    with open("rarities.json", encoding="utf-8") as f:
        rarities = json.load(f)

    for rarity in rarities:
        session.add(Rarity(name=get_russian_rarity_mapping().get(rarity['name'])))
    session.commit()

old_to_new = {}
shiny_to_base = {}

def get_rarity_mapping():
    """Возвращает маппинг старых названий редкостей на новые"""
    return {
        "common": "C",
        "uncommon": "B",
        "mythic": "S",
        "legend": "SR",
        "hrono": "SSR",
    }

def get_russian_rarity_mapping():
    """Возвращает маппинг русских названий редкостей на новые"""
    return {
        "Обычный": "C",
        "Редкий": "B",
        "Мифический": "S",
        "Легендарный": "SR",
        "Хроно": "SSR",
        "Лимитированный": "L",
    }

def update_icon_path(old_icon_name):
    """Обновляет путь иконки с новым форматом редкости"""
    import re

    # Извлекаем редкость из старого имени иконки
    # Поддерживаем любые расширения файлов, а не только PNG
    match = re.search(r'card_.*?_(.+?)(?:\(shiny\))?\.[^.]+$', old_icon_name)
    if not match:
        return old_icon_name

    old_rarity = match.group(1)
    rarity_mapping = get_rarity_mapping()
    new_rarity = rarity_mapping.get(old_rarity, old_rarity)

    # Формируем новое имя иконки
    if "shiny" in old_icon_name.lower():
        new_icon_name = old_icon_name.replace(f"_{old_rarity}(shiny)", f"_{new_rarity}(shiny)")
    else:
        # Заменяем только суффикс редкости, сохраняя расширение
        import os
        name_without_ext = os.path.splitext(old_icon_name)[0]
        ext = os.path.splitext(old_icon_name)[1]
        new_icon_name = name_without_ext.replace(f"_{old_rarity}", f"_{new_rarity}") + ext

    return new_icon_name

BUFF_MAPPING = {
    "f": "free_open",
    "t": "time_skip",
    "y": "yen_boost",
    "b": "luck_boost",
}


def recreate_titles(session):
    with open("titles.json", encoding="utf-8") as f:
        titles = json.load(f)

    for title_data in titles:
        buffs = {}

        if title_data["target1"]:
            buffs[BUFF_MAPPING[title_data["target1"]]] = title_data["buff1"]

        if title_data["target2"]:
            buffs[BUFF_MAPPING[title_data["target2"]]] = title_data["buff2"]

        session.add(
            Title(
                id=title_data["id"],
                title=title_data["title"],
                buffs=buffs,
                rarity_id=title_data["rarity_id"],
                droppable=title_data["droppable"],
            )
        )

    session.commit()

def recreate_cards(session):
    with open("cards.json", encoding="utf-8") as f:
        cards = json.load(f)

    base_cards = {}

    for card in cards:
        if card["shiny"]:
            continue

        verse = session.scalar(select(Verse).where(Verse.name == card['verse_name']))
        rarity_name = get_russian_rarity_mapping().get(card['rarity_name'])
        rarity = session.scalar(select(Rarity).where(Rarity.name == rarity_name))

        # Обновляем путь к иконке
        updated_icon = update_icon_path(card['icon'])

        new_card = Card(name=card['name'], value=card['value'],
            card_type=CardType.STANDARD,verse_id=verse.id,rarity_id=rarity.id,
            icon=updated_icon,has_shiny=False,droppable=card['can_drop'])
        session.add(new_card)
        session.flush()
        old_to_new[card['id']] = new_card.id
        base_cards[card["id"]] = new_card

    session.commit()

    for card in cards:
        if not card["shiny"]:
            continue

        verse = session.scalar(select(Verse).where(Verse.name == card['verse_name']))
        rarity_name = get_russian_rarity_mapping().get(card['rarity_name'])
        rarity = session.scalar(select(Rarity).where(Rarity.name == rarity_name))

        if card['id'] == 362: card['name'] = "Сид Кагэно"

        base_card = session.scalar(
            select(Card).where(
                Card.name == card["name"],
                Card.verse_id == verse.id,
                Card.rarity_id == rarity.id))

        if not base_card:
            print(f"Missing base for {card['id']}")
            continue

        base_card.has_shiny = True
        # Обновляем путь к shiny иконке
        base_card.shiny_icon = update_icon_path(card["icon"])

        shiny_to_base[card['id']] = base_card.id


    session.commit()

def reset_all_sequences(engine):
    inspector = inspect(engine)

    with engine.begin() as conn:

        for table_name in inspector.get_table_names():

            pk = inspector.get_pk_constraint(table_name)
            if not pk or not pk["constrained_columns"]:
                continue

            pk_column = pk["constrained_columns"][0]

            try:
                seq_name = conn.execute(
                    text("""
                        SELECT pg_get_serial_sequence(:table, :column)
                    """),
                    {"table": table_name, "column": pk_column}
                ).scalar()

                if not seq_name:
                    continue

                max_id = conn.execute(
                    text(f"""
                        SELECT COALESCE(MAX({pk_column}), 0)
                        FROM {table_name}
                    """)
                ).scalar()

                if max_id == 0:
                    conn.execute(
                        text("SELECT setval(:seq, 1, false)"),
                        {"seq": seq_name}
                    )
                    print(f"[SEQ FIX] {table_name}.{pk_column} -> 1 (empty table)")
                else:
                    conn.execute(
                        text("SELECT setval(:seq, :val, true)"),
                        {"seq": seq_name, "val": max_id}
                    )
                    print(f"[SEQ FIX] {table_name}.{pk_column} -> {max_id}")

            except Exception as e:
                print(f"[SKIP] {table_name}: {e}")

def recreate_usercards(session):
    with open("cards.json", encoding="utf-8") as f:
        cards = json.load(f)

    with open("usercards.json", encoding="utf-8") as f:
        usercards = json.load(f)

    old_cards = {c["id"]: c for c in cards}

    seen = set()

    for usercard in usercards:
        old_card = old_cards.get(usercard["card_id"])

        if not old_card:
            continue
        
        if not old_card["shiny"]:
            new_card_id = old_to_new.get(usercard["card_id"])
        else:
            new_card_id = shiny_to_base.get(usercard["card_id"])

        if new_card_id is None:
            continue

        key = (usercard["user_id"], new_card_id)

        if key in seen:
            continue
        seen.add(key)

        existing = session.scalar(
            select(UserCards).where(
                UserCards.user_id == usercard["user_id"],
                UserCards.card_id == new_card_id
            )
        )

        if existing:
            if old_card.get("shiny", False):
                existing.shiny = True
            continue

        session.add(
            UserCards(
                id=usercard["id"],
                user_id=usercard["user_id"],
                card_id=new_card_id,
                shiny=old_card.get("shiny", False),
                level=1
            )
        )

    session.commit()

def drop_card_type_enum(engine):
    """Удаляет ENUM card_type_enum"""

    with engine.begin() as conn:
        try:
            conn.execute(
                text("DROP TYPE IF EXISTS card_type_enum CASCADE")
            )
            print("[DROP] card_type_enum")
        except Exception as e:
            print(f"[ERROR] DROP card_type_enum: {e}")


def create_banners(session):
    now = datetime.now()
    standard = Banner(name="Стандартный", active=True, started_at=now, ended_at=now+timedelta(weeks=30000))
    umazing = Banner(name="UMAZING БАННЕР", active=True,verse_id = 14, started_at=now, ended_at=now+timedelta(days=30))
    
    session.add(standard)
    session.add(umazing)
    session.commit()


def recreate_users(session):
    with open("users.json", encoding="utf-8") as f:
        users = json.load(f)

    with open("profiles.json", encoding="utf-8") as f:
        profiles = json.load(f)

    profiles_map = {
        profile["user_id"]: profile
        for profile in profiles
    }

    for user in users:
        profile = profiles_map.get(user["id"])

        if profile is None:
            continue

        session.add(
            User(
                id=user["id"],
                balance=user["balance"],
                username=user["username"],
                name=user["name"],
                last_open=datetime.fromisoformat(user["last_open"]),
                profile=Profile(
                    id=profile["id"],
                    title_id=profile.get("title_id"),
                    joined=profile["joined"],
                ),
            )
        )

    session.commit()

def recreate_clans(session):
    with open("clans.json", encoding="utf-8") as f:
        clans = json.load(f)

    with open("clan_members.json", encoding="utf-8") as f:
        clan_members = json.load(f)

    members_by_clan = {}

    for member in clan_members:
        members_by_clan.setdefault(member["clan_id"], []).append(member)

    for clan_data in clans:
        clan = Clan(
            id=clan_data["id"],
            name=clan_data["name"],
            tag=clan_data["tag"],
            description=clan_data.get("description", ""),
            created_at=datetime.fromisoformat(clan_data["created_at"]),
            leader_id=clan_data["leader_id"],
            balance=clan_data.get("balance", 0),
        )

        for member_data in members_by_clan.get(clan_data["id"], []):
            clan.members.append(
                ClanMember(
                    user_id=member_data["user_id"],
                    clan_id=member_data["clan_id"],
                    joined_at=datetime.fromisoformat(member_data["joined_at"]),
                    is_leader=member_data.get("is_leader", False),
                    contribution=member_data.get("contribution", 0),
                )
            )

        session.add(clan)

    session.commit()

def main(step: int):

    session = Session()

    match step:
        case 1:
            
            export_table(session, "cards", "cards.json")
            export_table(session, "usercards", "usercards.json")
            export_table(session, "rarities", "rarities.json")
            export_table(session, "verses", "verses.json")
            export_table(session, "clan_members", "clan_members.json")
            export_table(session, "clans", "clans.json")
            export_table(session, "referrals", "refferals.json")
            export_table(session, "vip_subscriptions", "vips.json")
            export_table(session, 'titles', 'titles.json')
            export_table(session, 'users', 'users.json')
            export_table(session, 'profiles', 'profiles.json')

            session.close()

            print("\n[DONE] Экспорт завершён")

            drop_tables(engine)

            print("\n[DONE] Таблицы удалены")
            drop_card_type_enum(engine)

        case 2:
            recreate_tables(engine)
            recreate_verses(session)
            recreate_rarities(session)
            recreate_cards(session)
            recreate_titles(session)
            recreate_users(session)
            recreate_usercards(session)
            reset_all_sequences(engine)
            create_banners(session)

if __name__ == "__main__":
    main(2)