from enum import Enum

class InviteEnum(Enum):
    NOT_USER = "not_user_id"
    CANT_BE_REFERRAL = "u_cant_be_referral"
    ONLY_NEW_USERS = "only_new_users"
    SUCCESS = 'success'
    SORRY = "sorry"