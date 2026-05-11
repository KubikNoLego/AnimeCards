from app.database.models import Title


def format_buffs(title: Title) -> str:
    mapping = {
        'y': '💰 +{}% к йенам',
        'b': '🍀 +{}% к удаче Хроно',
        'f': '🎴 +{} бесплатное открытие/день',
        't': '⏳ -{} мин к кулдауну',
    }

    ordered = []
    for key in mapping:
        for value, target in title.buffs:
            if target == key:
                ordered.append(mapping[key].format(value))

    return '\n'.join(ordered)