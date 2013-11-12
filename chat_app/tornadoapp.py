# -*- coding: utf-8 -*-
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chat.settings")

import tornado.websocket
import tornado.escape
import logging
import re
import json
from .models import Room, Message, CustomUser
from django.contrib.sessions.models import Session


logging_handler = logging.FileHandler(filename='chat_debug_log.txt', mode='a')
logging_formatter = logging.Formatter(fmt='[%(levelname)-8s %(message)s')
logging_handler.setFormatter(logging_formatter)
logger = logging.getLogger()
logger.addHandler(logging_handler)
logger.setLevel(logging.INFO)

#filename = os.path.abspath(__file__)
#with open(r'D:\SCRIPTS\DJANGO\tornadochat\chat_app\badwords.txt') as file:
#    badwords = [line.decode('cp1251').strip() for line in file.readlines()]
#logger.info(badwords)


def censor_message_text(text):
    #replace_words = u'хуй', u'пизда', u'блять', u'ебать'
    for word in badwords:
        text = re.sub(re.escape(word), u'цензура', text)
    return text


class ChatSocketHandler(tornado.websocket.WebSocketHandler):

    connections = {}
    room_names = Room.objects.all().values_list('title', flat=True)
    for room_name in room_names:
        connections[room_name] = {}

    def open(self):
        morsel = self.request.cookies['sessionid']  # возвращает объект Morsel.
        sessionid = morsel.value
        decoded_session = Session.objects.get(pk=sessionid).get_decoded()
        user_id = decoded_session['_auth_user_id']  # _auth_user_id содержит pk объекта django.contrib.auth.models.User
        self.user = CustomUser.objects.get(user__pk=user_id)
        self.user_name = self.user.user.username
        first_room = self.room_names[0]
        self.connections[first_room][self.user_name] = self  # добавляю своё соединение в общий словарь.

        users_in_f_room = [u for u in self.connections[first_room]]
        d = {'text': 'initialization',
             'rooms': self.room_names,
             'users': users_in_f_room}
        mess = json.dumps(d, ensure_ascii=False)
        self.write_message(mess)  # шлю себе начальные данные(комнаты, пользователей в 1й комнате)

        for user_in_f_room, connection in self.connections[first_room].items():  # цикл по всем соединениям.
            if user_in_f_room != self.user_name:  # уведомление в чат всем , кроме себя
                d = {'room': first_room,
                     'text': 'new_user',
                     'user': user_in_f_room}
                mess = json.dumps(d)
                connection.write_message(d)

    def chat_handler(self, message):
        if message['text'] == 'disconnect':
            mess_del = 'remove_user:{}'.format(self.user_name)
            for connection in self.connections.values():
                connection.write_message(mess_del)
            del self.connections[self.user_name]

        else:
            room = Room.objects.filter(title=message['room']).get()
            message_obj = Message(room=room, username=self.user_name, text=message['text'])
            message_obj.save()
            d = {'room': message['room'],
                 'user': self.user_name,
                 'text': censor_message_text(message['text'])}
            mess = json.dumps(d)
            for connection in self.connections[message['room']].values():
                connection.write_message(mess)

    def on_message(self, message):
        parsed = tornado.escape.json_decode(message)
        if parsed['msgtype'] == 'chat':
            self.chat_handler(parsed['msg'])

