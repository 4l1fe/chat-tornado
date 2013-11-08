# -*- coding: utf-8 -*-
import re
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chat.settings")

import tornado.websocket
import tornado.escape
import logging
from .models import Room, Message, CustomUser
from django.contrib.sessions.models import Session


logging_handler = logging.FileHandler(filename='chat_debug_log.txt', mode='a')
logging_formatter = logging.Formatter(fmt='[%(levelname)-8s %(message)s')
logging_handler.setFormatter(logging_formatter)
logger = logging.getLogger()
logger.addHandler(logging_handler)
logger.setLevel(logging.INFO)

#filename = os.path.abspath(__file__)
with open(r'D:\SCRIPTS\DJANGO\tornadochat\chat_app\badwords.txt') as file:
    badwords = [line.decode('cp1251').strip() for line in file.readlines()]
logger.info(badwords)


def censor_message_text(text):
    #replace_words = u'хуй', u'пизда', u'блять', u'ебать'
    for word in badwords:
        text = re.sub(re.escape(word), u'<strong>цензура</strong>', text)
    return text


class ChatSocketHandler(tornado.websocket.WebSocketHandler):

    connections = {}
    room_names = Room.objects.all().values_list('title', flat=True)
    for room_name in room_names:
        connections[room_name] = {}

    def open(self):
        morsel = self.request.cookies['sessionid']  # возвращает объект Morsel.
        sessionid = morsel.value
        session = Session.objects.get(pk=sessionid)
        decoded_session = session.get_decoded()
        user_id = decoded_session['_auth_user_id']  # _auth_user_id содержит pk объекта django.contrib.auth.models.User
        self.user = CustomUser.objects.get(user__pk=user_id)
        self.user_current_room = self.user.room.title
        self.user_name = self.user.user.username

        self.connections[self.user_current_room][self.user_name] = self  # добавляю своё соединение в общий словарь.
        for online_user_name, connection in self.connections[self.user_current_room].items(): # цикл по всем соединениям.
            self.write_message('new_user:'+online_user_name)  # шлю себе имя каждого онлайн польз из существующих.
            if online_user_name != self.user_name:  # уведомление в чат всем , коме себя
                connection.write_message('new_user:'+self.user_name)  # шлю своё имя этому пользователю
                mess = '{0} joined the room!'.format(self.user_name)
                connection.write_message(mess)

        room_names = []  # посылаем все существ-ие комнаты с выделением текущей
        for room_name in self.room_names:
            if room_name == self.user_current_room:
                room_name = '<strong>{}</strong>'.format(room_name)
            room_names.append(room_name)
        mess = 'all_rooms:' + ';'.join(room_names)
        self.write_message(mess)

    def chat_handler(self, message):
        if message['text'] == 'disconnect':
            mess = '{0} left the room!'.format(self.user_name)
            mess_del = 'remove_user:{}'.format(self.user_name)
            for connection in self.connections[self.user_current_room].values():
                connection.write_message(mess_del)
                connection.write_message(mess)
            del self.connections[self.user_current_room][self.user_name]

        elif message['text'] == 'change_room':
            new_room = Room.objects.get(title=message['new_room'])  # узкое место, вдруг кто успеет сделать запрос на удалённую комнату
            self.user.room = new_room
            self.user.save()

            mess_del = 'remove_user:{}'.format(self.user_name)
            for online_user_name, connection in self.connections[self.user_current_room].items():
                if online_user_name != self.user_name:
                    connection.write_message(mess_del)

            del self.connections[self.user_current_room][self.user_name]  # переписываю соединение в другую комнату
            self.user_current_room = new_room.title
            self.connections[self.user_current_room][self.user_name] = self

            self.write_message('change_room:{}'.format(self.user_current_room))
            self.write_message('You entered to the {} room'.format(self.user_current_room))
            for online_user_name, connection in self.connections[self.user_current_room].items():  # цикл по всем соединениям.
                self.write_message('new_user:'+online_user_name)                                   # шлю себе имя каждого онлайн польз из существующих.
                if online_user_name != self.user_name:                                             # уведомление в чат всем , кроме себя, что я подключился
                    connection.write_message('new_user:'+self.user_name)                           # шлю своё имя этому пользователю
                    mess = '{0} joined the room!'.format(self.user_name)
                    connection.write_message(mess)
        else:
            room = Room.objects.filter(title=self.user_current_room).get()
            message['text'] = censor_message_text(message['text'])
            message_obj = Message(room=room, username=self.user_name, text=message['text'])
            message_obj.save()
            mess = u'{0}: {1}'.format(self.user_name, message['text'])
            for connection in self.connections[self.user_current_room].values():
                connection.write_message(mess)

    def on_message(self, message):
        parsed = tornado.escape.json_decode(message)
        if parsed['msgtype'] == 'chat':
            self.chat_handler(parsed['msg'])

