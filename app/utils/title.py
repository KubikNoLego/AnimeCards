from app.database.models import Title


def format_buffs(title: Title) -> str:
    mapping = {
        'yen_boost': '💰 +{}% к йенам',
        'luck_boost': '🍀 +{}% к удаче Хроно',
        'free_open': '🎴 +{} бесплатное открытие/день',
        'time_skip': '⏳ -{} мин к кулдауну',
    }

    ordered = []
    for buff_key, buff_value in title.buffs.items():
        if buff_key in mapping:
            ordered.append(mapping[buff_key].format(buff_value))

    return '\n'.join(ordered)
