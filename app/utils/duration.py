from datetime import timedelta


def format_duration(delta: timedelta) -> str:
    total_seconds = max(0, int(delta.total_seconds()))

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []

    if hours:
        parts.append(f"{hours} ч")
    if minutes:
        parts.append(f"{minutes} мин")
    if not hours and not minutes:
        parts.append(f"{seconds} сек")

    return " ".join(parts)