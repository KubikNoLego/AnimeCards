from html import escape

from app.database.models import User


async def top_players_by_balance_formatter(top:list[User] ,user_id:int) -> str:
    if not top:
        return "<i>🏆 Топ игроков пока пуст.</i>"
            
    players_text = []

    for i, player in enumerate(top, 1):
        place_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        highlight = "<b><i>" if player.id == user_id else ""
        end_highlight = "</i></b>" if player.id == user_id else ""

        # Создаем кликабельную ссылку на профиль пользователя
        if player.username:
            player_link = f'<a href="t.me/{player.username}">{escape(player.name)}</a>'
        else:
            player_link = escape(player.name)
                
        player_value = getattr(player, "balance", 0)
        player_info = f"{place_emoji} {highlight}{player_link} — {player_value} ¥{end_highlight}"
        players_text.append(player_info)

    return "🏆 Топ игроков по балансу\n"+"\n".join(players_text)

async def top_players_by_wins_formatter(top: list[User], user_id:int) -> str:
    if not top:
        return "<i>⚔️ Топ игроков пока пуст.</i>"
            
    players_text = []

    for i, player in enumerate(top, 1):
        place_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        highlight = "<b><i>" if player.id == user_id else ""
        end_highlight = "</i></b>" if player.id == user_id else ""

        # Создаем кликабельную ссылку на профиль пользователя
        if player.username:
            player_link = f'<a href="t.me/{player.username}">{escape(player.name)}</a>'
        else:
            player_link = escape(player.name)
                
        player_value = getattr(player, "pvp_wins", 0)
        wins = "победа" if player_value == 1 else "победы" if player_value in [2,3] else "побед"
        player_info = f"{place_emoji} {highlight}{player_link} — {player_value} {wins}{end_highlight}"
        players_text.append(player_info)

    return "⚔️ Топ игроков по победам в PvP\n"+"\n".join(players_text)