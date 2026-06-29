def plural(number: int, one: str, two: str, five: str) -> str:
    number = abs(number)

    if 11 <= number % 100 <= 14:
        return five

    last = number % 10

    if last == 1:
        return one
    elif 2 <= last <= 4:
        return two
    else:
        return five