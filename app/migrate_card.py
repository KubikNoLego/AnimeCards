#!/usr/bin/env python3

from datetime import datetime
import json

from sqlalchemy import create_engine, select, text
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

def recreate_cards(session):
    with open("cards.json", encoding="utf-8") as f:
        cards = json.load(f)

    base_cards = {}

    for card in cards:
        if card["shiny"]:
            continue

        verse = session.scalar(select(Verse).where(Verse.name == card['verse_name']))
        rarity = session.scalar(select(Rarity).where(Rarity.name == card['rarity_name']))

        new_card = Card(name=card['name'], value=card['value'],
            card_type=CardType.STANDARD,verse_id=verse.id,rarity_id=rarity.id,
            icon=card['icon'],has_shiny=False,droppable=card['can_drop'])
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
        base_card.shiny_icon = card["icon"]

        shiny_to_base[card['id']] = base_card.id


    session.commit()

def recreate_usercards(session):
    with open("cards.json", encoding="utf-8") as f:
        cards = json.load(f)

    with open("usercards.json", encoding="utf-8") as f:
        usercards = json.load(f)

    for usercard in usercards:
        old_cards = {c["id"]: c for c in cards}
        old_card = old_cards[usercard['card_id']]
        if not old_card['shiny']:
            new_card_id = old_to_new[usercard['card_id']]
        else:
            new_card_id = shiny_to_base[usercard['card_id']]


        session.add(UserCards(id=usercard['id'],user_id=usercard["user_id"],card_id=new_card_id, shiny=old_card.get('shiny',False),level=1))
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
            recreate_tables(engine)
            recreate_verses(session)
            #recreate_rarities(session)
            recreate_cards(session)
            #recreate_usercards(session)


if __name__ == "__main__":
    main(2)