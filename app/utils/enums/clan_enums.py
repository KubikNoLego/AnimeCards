from enum import Enum


class ClanKick(str, Enum):
    NO_LEADER = "Ошибка"
    NO_PERMS = "Недостаточно прав"
    NO_TARGET = "Участник не найден"
    SELF_KICK = "Нельзя выгнать себя"
    WRONG_CLAN = "Игрок не в вашем клане"
    TARGET_LEADER = "Нельзя выгнать лидера"

class ClanActions(int, Enum):
    ACCEPT = 1
    DECLINE = 0

class ClanInviteResult(str, Enum):
    SUCCESS = "Приглашение отправлено"
    ACCEPTED = "Приглашение принято"
    DECLINED = "Приглашение отклонено"
    NOT_FOUND = "Приглашение не найдено"
    NOT_LEADER = "Вы не лидер клана"
    PRIVATE_CHAT = "Команда недоступна в ЛС"
    NO_REPLY = "Ответьте на сообщение игрока"
    USER_NOT_FOUND = "Пользователь не найден"
    USER_ALREADY_IN_CLAN = "Игрок уже в клане"
    INVITE_ALREADY_EXISTS = "Приглашение уже отправлено"
    SELF_INVITE = "Нельзя пригласить себя"

class CreateClanResult(str, Enum):
    SUCCESS = "Клан успешно создан"
    NOT_ENOUGH_YENS = "Недостаточно йен"
    INVALID_STATE = "Ошибка состояния"
    ALREADY_IN_CLAN = "Вы уже состоите в клане"