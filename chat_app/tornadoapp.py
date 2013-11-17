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
from django.core.exceptions import ObjectDoesNotExist


logging_handler = logging.FileHandler(filename='chat_debug_log.txt', mode='a')
logging_formatter = logging.Formatter(fmt='[%(levelname)-8s] %(message)s')
logging_handler.setFormatter(logging_formatter)
logger = logging.getLogger()
logger.addHandler(logging_handler)
logger.setLevel(logging.INFO)

#filename = os.path.realpath('badwords.txt')
with open(r'D:\SCRIPTS\DJANGO\tornadochat\chat_app\badwords.txt') as file:
    badwords = [line.decode('cp1251').strip() for line in file.readlines()]
#logger.info(badwords)


def censor_message_text(text):
    for word in badwords:
        text = re.sub(re.escape(word), u'цензура', text)
    return text


class ChatSocketHandler(tornado.websocket.WebSocketHandler):

    connections = {}
    room_names = Room.objects.all().values_list('title', flat=True)
    for room_name in room_names:
        connections[room_name] = []

    def open(self):  # при подключении работаем с первой комнатой.
        morsel = self.request.cookies['sessionid']  # возвращает объект Morsel.
        sessionid = morsel.value
        decoded_session = Session.objects.get(pk=sessionid).get_decoded()
        user_id = decoded_session['_auth_user_id']  # _auth_user_id содержит pk объекта django.contrib.auth.models.User
        self.user = CustomUser.objects.get(user__pk=user_id)
        self.user_name = self.user.user.username
        first_room = self.room_names[0]
        self.connections[first_room].append(self) # добавляю своё соединение в общий словарь.

        users_in_f_room = [con.user_name for con in self.connections[first_room]]
        d = {'type': 'initialization',
             'rooms': [r.encode() for r in self.room_names],
             'users': users_in_f_room}
        mess = json.dumps(d)
        self.write_message(mess)  # шлю себе начальные данные(комнаты, пользователей в 1й комнате)

        for connection in self.connections[first_room]:
            if connection.user_name != self.user_name:  # уведомление в чат всем , кроме себя
                d = {'room': first_room,
                     'type': 'add_user',
                     'user': connection.user_name}
                mess = json.dumps(d)
                connection.write_message(mess)

    def chat_handler(self, message):
        if message['type'] == 'text':
            room = Room.objects.get(title=message['room'])
            message_obj = Message(room=room, username=self.user_name, text=message['text'])
            message_obj.save()
            d = {'room': message['room'],
                 'user': self.user_name,
                 'type': 'text',
                 'text': censor_message_text(message['text'])}
            mess = json.dumps(d)
            all_connections = [con for room in self.connections for con in self.connections[room]]
            logger.info('all_coon = '+str(all_connections))
            for con in all_connections:
                con.write_message(mess)
        elif message['type'] == 'disconnect':
            d = {'room': message['room'],
                 'type': 'disconnect',
                 'user': self.user_name}
            mess = json.dumps(d)
            all_connections = [con for room in self.connections for con in self.connections[room]]
            logger.info('pre_disconnect = '+str(all_connections))
            for con in all_connections:
                con.write_message(mess)
            self.connections[message['room']].remove(self)
            self.close()
        elif message['type'] == 'change_room':
            logger.info('pre_change = '+str(self.connections))
            self.connections[message['new_room']].append(self)
            logger.info('post_change = '+str(self.connections))
            self.connections[message['room']].remove(self)
            logger.info('post_pop = '+str(self.connections))
        elif message['type'] == 'edit_room_name':
            logger
            try:
                room = Room.objects.get(title=message['room'])
                room.title = message['edited_name']
                room.save()
                d = {'type': 'edit_room_name',
                     'room': message['room'],
                     'edited_name': message['edited_name']}
                mess = json.dumps(d)
            except ObjectDoesNotExist:
                d = {'type': 'error',
                     'text': 'Такой комнаты не существует'}
                mess = json.dumps(d)

            all_connections = [con for room in self.connections for con in self.connections[room]]
            for con in all_connections:
                con.write_message(mess)

    def on_message(self, message):
        parsed = tornado.escape.json_decode(message)
        if parsed['msg_from'] == 'chat':
            self.chat_handler(parsed['msg'])