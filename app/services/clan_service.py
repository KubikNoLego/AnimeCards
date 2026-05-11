from app.database.requests import DB


async def get_member_page(db: DB, page: int, user_id: int):
    user = await db.user.get_user(user_id)

    if not user:
        return None
    
    clan = await db.clan.get_clan(user.clan_member.clan_id)

    members = [m for m in clan.members if m.user_id != user_id]

    if not members: return {'empty': True}

    return {'empty': False,
            'member': members[page-1],
            'total': len(members),
            'is_leader': user.clan_member.is_leader
            }