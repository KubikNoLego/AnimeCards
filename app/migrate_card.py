#!/usr/bin/env python3

from datetime import datetime
import json

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker, Session

from .database.models import Card, UserCards, Verse, Rarity, Base, CardType

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
    """Удаление таблиц"""

    tables = ["usercards", "cards", "verses", "rarities", "trades", "battle_inventories"]

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


def export_table(session, model, output_file):

    print(f"[EXPORT] {model.__tablename__}")

    data = session.query(model).all()

    result = [model_to_dict(item) for item in data]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=4
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
        session.add(Rarity(name=rarity['name']))
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

def recreate_cards(session):
    with open("cards.json", encoding="utf-8") as f:
        cards = json.load(f)

    base_cards = {}

    for card in cards:
        if card["shiny"]:
            continue

        verse = session.scalar(select(Verse).where(Verse.name == card['verse_name']))
        rarity = session.scalar(select(Rarity).where(Rarity.name == card['rarity_name']))

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
        rarity = session.scalar(select(Rarity).where(Rarity.name == card['rarity_name']))

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

def main(step: int):

    session = Session()
    match step:
        case 1:
            exports = [
                (Card, "cards.json"),
                (UserCards, "usercards.json"),
                (Verse, "verses.json"),
                (Rarity, "rarities.json"),
            ]

            for model, filename in exports:
                export_table(session, model, filename)

            session.close()

            print("\n[DONE] Экспорт завершён")

            drop_tables(engine)

            print("\n[DONE] Таблицы удалены")

        case 2:
            #recreate_tables(engine)
            #recreate_verses(session)
            #recreate_rarities(session)
            #recreate_cards(session)
            #recreate_usercards(session)
            reset_all_sequences(engine)


if __name__ == "__main__":
    main(2)