
from CAC import *
import sqlite3
#import datetime
#import os
#from rich import print
#from time import sleep
#
#rarity
rare_cards = [Aya,Kaname,Itsuki,Sudo,Kadovaki,Todano,Chigiri,Yu,Miyuki,Idzumi,Toreo,Stef,Yachiru,Hirako,Yutori,Makoto,Otoribashe,Muguruma,Sadzhin,Nonoe,Chisaki,Pochita,Yamato,Odzava,Kinro,Ginro,Magma,Yudzuriha,Nitta,Miwa,Dzuyenpei,Bayer,Avasaka,Fugaku,Sakura,Shikamaru,Jonhatan,Joshep2,Kiyoshi,Natala,Subaru,Momo,Turbo,Cid,Alpha,Beta,Gamma,Kaneki,Polnaref,Okuyasu,Neko,Rem,Ram,Beatrice,Tanjiro,Aoi,Higuti,Genya,Sumi,Naho,Kiyo,Sung_Jin,Ji_Hu,Key,Horikita]
epic_cards = [Aomine,Avrora,Amane,Sharlote,Shelly,RenYamai,SatoruByc,Kyue,Inoue,Isida,Sado,Siho,Akina,Byakuya,Gin,Kenpachi,MomoNisimia,Toshiro,Kurami,Ayano,Fil,Kobeni,Suika,Oki,Rabbit,Kisibe,Yaga,Maki,Deydara,Konan,Orochimaru,Juraev,Bachira,Isagi,Josuke,Kagami,Bols,Midorima,Seiko,Alexia,Airis,Touka,Kotaro,Caeser,Saiko,Nishima,Anko,Tanjiro2,Zenitsu,Inosuke,Chi_Jul,Nobara,Jin_Hy,Kakeru,Uedi,Pember,Obito]
mythic_cards = [Dio,Bulat,Emilia,Titose,Agari,Fubuki,KeySironage,Sonic,Yui,Kiske,Shihoin,Jiorno,Tenji,Chitose,Rukia,Kise,Masha,Jibril,Kohaku,Kaseki,YamatoGen,Power,Angel,Lazy,Esdes,Chelsi,Labbok,Kurome,Sussano,Murasakibara,Shidou,Touka2,Kakein,Bashame,Mitsuri,Shinobu,Obanai,Sanemi,Kan,Ren,Kushida,Misa,Hinami,RemDeath,Pain,Kakashi,Itachi,Saske,Megumi,Migel,Suguru,Todo,Jogo,Mahito]
legend_cards = [Akashi,Tatsumaki,King,Genos,Nadzimi,Alya,Tika,Motoko,Joshep,Ichigo,KeySinomia,Saraisi,Saki,Cukasa,Chrome,GenAsagiri,Nasa,Nagi,Tet,Yuki,Izuna,Aki,Denzi,Nash,Tetsu,Puck,Leone,SpeedWagon,Delta,KotaroGul,Jotaro,Tokaro,Giyu,Tokito,ChaIn,Sakayanagi,Ayato,Nia,Soitiro,Kel,Kurama,Minato,Tsunade,Echidna,Itadori,Toji]
chrono_cards = [Sattela,Rin,Kuroko,Komi,Aizen,Kaguya,Yudzaki,Miyako,Saitama,Garou,Yuiti,SenkoIsigami,Mahiru,Kubo,OkarunChad,Shadow,Sae,Makima,KanekiLastForm,Tatsumi,Akame,Main,Arima,Shikonoko,Gyomei,JinWo,Kiyotaka,L,Ryok,Lait,Naruto,Satoru,Sukuna,Sora,Shiro,Masachika]
limited_cards = [Penguin,Sibir,Sukufich,Igris]

#cards = rare_cards + epic_cards + mythic_cards + legend_cards + chrono_cards
#already = []
#for card in cards:
#    if os.path.isfile(card["path"]):
#        print(f"[bold green]{card.get("name")} - OK[/bold green]")
#    else:
#        print(f"[bold green]{card.get("name")} - NOT OK[/bold green]")
#    if card not in already:
#        already.append(str(card.get("name")))
#    else:
#        print(f"[bold red]{card.get("name")} - ALREADY[/bold red]")
#        sleep(2)
#    print(f"{str(card.get("name"))}\n{len(already)}")
#
#db = sqlite3.connect("db.db")
#cursor = db.cursor()
#cursor.execute('SELECT * FROM users')
#users = cursor.fetchall()
#z=0
#for user in users:
#    card_hand = user[9].split(' ')
#    card_hand.remove("None")
#    y = 0
#    for card in card_hand:
#        if eval(card)['rarity'] == "Хроно" and card != "Masachika" and card != "Kuroko" and card != "Mahiru":
#            y+=1
#            print(card)
#    if y!=0:
#        print(f"{user[1]} - {y}")
#        z+=1
#print(z)
#for user in users:
#    card_hand = user[9]
#    card_hand_list = card_hand.split(" ")
#    del card_hand_list[0]
#    card_amount = 0
#    if len(card_hand_list) > 0:
#        for card in range(0,(len(card_hand_list))):
#            y = eval(card_hand_list[card])
#            card_amount += y["score"]
#    cursor.execute(f"UPDATE users SET cards_amount = '{card_amount}' WHERE id = {user[0]}")
#    db.commit()

#score = cursor.execute(f"SELECT cards_amount FROM users WHERE clan = 'пупсики'").fetchall()
#count = 0
#for user_score in score:
#    print(user_score[0])
#    count = count+user_score[0]
#print(count)
