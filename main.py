#########################################
#Импорт библиотек
import datetime
import json
import random
import sqlite3
import time
import telebot

from Cards import *
from telebot import types
from CAC import *
from Config import Bot_Token as token
##########################################
#Настройка бота
bot = telebot.TeleBot(token)
#Обработка команд

@bot.message_handler(commands=['notic'])
def notic(message):
    if message.from_user.id == 5027089008:
        # Подключение к базе данных
        db = sqlite3.connect("db.db")
        cursor = db.cursor()
        # Запись игрока
        l = 0
        cursor.execute(f"SELECT user_id FROM users")
        for id in cursor.fetchall():
            try:
                bot.send_message(id[0],message.text[7:], parse_mode="HTML", disable_web_page_preview=True)
            except:
                l+=1
        print(l)
        db.close()
@bot.message_handler(commands=['stat'])
def notic(message):
    if message.from_user.id == 5027089008:
    # Подключение к базе данных
        db = sqlite3.connect("db.db")
        cursor = db.cursor()
        # Запись игрока
        s = cursor.execute(f"SELECT id FROM users").fetchall()
        bot.send_message(message.chat.id,f"Всего зарегестрировано - {len(s)}", parse_mode="HTML", disable_web_page_preview=True)
        db.close()
@bot.message_handler(commands=['notict'])
def notic(message):
    if message.from_user.id == 5027089008:
        # Подключение к базе данных
        db = sqlite3.connect("db.db")
        cursor = db.cursor()
        # Запись игрока
        cursor.execute(f"SELECT user_id FROM users")
        bot.send_message(message.chat.id,message.text[8:], parse_mode="HTML",disable_web_page_preview=True)
        db.close()
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type == 'private':
        page = 1
        #Подключение к базе данных
        db = sqlite3.connect("db.db")
        cursor = db.cursor()
        #Запись игрока
        cursor.execute(f"SELECT user_id FROM users WHERE user_id = {message.from_user.id}")
        if cursor.fetchone() == None:
            cursor.execute(f"INSERT INTO users(user_id,username) VALUES({message.from_user.id},'{bot.get_chat_member(message.from_user.id,message.from_user.id).user.username}') ;")
            db.commit()
        #Кнопки бота
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("🃏 | Получить карту")
        btn2 = types.KeyboardButton("📓 | Статистика")
        btn3 = types.KeyboardButton("😎 | Топ игроки")
#        btn4 = types.KeyboardButton("👥 | Клан")
        btn5 = types.KeyboardButton("🛒 | Ежедневный магазин")
        markup.add(btn1,btn2,btn3,btn5)
        #Отправка сообщения
        bot.send_message(message.chat.id,
                         text='<b>✌️Добро пожаловать в AnimeCards.</b>\n\n📝 Для начала нажмите на <b>"🃏 | Получить карту"</b>.\n\n📡 Если вы захотите посмотреть свои карты можете нажать на <b>"📓 | Колода"</b>.\n\n🔎 Также вы можете попытаться стать лучшим игроком <b>"😎 | Топ игроки"</b>.\n\n  <b><a href = "https://t.me/anicrd">Чат</a> | <a href = "https://t.me/anicrds">Новости</a></b>'.format(message.from_user), reply_markup=markup, parse_mode="HTML")
        db.close()

@bot.message_handler(content_types='text')
def message(message):
    db = sqlite3.connect("db.db")
    cursor = db.cursor()
    if message.text == "🃏 | Получить карту" and message.is_from_offline != True or message.text.lower()[:9] == "/get_card" and message.is_from_offline != True:
        cursor.execute(f"SELECT user_id FROM users WHERE user_id = {message.from_user.id}")
        if cursor.fetchone() == None:
            bot.reply_to(message,
                         f'❗ | <b><a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a></b>, твоя коллекция ждёт тебя! Нажми <a href="tg://user?id=7808827072">/start</a> в боте!',
                         parse_mode='HTML')
        else:
           # Последнее получение карты
           last_use = cursor.execute(f"SELECT card_await FROM users WHERE user_id = {message.from_user.id}").fetchone()[0]
           # Проверка на возможность получение карты
           data = datetime.date.today()
           date = data.weekday()
           if date >= 5:
               time = 1
           else:
               time = 2
           if str(datetime.datetime.now() - datetime.timedelta(hours=time)) > last_use:
              m = (datetime.datetime.now() + datetime.timedelta(seconds=random.randint(1,60))).strftime("%Y-%m-%d %H:%M:%S.%f")
              cursor.execute(f'UPDATE users SET card_await = "{m}" WHERE user_id = {message.from_user.id};')

              db.commit()
              # Редкость карты
              x = random.randint(1,100)
              # Статистика игрока
              clan = cursor.execute(f"SELECT clan FROM users WHERE user_id = {message.from_user.id}").fetchone()[0]
              kol = cursor.execute(f"SELECT cards_amount, rare, epic, mythic,legend,chrono, card_hand,lucky FROM users WHERE user_id = {message.from_user.id}").fetchone()
              # Получение карты
              if x < 1001:
                  t = None
                  y = None
                  r = None
                  # t - редкость карты
                  # y - карта
                  if kol[7] == 0:
                    if x in rare:
                        r = "rare"
                        t = kol[1]
                        y = random.choice(rare_cards)
                    if x in epic:
                        r = "epic"
                        t = kol[2]
                        y = random.choice(epic_cards)
                    if x in mythic:
                        r = "mythic"
                        t = kol[3]
                        y = random.choice(mythic_cards)
                    if x in legend:
                        r = "legend"
                        t = kol[4]
                        y = random.choice(legend_cards)
                    if x == 1000:
                        r = "chrono"
                        t = kol[5]
                        y = random.choice(chrono_cards)
                  else:
                      if x in rare:
                          r = "epic"
                          t = kol[2]
                          y = random.choice(epic_cards)
                      if x in epic:
                          r = "mythic"
                          t = kol[3]
                          y = random.choice(mythic_cards)
                      if x in mythic:
                          r = "legend"
                          t = kol[4]
                          y = random.choice(legend_cards)
                      if x in legend:
                          r = "chrono"
                          t = kol[5]
                          y = random.choice(chrono_cards)
                      if x == 1000:
                          r = "chrono"
                          t = kol[5]
                          y = random.choice(chrono_cards)
                  # Отправка сообщения
                  try:
                      photo = open(y["path"], 'rb')
                      bot.send_photo(message.chat.id, photo,
                                     caption=f"🥳 | Поздравляем, <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>! Вам выпал <b>{y['title']}</b>!\n\n💍Редкость: {y['rarity']},\n🎖Оценка: {y['score']},\n🌍Вселенная: {y['verse']}\n\n⏱ | Следующая попытка через {time}ч!",parse_mode='HTML')
                      # Добавление карты и времени в бд
                      if clan != "None":
                          score = cursor.execute(f"SELECT score FROM clans WHERE clan = '{clan}'").fetchone()[0]
                          cursor.execute(f'UPDATE clans SET score = {int(score) + int(y["score"])} WHERE clan = "{clan}"')
                          db.commit()
                      card_hand_list = ((kol[6]).split(" "))
                      if str(y["name"]) in card_hand_list:
                          cursor.execute(f'UPDATE users SET cards_amount = "{int(int(kol[0]) + int(y["score"]))}",{r} = {int(int(t) + 1)}, card_hand = "{kol[6]}" WHERE user_id = {message.from_user.id};')
                          db.commit()
                          db.close()
                      else:
                          cursor.execute(f'UPDATE users SET cards_amount = "{int(int(kol[0]) + int(y["score"]))}",{r} = {int(int(t) + 1)}, card_hand = "{kol[6]} {str(y["name"])}", lucky=0 WHERE user_id = {message.from_user.id};')
                          db.commit()
                          db.close()
                  except Exception as s:
                      m = 0
                      cursor.execute(f'UPDATE users SET card_await = "{m}" WHERE user_id = {message.from_user.id};')
                      db.commit()
                      db.close()
           # Не достаточно прожданого времени
           else:
               date_to = (datetime.datetime.strptime(last_use, "%Y-%m-%d %H:%M:%S.%f") + datetime.timedelta(hours=time))
               bot.send_message(message.chat.id,f"⏰ | Следующая попытка будет доступна только в <b>{str(datetime.datetime.strftime(date_to, '%H часов %M минут'))} по МСК</b>!",parse_mode="HTML")

    if message.text == "📓 | Статистика" or message.text.lower()[:10] == "/myprofile":
        #Статистика игрока
        kol = cursor.execute(f"SELECT cards_amount, rare, epic, mythic,legend,chrono FROM users WHERE user_id = {message.from_user.id}").fetchone()
        clan = cursor.execute(f"SELECT clan FROM users WHERE user_id = {message.from_user.id}").fetchone()[0]
        #Список случайных цитат
        randomcit = ["«Мама учила не ругаться матом, но жизнь научила не ругаться матом при маме» - Павел Дуров",
                     "«Я всегда говорю себе что нужно перестать пить, но я не слушаю советы от алкоголиков» - Трудовик",
                     "«Девушки, как кубки в бравл старс, то приходят то уходят» - ZabWarudo",
                     "«Есть вещи, которые лучше не знать. И, судя по всему, большинство считает, что это грамматика и пунктуация» - Автор неизвестен",
                     "«Я никогда не видел, что бы кто-то стройный пил диетическую колу» - Дональд Трамп",
                     "«Лучше бы порнуха приснилась» - Дмитрий Менделеев",
                     "«Если жизнь это вызов, то я перезвоню» - Джейсон Стетхем",
                     "«Не ругайте ленивых, они ничего не сделали»- Жак Фреско",
                     "«Лучше конец света, чем конец у светы» - Неопознанный Летающий Мужик",
                     "«Рабы системы пьют по пятницам, свободные личности не обращают внимание на такие мелочи, как дни недели» - Sun Xui Vchai",
                     "«Розы вянут на газоне, пацаны в французской зоне» - Павел Дуров"]
        markap = types.InlineKeyboardMarkup(row_width=1)
        item = types.InlineKeyboardButton('Посмотреть свои карты', callback_data='show')
        item2 = types.InlineKeyboardButton('Все карты', callback_data='show3')
        markap.add(item,item2)
        #Отправка сообщения
        if clan == "None":
            clan = "Отсутствует"
        if message.chat.type == 'private':
           bot.send_message(message.chat.id, f"🃏 | Количество ваших очков: {kol[0]}\n\n🔵 | Выпало обычных карт: {kol[1]},\n🟣 | Выпало эпических карт: {kol[2]},\n🔴 | Выпало мифических карт: {kol[3]},\n🟡 | Выпало легендарных карт: {kol[4]},\n🌈 | Количество выпадений хроно карт: {kol[5]}\n\n💘 | <b>{random.choice(randomcit)}</b>", parse_mode='HTML', reply_markup=markap)
        else:
            bot.reply_to(message,f"🃏 | Количество ваших очков: {kol[0]}\n\n🔵 | Выпало обычных карт: {kol[1]},\n🟣 | Выпало эпических карт: {kol[2]},\n🔴 | Выпало мифических карт: {kol[3]},\n🟡 | Выпало легендарных карт: {kol[4]},\n🌈 | Количество выпадений хроно карт: {kol[5]}\n\n💘 | <b>{random.choice(randomcit)}</b>",parse_mode='HTML')
        db.close()
#🏹 | Клан: {clan}\n
    if message.text == "😎 | Топ игроки" or message.text.lower()[:8] == "/get_top":
        y = cursor.execute(f"SELECT user_id, cards_amount FROM users ORDER BY cards_amount DESC LIMIT 30").fetchall()
        smile = ["😎", "✨", "❤", "🌈", "🏹", "😍", "💘", "💖", "🤗", "🎉", "😊", "🌹", "🎈", "🎨","🎂","🥳", "😃", "👏","🎁"]
        text = ""
        num = 1
        for x in y:
            text += f'<b>{num}</b>. <a href="tg://openmessage?user_id={x[0]}">{bot.get_chat_member(x[0], x[0]).user.first_name}</a> - <b>{x[1]} очков</b> {random.choice(smile)}\n'
            num += 1
        bot.reply_to(message, text=f'{text}\n<b>Очки сбрасываются каждые 2 месяца. Следуйщий сброс 29 марта</b>',parse_mode='HTML')

    if message.text.lower() == "!трейд" and message.reply_to_message:
        trade_with = cursor.execute(f"SELECT trade_with FROM users WHERE user_id = {message.from_user.id}").fetchone()[0]
        trade_with2 = cursor.execute(f"SELECT trade_with FROM users WHERE user_id = {message.reply_to_message.from_user.id}").fetchone()[0]
        if message.reply_to_message.from_user.id != message.from_user.id:
            if trade_with == "None":
                if trade_with2 == "None":
                    cursor.execute(f"UPDATE users SET trade_with = {message.reply_to_message.from_user.id} WHERE user_id = {message.from_user.id}")
                    cursor.execute(f"UPDATE users SET trade_with = {message.from_user.id} WHERE user_id = {message.reply_to_message.from_user.id}")
                    db.commit()
                    bot.reply_to(message,f"💬 | Мы выслали вам список карт в лс! Выберете одну из них для продолжения трейда.",parse_mode="HTML")
                    markap = types.InlineKeyboardMarkup(row_width=1)
                    item = types.InlineKeyboardButton('Показать все карты', callback_data='show2')
                    markap.add(item)
                    bot.send_message(message.from_user.id, f"🏹 | Выберете карту для совершения трейда!", parse_mode='HTML',reply_markup=markap)
                else:
                    bot.reply_to(message, f"❗ | Игрок уже ведёт трейд с другим человеком!", parse_mode="HTML")
            else:
                bot.reply_to(message, f"❗ | Вы уже ведёте трейд с другим человеком!", parse_mode="HTML")
        else:
            bot.reply_to(message, f"😡 | Вы не можете трейдится с самим собой")

    if message.text.lower() == "!трейд отмена":

       cl = cursor.execute(f"SELECT trade_with FROM users WHERE user_id = {message.from_user.id}").fetchone()[0]

       if cl != "None":
           bot.reply_to(message, f"💬 | Трейд отменён")
           cursor.execute(f"UPDATE users SET trade_with = 'None' WHERE user_id = {message.from_user.id}")
           cursor.execute(f"UPDATE users SET trade_with = 'None' WHERE trade_with = {message.from_user.id}")
           db.commit()
           db.close()
       else:
           bot.reply_to(message, f"❗ | У вас нет активного трейда")

    if message.text == "🛒 | Ежедневный магазин":
        if message.chat.type == 'private':
            tovar = cursor.execute(f"SELECT luckyt,ruletka,second_chance FROM users WHERE user_id = {message.from_user.id}").fetchone()
            markup = types.InlineKeyboardMarkup(row_width=1)
            if str(datetime.datetime.now() - datetime.timedelta(hours=24)) > tovar[2]:
                tv1 = types.InlineKeyboardButton('👼 Второй шанс',callback_data="{\"method\":\"shop\",\"Tv\":\"secondchance\"}")

            else:
                tv1=types.InlineKeyboardButton(f'{datetime.datetime.strftime((datetime.datetime.strptime(tovar[2], "%Y-%m-%d %H:%M:%S.%f")+datetime.timedelta(hours=24)),"%H:%M:%S")}',callback_data="pass")
            if str(datetime.datetime.now() - datetime.timedelta(hours=24)) > tovar[1]:
                tv2 = types.InlineKeyboardButton('🎱 Рулетка',callback_data="{\"method\":\"shop\",\"Tv\":\"ruletka\"}")
            else:
                tv2=types.InlineKeyboardButton(f'{datetime.datetime.strftime((datetime.datetime.strptime(tovar[1], "%Y-%m-%d %H:%M:%S.%f")+datetime.timedelta(hours=24)),"%H:%M:%S")}',callback_data="pass")
            if str(datetime.datetime.now() - datetime.timedelta(hours=24)) > tovar[0]:
                tv3 = types.InlineKeyboardButton('🍀 Удача', callback_data="{\"method\":\"shop\",\"Tv\":\"lucky\"}")
            else:
                tv3=types.InlineKeyboardButton(f'{datetime.datetime.strftime((datetime.datetime.strptime(tovar[0], "%Y-%m-%d %H:%M:%S.%f")+datetime.timedelta(hours=24)),"%H:%M:%S")}',callback_data="pass")
            markup.add(tv1,tv2,tv3)
            bot.send_message(message.chat.id,"<b>Привет!</b> Добро пожаловать в магазин 🏪 Товар можно купить <b>один раз в день</b>. В качестве валюты используются очки, получаемые с открытых карт.\n\n👼 Второй шанс - даёт возможность открыть карту без ожидания.\n<b>💸 Стоимость: 30 очков</b>\n\n🎱 Рулетка - после покупки вы получаете от 1 до 30 очков.\n<b>💸 Стоимость: 15 очков</b>\n\n🍀 Удача - меняет вероятности выпадения редкостей карт, но работает <b>1 раз</b> после покупки.\n<b>💸 Стоимость: 45 очков</b>\n\n<b>Доступные товары:</b>",parse_mode="HTML",reply_markup=markup)
            db.close()
#    if message.text.lower()[:5] == "+клан":
#        clan = cursor.execute(f"SELECT clan FROM users WHERE user_id = {message.from_user.id}").fetchone()[0]
#        card = cursor.execute(f"SELECT cards_amount FROM users WHERE user_id = {message.from_user.id}").fetchone()[0]
#        if (message.text.lower()[6:]).replace(" ", "") != "":
#            if clan != "None":
#                bot.reply_to(message, f'💬 | Вы уже состоите в клане - <b>{clan}</b>', parse_mode="HTML")
#            else:
#                if card < 100:
#                    bot.reply_to(message,
#                                 f'❗ | <a href = "tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>, для создания клана требуется 100 очков, которые будут сняты после создания клана',
#                                 parse_mode="HTML")
#                else:
#                    if len(message.text[6:].replace(" ", "")) > 15 or len(
#                            message.text[6:].replace(" ", "")) < 3:
#                        bot.reply_to(message,
#                                     f"❗ | Название клана не должно превышать 15 символов и быть меньше 3 символов, а также не содержать пробелов")
#                    else:
#                        clan_check = True
#                        try:
#                            clan_name = cursor.execute(f"SELECT clan FROM clans WHERE clan = '{message.text[6:].replace(" ", "")}'").fetchone()[0]
#                            clan_check = False
#                        except:
#                            clan_check = True
#                        if clan_check:
#                           bot.reply_to(message,
#                                        f"🎂 | <b>Клан успешно создан! Чтобы добавить участников, напишите ответ на сообщение пользователя, которого хотите добавить с тесктом \"+приглашение\".</b>",
#                                        parse_mode="HTML")
#                           cursor.execute(f"UPDATE users SET clan = '{message.text[6:].replace(" ", "")}' WHERE user_id = {message.from_user.id}")
#                           cursor.execute(f"UPDATE users SET cards_amount = '{card - 100}' WHERE user_id = {message.from_user.id}")
#                           cursor.execute(f"INSERT INTO clans (clan,owner,score,members) VALUES ('{message.text[6:].replace(" ", "")}',{message.from_user.id},{card - 100},{message.from_user.id})")
#                           db.commit()
#                           db.close()
#                        else:
#                           bot.reply_to(message, f"❗ | Клан с таким именем уже существует, пожалуйста, выберите другое.")
#        else:
#            bot.reply_to(message, "❗ | После <b>+клан</b> идёт название клана. Напишите его, пожалуйста.",
#                         parse_mode="HTML")
#
#    if message.text == "-клан":
#        clan = cursor.execute(f"SELECT clan FROM users WHERE user_id = {message.from_user.id}").fetchone()[0]
#        clan_info = cursor.execute(f"SELECT members FROM clans WHERE clan = '{clan}'").fetchone()[0]
#        clan_info = str(clan_info).split(" ")
#        clan_score = cursor.execute(f"SELECT score FROM clans WHERE clan = '{clan}'").fetchone()[0]
#        card = cursor.execute(f"SELECT cards_amount FROM users WHERE user_id = {message.from_user.id}").fetchone()[0]
#        if clan[0] != "None":
#            clan_info.remove(str(message.from_user.id))
#            separator = ' '
#            clan_info = separator.join(clan_info)
#            amount = int(clan_score) - int(card)
#            bot.reply_to(message, f"🎈 | <b>Вы успешно покинули клан</b>", parse_mode="HTML")
#            if clan_info:
#                cursor.execute(f"UPDATE users SET clan = 'None' WHERE user_id={message.from_user.id}")
#                cursor.execute(
#                    f"UPDATE clans SET members = '{clan_info}', score = '{amount}' WHERE clan = '{clan}'")
#                db.commit()
#            else:
#                cursor.execute(f"DELETE FROM clans WHERE clan = '{clan}';")
#                cursor.execute(f"UPDATE users SET clan = 'None' WHERE user_id={message.from_user.id}")
#                db.commit()
#            db.close()
#
#    if message.text.lower() == "+приглашение" and message.reply_to_message:
#        if message.chat.type != "private":
#            clan2 = message.reply_to_message.from_user.id
#            clan = cursor.execute(f"SELECT clan FROM users WHERE user_id = {message.from_user.id}").fetchone()[0]
#            clan_to = cursor.execute(f"SELECT clan FROM users WHERE user_id = {clan2}").fetchone()[0]
#            if clan == "None":
#                bot.reply_to(message, f'💬 | Вы не состоите в клане. Вы не можете пригласить человека!',
#                             parse_mode="HTML")
#            else:
#                if clan_to != "None":
#                    bot.reply_to(message,f'💬 | <a href = "tg://user?id={clan2}">{message.reply_to_message.from_user.first_name}</a> уже состоит в клане - <b>{clan_to}</b>',parse_mode="HTML")
#                else:
#                    markap = types.InlineKeyboardMarkup(row_width=2)
#                    item = types.InlineKeyboardButton('Да', callback_data="{\"m\":\"ar\",\"Userid\":" + str(message.from_user.id) + ",\"UserTo\":" + str(clan2) + "}")
#                    item2 = types.InlineKeyboardButton('Нет',callback_data="{\"m\":\"dr\",\"Userid\":" + str(message.from_user.id) + ",\"UserTo\":" + str(clan2) + "}")
#                    markap.add(item, item2)
#                    bot.reply_to(message,f"🎈 | <b>Вы уверены что хотите пригласить <a href = 'tg://user?id={clan2}'>{message.reply_to_message.from_user.first_name}</a> в клан?</b>",reply_markup=markap,parse_mode="HTML")
#                    db.commit()
#                    db.close()
#
#    if message.text == "👥 | Клан" or message.text.lower()[:5] == "/clan":
#        clan = cursor.execute(f"SELECT clan FROM users WHERE user_id = {message.from_user.id}").fetchone()[0]
#        if str(clan) == "None":
#            bot.send_message(message.chat.id,
#                             f'Привет, <a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>!\n<b>Сейчас у тебя нет клана, но ты можешь создать его</b>, если у тебя есть 100 очков. Напиши <b>"+клан (название клана)"</b> для его создания и помни что изменить имя клана будет невозможно!\n\nЧтобы покинуть клан напиши <b>"-клан"</b>.',
#                             parse_mode="HTML")
#        else:
#            members = cursor.execute(f"SELECT members,score,clan,owner FROM clans WHERE clan = '{clan}'").fetchone()
#            users = str(members[0]).split(" ")
#            text = ""
#            num = 1
#            for user in users:
#                if str(user) == str(members[3]):
#                    text += f'<b>{num}</b>. <a href="tg://openmessage?user_id={user}">{bot.get_chat_member(user, user).user.first_name}</a> - <b>Создатель</b>\n'
#                else:
#                    text += f'<b>{num}</b>. <a href="tg://openmessage?user_id={user}">{bot.get_chat_member(user, user).user.first_name}</a>\n'
#                num += 1
#            markup = types.InlineKeyboardMarkup(types.InlineKeyboardButton('>',callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(page + 1) + ",\"CountPage\":" + str(count) + "}"))
#            bot.send_message(message.chat.id,f'💬 Клан: <b>{clan}</b>\n🔟 Общее кол-во очков: <b>{members[1]}</b>\n\n👥 Участники:\n{text}', parse_mode = "HTML",markup=markap)
#    if message.text.lower()[:14] == "/get_clans_top":
#        y = cursor.execute(f"SELECT score,clan FROM clans ORDER BY score DESC LIMIT 10").fetchall()
#        smile = ["😎", "✨", "❤", "🌈", "🏹", "😍", "💘", "💖", "🤗", "🎉", "😊", "🌹", "🎈", "🎨","🎂","🥳", "😃", "👏","🎁"]
#        text = ""
#        num = 1
#        for x in y:
#            text += f'<b>{num}</b>. <b>{x[1]}</b> - <b>{x[0]} очков</b> {random.choice(smile)}\n'
#            num += 1
#        bot.reply_to(message, text=f'{text}\n<b>Очки кланов сбрасываются каждые 2 месяца. Следуйщий сброс 29 марта</b>',parse_mode='HTML')


@bot.callback_query_handler(func = lambda call:True)
def callback(call):
    db = sqlite3.connect("db.db")
    cursor = db.cursor()
    card_hand = cursor.execute(f"SELECT card_hand FROM users WHERE user_id ={call.from_user.id}").fetchone()
    card_hand_list = card_hand[0].split(" ")
    del card_hand_list[0]
    count = len(card_hand_list)
    if call.message:
        if 'shop' in call.data:
            json_string = json.loads((call.data.split("_"))[0])
            tovar = json_string['Tv']
            bot.delete_message(call.message.chat.id, call.message.id)
            score = cursor.execute(f"SELECT cards_amount FROM users WHERE user_id={call.from_user.id}").fetchone()[0]
            if tovar == "secondchance":
                if int(score) >= 30:
                    cursor.execute(f"UPDATE users SET second_chance = '{datetime.datetime.now()}', card_await='0', cards_amount={int(score)-30} WHERE user_id={call.from_user.id}")
                    bot.send_message(call.from_user.id, f"Вы успешно купили \"👼 Второй шанс\". Откройте карту!")
                    db.commit()
                    db.close()
                else:
                    bot.send_message(call.from_user.id,f"Вам не хватило очков для покупки")
            if tovar == "ruletka":
                if int(score) >=15:
                    add = random.randint(1,30)
                    cursor.execute(f"UPDATE users SET ruletka = '{datetime.datetime.now()}', cards_amount={(int(score)-15)+add} WHERE user_id={call.from_user.id}")
                    bot.send_message(call.from_user.id,f"Вы купили \"🎱 Рулетка\". Вам добавлено - {add} очков")
                    db.commit()
                    db.close()
                else:
                    bot.send_message(call.from_user.id,f"Вам не хватило очков для покупки")
            if tovar == "lucky":
                if int(score) >=45:
                    cursor.execute(f"UPDATE users SET luckyt = '{datetime.datetime.now()}', lucky=1, cards_amount={int(score)-45} WHERE user_id={call.from_user.id}")
                    bot.send_message(call.from_user.id,f"Вы купили \"🍀 Удача\". При следуйщем открытие вам повезёт!")
                    db.commit()
                    db.close()
                else:
                    bot.send_message(call.from_user.id,f"Вам не хватило очков для покупки")
        if 'pagination' in call.data:
            json_string = json.loads((call.data.split("_"))[0])
            page = json_string['NumberPage']
            method = json_string['method']
            markup = types.InlineKeyboardMarkup()
            if method == "pagination":
                if page <= 0:
                    page = 1
                    item2 = types.InlineKeyboardButton('>',
                                                       callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(
                                                           page + 1) + ",\"CountPage\":" + str(count) + "}")
                    l = f"{page}/{count}"
                    item3 = types.InlineKeyboardButton(text=l, callback_data="pass")

                    markup.add(item3, item2)
                if page > count:
                    page = count
                    item1 = types.InlineKeyboardButton('<',
                                                       callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(
                                                           page - 1) + ",\"CountPage\":" + str(count) + "}")
                    l = f"{page}/{count}"
                    item3 = types.InlineKeyboardButton(text=l, callback_data="pass")
                    markup.add(item1, item3)
                elif page == 1:
                    item2 = types.InlineKeyboardButton('>',
                                                       callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(
                                                           page + 1) + ",\"CountPage\":" + str(count) + "}")
                    l = f"{page}/{count}"
                    item3 = types.InlineKeyboardButton(text=l, callback_data="pass")
                    markup.add(item3, item2)
                elif page == count:
                    item1 = types.InlineKeyboardButton('<',
                                                       callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(
                                                           page - 1) + ",\"CountPage\":" + str(count) + "}")
                    l = f"{page}/{count}"
                    item3 = types.InlineKeyboardButton(text=l, callback_data="pass")
                    markup.add(item1, item3)
                else:
                    item1 = types.InlineKeyboardButton('<',
                                                       callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(
                                                           page - 1) + ",\"CountPage\":" + str(count) + "}")
                    item2 = types.InlineKeyboardButton('>',
                                                       callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(
                                                           page + 1) + ",\"CountPage\":" + str(count) + "}")
                    l = f"{page}/{count}"
                    item3 = types.InlineKeyboardButton(text=l, callback_data="pass")
                    item7 = types.InlineKeyboardButton("<<<",
                                                       callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(
                                                           page - 100) + ",\"CountPage\":" + str(count) + "}")
                    item6 = types.InlineKeyboardButton("<<",
                                                       callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(
                                                           page - 10) + ",\"CountPage\":" + str(count) + "}")
                    item5 = types.InlineKeyboardButton('>>>',
                                                       callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(
                                                           page + 100) + ",\"CountPage\":" + str(count) + "}")
                    item4 = types.InlineKeyboardButton('>>',
                                                       callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(
                                                           page + 10) + ",\"CountPage\":" + str(count) + "}")
                    spisok2 = ""
                    if (int(page) - 100) > 0:
                        spisok2 += "item7 "
                    elif (int(page) - 10) > 0:
                        spisok2 += "item6 "
                    elif (int(page) + 10) < int(count):
                        spisok2 += "item4 "
                    elif (int(page) + 100) < int(count):
                        spisok2 += "item5 "
                    elem = []
                    for el in spisok2.split(" "):
                        if el != '':
                            elem.append(eval(el))
                    markup.add(item1, item3, item2)
                    markup.add(*elem)
                try:
                    y = eval(card_hand_list[page-1].replace(" ", ""))
                    photo = types.InputMediaPhoto(open(y["path"], 'rb'))
                    bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.id, media=photo)
                    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.id,
                                             caption=f"<b>{y['title']}</b>\n\n💍Редкость: {y['rarity']},\n🎖Оценка: {y['score']},\n🌍Вселенная: {y['verse']}",parse_mode='HTML', reply_markup=markup)
                except:
                    pass
            if method == "paginationt":
                if page <= 0:
                    page = 1
                    item2 = types.InlineKeyboardButton('>',callback_data="{\"method\":\"paginationt\",\"NumberPage\":" + str(page + 1) + ",\"CountPage\":" + str(count) + "}")
                    l = "✅ | Выбрать карту"
                    item3 = types.InlineKeyboardButton(text=l,callback_data="{\"method\":\"complete\",\"NumberPage\":" + str(page) + "}")
                    markup.add(item3, item2)
                if page > count:
                    page = count
                    item1 = types.InlineKeyboardButton('<',callback_data="{\"method\":\"paginationt\",\"NumberPage\":" + str(page - 1) + ",\"CountPage\":" + str(count) + "}")
                    l = "✅ | Выбрать карту"
                    item3 = types.InlineKeyboardButton(text=l, callback_data="{\"method\":\"complete\",\"NumberPage\":" + str(page) + "}")
                    markup.add(item1, item3)
                elif page == 1:
                    item2 = types.InlineKeyboardButton('>',callback_data="{\"method\":\"paginationt\",\"NumberPage\":" + str(page + 1) + ",\"CountPage\":" + str(count) + "}")
                    l = "✅ | Выбрать карту"
                    item3 = types.InlineKeyboardButton(text=l,callback_data="{\"method\":\"complete\",\"NumberPage\":" + str(page) + "}")
                    markup.add(item3, item2)
                elif page == count:
                    item1 = types.InlineKeyboardButton('<',callback_data="{\"method\":\"paginationt\",\"NumberPage\":" + str(page - 1) + ",\"CountPage\":" + str(count) + "}")
                    l = "✅ | Выбрать карту"
                    item3 = types.InlineKeyboardButton(text=l,callback_data="{\"method\":\"complete\",\"NumberPage\":" + str(page) + "}")
                    markup.add(item1, item3)
                else:
                    item1 = types.InlineKeyboardButton('<',callback_data="{\"method\":\"paginationt\",\"NumberPage\":" + str(page - 1) + ",\"CountPage\":" + str(count) + "}")
                    item2 = types.InlineKeyboardButton('>',callback_data="{\"method\":\"paginationt\",\"NumberPage\":" + str(page + 1) + ",\"CountPage\":" + str(count) + "}")
                    l = "✅ | Выбрать карту"
                    item3 = types.InlineKeyboardButton(text=l,callback_data="{\"method\":\"complete\",\"NumberPage\":" + str(page) + "}")
                    markup.add(item1, item3, item2)
                try:
                    y = eval(card_hand_list[page - 1].replace(" ", ""))
                    photo = types.InputMediaPhoto(open(y["path"], 'rb'))
                    bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.id, media=photo)
                    bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.id,
                                             caption=f'<b>{y["title"]}</b>\n\n💍Редкость: {y["rarity"]},\n🎖Оценка: {y["score"]},\n🌍Вселенная: {y["verse"]}',
                                             parse_mode='HTML', reply_markup=markup)
                except:
                    pass
            if method == "paginationa":
                cards = rare_cards + epic_cards + mythic_cards + legend_cards + chrono_cards
                count = len(cards)
                markup = types.InlineKeyboardMarkup(row_width=7)
                if page <= 0:
                    page = 1
                    item2 = types.InlineKeyboardButton('>',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page + 1) + ",\"CountPage\":" + str(count) + "}")
                    l = f"{page}/{count}"
                    item3 = types.InlineKeyboardButton(text=l, callback_data="pass")
                    item4 = types.InlineKeyboardButton('>>',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page + 10) + ",\"CountPage\":" + str(count) + "}")
                    item5 = types.InlineKeyboardButton('>>>',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page + 100) + ",\"CountPage\":" + str(count) + "}")
                    markup.add(item3, item2, item4, item5)
                if page > count:
                    page = count
                    item1 = types.InlineKeyboardButton('<',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page - 1) + ",\"CountPage\":" + str(count) + "}")
                    l = f"{page}/{count}"
                    item3 = types.InlineKeyboardButton(text=l, callback_data="pass")
                    item4 = types.InlineKeyboardButton('<<',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page - 10) + ",\"CountPage\":" + str(count) + "}")
                    item5 = types.InlineKeyboardButton('<<<',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page - 100) + ",\"CountPage\":" + str(count) + "}")
                    markup.add(item5, item4, item1, item3)
                elif page == 1:
                    item2 = types.InlineKeyboardButton('>',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page + 1) + ",\"CountPage\":" + str(count) + "}")
                    l = f"{page}/{count}"
                    item3 = types.InlineKeyboardButton(text=l, callback_data="pass")
                    item4 = types.InlineKeyboardButton('>>',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page + 10) + ",\"CountPage\":" + str(count) + "}")
                    item5 = types.InlineKeyboardButton('>>>',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page + 100) + ",\"CountPage\":" + str(count) + "}")
                    markup.add(item3, item2, item4, item5)
                elif page == count:
                    item1 = types.InlineKeyboardButton('<',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page - 1) + ",\"CountPage\":" + str(count) + "}")
                    l = f"{page}/{count}"
                    item3 = types.InlineKeyboardButton(text=l, callback_data="pass")
                    item4 = types.InlineKeyboardButton('<<',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page - 10) + ",\"CountPage\":" + str(count) + "}")
                    item5 = types.InlineKeyboardButton('<<<',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page - 100) + ",\"CountPage\":" + str(count) + "}")
                    markup.add(item5, item4, item1, item3)
                else:
                    item1 = types.InlineKeyboardButton('<',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page - 1) + ",\"CountPage\":" + str(count) + "}")
                    item2 = types.InlineKeyboardButton('>',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page + 1) + ",\"CountPage\":" + str(count) + "}")
                    l = f"{page}/{count}"
                    item3 = types.InlineKeyboardButton(text=l, callback_data="pass")
                    item7 = types.InlineKeyboardButton("<<<",
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page - 100) + ",\"CountPage\":" + str(count) + "}")
                    item6 = types.InlineKeyboardButton("<<",
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page - 10) + ",\"CountPage\":" + str(count) + "}")
                    item5 = types.InlineKeyboardButton('>>>',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page + 100) + ",\"CountPage\":" + str(count) + "}")
                    item4 = types.InlineKeyboardButton('>>',
                                                       callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                                                           page + 10) + ",\"CountPage\":" + str(count) + "}")
                    spisok2 = ""
                    if (int(page) - 100) >= 0:
                        spisok2 += "item7 "
                    if (int(page) - 10) >= 0:
                        spisok2 += "item6 "
                    if (int(page) + 10) <= int(count):
                        spisok2 += "item4 "
                    if (int(page) + 100) <= int(count):
                        spisok2 += "item5 "
                    elem = []
                    for el in spisok2.split(" "):
                        if el != '':
                            elem.append(eval(el))
                    markup.add(item1, item3, item2)
                    markup.add(*elem)
                try:
                    y = eval((cards[page - 1])["name"])
                    photo = types.InputMediaPhoto(open(y["path"], 'rb'))
                    bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.id, media=photo)
                    if y["name"] in card_hand_list:
                        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.id,
                                                 caption=f'<b>{y["title"]}</b>\n\n💍Редкость: {y["rarity"]},\n🎖Оценка: {y["score"]},\n🌍Вселенная: {y["verse"]}\n✅ | Вы уже получили эту карту!',
                                                 parse_mode='HTML', reply_markup=markup)
                    else:
                        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.id,
                                                 caption=f'<b>{y["title"]}</b>\n\n💍Редкость: {y["rarity"]},\n🎖Оценка: {y["score"]},\n🌍Вселенная: {y["verse"]}\n😢 | Вы ещё не получили эту карту.',
                                                 parse_mode='HTML', reply_markup=markup)
                except:
                    pass
        if call.data == "show":
            if count == 1:
                bot.send_message(call.message.chat.id, "<b>Чтобы открыть эту функцию, получите две карты!</b>", parse_mode="HTML")
            else:
                page = 1
                markup = types.InlineKeyboardMarkup(row_width=2)
                item2 = types.InlineKeyboardButton('>', callback_data="{\"method\":\"pagination\",\"NumberPage\":" + str(page+1) + ",\"CountPage\":" + str(count) + "}")
                l = f"1/{len(card_hand_list)}"
                item3 = types.InlineKeyboardButton(text=l, callback_data="pass")
                markup.add(item3,item2)
                y = eval(card_hand_list[0])
                m=call.message.chat.id
                photo = open(y["path"], 'rb')
                bot.send_photo(m,photo=photo,caption=f'<b>{y["title"]}</b>\n\n💍Редкость: {y["rarity"]},\n🎖Оценка: {y["score"]},\n🌍Вселенная: {y["verse"]}', parse_mode="HTML",reply_markup=markup)

        if call.data == "show2":
            if count == 1:
                bot.send_message(call.message.chat.id, "<b>Чтобы открыть эту функцию, получите две карты!</b>", parse_mode="HTML")
            else:
                page = 1
                markup = types.InlineKeyboardMarkup(row_width=2)
                item2 = types.InlineKeyboardButton('>', callback_data="{\"method\":\"paginationt\",\"NumberPage\":" + str(page+1) + ",\"CountPage\":" + str(count) + "}")
                l = "✅ | Выбрать карту"
                item3 = types.InlineKeyboardButton(text=l, callback_data="{\"method\":\"complete\",\"NumberPage\":" + str(
                                                page) + "}")
                markup.add(item3,item2)
                y = eval(card_hand_list[0])
                m=call.message.chat.id
                photo = open(y["path"], 'rb')
                bot.delete_message(call.message.chat.id,call.message.id)
                bot.send_photo(m,photo=photo,caption=f'<b>{y["title"]}</b>\n\n💍Редкость: {y["rarity"]},\n🎖Оценка: {y["score"]},\n🌍Вселенная: {y["verse"]}', parse_mode="HTML",reply_markup=markup)
        if "complete" in call.data:
            json_string = json.loads((call.data.split("_"))[0])
            page = json_string['NumberPage']
            y = eval(card_hand_list[page - 1].replace(" ", ""))
            bot.delete_message(call.message.chat.id,call.message.id)
            bot.send_message(call.message.chat.id,f"✅ | Вы выбрали карту для трейда!")
            card_hand = cursor.execute(f"SELECT card_hand FROM users WHERE user_id ={call.from_user.id}").fetchone()
            card_hand2 = cursor.execute(f"SELECT card_hand FROM users WHERE trade_with ={call.from_user.id}").fetchone()
            card_handler = cursor.execute(f"SELECT user_id FROM users WHERE trade_with ={call.from_user.id}").fetchone()
            if str(y["name"]) in card_hand2:
                bot.send_message(call.message.chat.id, f"❗ | У игрока уже есть эта карта")
                cursor.execute(f"UPDATE users SET trade_with = 'None' WHERE user_id = {call.from_user.id}")
                cursor.execute(f"UPDATE users SET trade_with = 'None' WHERE trade_with = {call.from_user.id}")
                db.commit()
                db.close()
            else:
                photo = open(y["path"], 'rb')
                bot.send_photo(card_handler[0],photo=photo, caption=f'🥳 | Вам отправили карту!\nПолучена карта: \n<b>{y["title"]}</b>\n\n💍Редкость: {y["rarity"]},\n🎖Оценка: {y["score"]},\n🌍Вселенная: {y["verse"]}', parse_mode="HTML")
                to_card_rem =  card_hand[0].replace(f'{str(y["name"])}', '')
                to_card_hand = f'{card_hand2[0]} {str(y["name"])}'
                cursor.execute(f"UPDATE users SET card_hand = '{to_card_rem}' WHERE user_id = {call.from_user.id}")
                cursor.execute(f"UPDATE users SET card_hand = '{to_card_hand}' WHERE trade_with = {call.from_user.id}")
                cursor.execute(f"UPDATE users SET trade_with = 'None' WHERE user_id = {call.from_user.id}")
                cursor.execute(f"UPDATE users SET trade_with = 'None' WHERE trade_with = {call.from_user.id}")
                db.commit()
                db.close()
        if call.data == "show3":
             page = 1
             cards = rare_cards + epic_cards + mythic_cards + legend_cards + chrono_cards
             allcards = len(cards)
             markup = types.InlineKeyboardMarkup(row_width=4)
             item2 = types.InlineKeyboardButton('>', callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(page+1) + ",\"CountPage\":" + str(allcards) + "}")
             l = f"1/{allcards}"
             item3 = types.InlineKeyboardButton(text=l, callback_data="pass")
             item4 = types.InlineKeyboardButton('>>', callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                 page + 10) + ",\"CountPage\":" + str(count) + "}")
             item5 = types.InlineKeyboardButton('>>>', callback_data="{\"method\":\"paginationa\",\"NumberPage\":" + str(
                 page + 100) + ",\"CountPage\":" + str(count) + "}")
             markup.add(item3,item2, item4,item5)
             y = eval((cards[0])["name"])
             m=call.message.chat.id
             photo = open(y["path"], 'rb')
             bot.delete_message(call.message.chat.id,call.message.id)
             bot.send_photo(m,photo=photo,caption=f'<b>{y["title"]}</b>\n\n💍Редкость: {y["rarity"]},\n🎖Оценка: {y["score"]},\n🌍Вселенная: {y["verse"]}', parse_mode="HTML",reply_markup=markup)

        if "ar" in call.data:
            json_string = json.loads((call.data.split("_"))[0])
            user_id = json_string['Userid']
            user_to = json_string["UserTo"]
            if call.from_user.id == user_id:
                bot.delete_message(call.message.chat.id,call.message.id)
                markap = types.InlineKeyboardMarkup(row_width=2)
                clan_r = cursor.execute(f"SELECT clan FROM users WHERE user_id = {user_id}").fetchone()[0]
                markap.add(types.InlineKeyboardButton('Да', callback_data="{\"m\":\"acc\",\"Userid\":" + str(user_to) + ",\"Clan\":" + f"\"{str(clan_r)}\"" + "}"), types.InlineKeyboardButton('Нет', callback_data="{\"m\":\"den\",\"Userid\":" + str(user_to) + ",\"Clan\":" + f'\"{str(clan_r)}\"' + "}"))
                bot.send_message(call.message.chat.id, f'<a href="tg://user?id={user_to}">{bot.get_chat_member(user_to, user_to).user.first_name}</a>, тебя пригласили в клан <b>{clan_r}</b>! Принять приглашение?',parse_mode="HTML",reply_markup=markap)
                db.close()
        if "dr" in call.data:
            json_string = json.loads((call.data.split("_"))[0])
            user_id = json_string['Userid']
            if call.from_user.id == user_id:
                bot.delete_message(call.message.chat.id, call.message.id)
        if "acc" in call.data:
            json_string = json.loads((call.data.split("_"))[0])
            user_id = json_string['Userid']
            clan = json_string['Clan']
            if call.from_user.id == user_id:
                bot.send_message(call.message.chat.id,f'<a href="tg://user?id={user_id}">{bot.get_chat_member(user_id, user_id).user.first_name}</a>, ты принял приглашение!',parse_mode="HTML")
                clan_info = cursor.execute(f"SELECT members FROM clans WHERE clan = '{str(clan)}'").fetchone()[0]
                card = cursor.execute(f"SELECT cards_amount FROM users WHERE user_id = {int(user_id)}").fetchone()[0]
                clan_score = cursor.execute(f"SELECT score FROM clans WHERE clan = '{clan}'").fetchone()[0]
                amount = int(card) + int(clan_score)
                clan_info = f"{clan_info} {user_id}"
                cursor.execute(f"UPDATE users SET clan = '{clan}' WHERE user_id = {user_id}")
                db.commit()
                cursor.execute(f"UPDATE clans SET members = '{clan_info}', score = '{amount}' WHERE clan = '{clan}'")
                db.commit()
                db.close()
                bot.delete_message(call.message.chat.id, call.message.id)

        if "den" in call.data:
            json_string = json.loads((call.data.split("_"))[0])
            user_id = json_string['Userid']
            if call.from_user.id == user_id:
                bot.delete_message(call.message.chat.id, call.message.id)
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as x:
        print(x)