# -*- coding: utf-8 -*-
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chat.settings")

import tornado.websocket
import tornado.escape
import logging
import re
import json
from copy import copy
from .models import Room, Message, CustomUser, NotAllowedToChange, NotAllowedToDelete, ReachMaxRoomCount
from django.contrib.sessions.models import Session
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError


logging_handler = logging.FileHandler(filename='chat_debug_log.txt', mode='a')
logging_formatter = logging.Formatter(fmt='[%(levelname)-8s %(asctime)s] %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
logging_handler.setFormatter(logging_formatter)
logger = logging.getLogger()
logger.addHandler(logging_handler)
logger.setLevel(logging.INFO)

#filename = os.path.realpath('badwords.txt')
filename = os.path.join(os.path.dirname(__file__), 'badwords.txt')
with open(filename) as file:
    badwords = [line.decode('cp1251').strip() for line in file.readlines()]
#logger.info(badwords)


def censor_message_text(text):
    for word in badwords:
        text = re.sub(re.escape(word), u'цензура', text)
    return text


class ChatSocketHandler(tornado.websocket.WebSocketHandler):

    # Создание соединений с комнатами при запуске сервера.
    connections = {}
    room_names = Room.objects.order_by('pk').values_list('title', flat=True)
    for room_name in room_names:
        connections[room_name] = []

    def open(self):  # при подключении работаем с первой комнатой.
        morsel = self.request.cookies['sessionid']  # возвращает объект Morsel.
        sessionid = morsel.value
        decoded_session = Session.objects.get(pk=sessionid).get_decoded()
        user_id = decoded_session['_auth_user_id']  # _auth_user_id содержит pk объекта django.contrib.auth.models.User
        self.user = CustomUser.objects.get(user__pk=user_id)
        self.user_name = self.user.user.username
        self.room_names = Room.objects.order_by('pk').values_list('title', flat=True)  # Комнаты могут обновиться, проверяем.
        self.main_room = self.room_names[0].decode()
        self.connections[self.main_room].append(self) # добавляю своё соединение в общий словарь.

        d = {'type': 'initialization',
             'rooms': [r.encode() for r in self.room_names]}
        mess = json.dumps(d)
        self.write_message(mess)  # шлю себе все комнаты

        users_in_main_room = [conn.user_name for conn in self.connections[self.main_room]]
        d = {'type': 'all_users',
             'users': users_in_main_room}
        mess = json.dumps(d)
        self.write_message(mess)  # шлю всех польз-й из основной комнаты

        for conn in self.connections[self.main_room]:
            if conn.user_name != self.user_name:  # уведомление в чат всем , кроме себя
                d = {'type': 'add_user',
                     'room': self.main_room,
                     'user': self.user_name}
                mess = json.dumps(d)
                conn.write_message(mess)

    def on_message(self, message):
        parsed = tornado.escape.json_decode(message)
        if parsed['msg_from'] == 'chat':
            self.chat_handler(parsed['msg'])

    def custom_write_message(self, d):
        mess = json.dumps(d)
        all_connections = [conn for room in self.connections for conn in self.connections[room]]
        for conn in all_connections:
            conn.write_message(mess)

    def chat_handler(self, message):
        if message['type'] == 'text':
            try:
                room = Room.objects.get(title=message['room'])
                message_obj = Message(room=room, username=self.user_name, text=message['text'])
                message_obj.save()
                d = {'type': 'text',
                     'room': message['room'],
                     'user': self.user_name,
                     'text': censor_message_text(message['text'])}
            except ObjectDoesNotExist:
                d = {'type': 'error',
                     'text': 'Такой комнаты не существует'}
            mess = json.dumps(d)
            self.custom_write_message(d)
        elif message['type'] == 'disconnect':
            d = {'type': 'disconnect',
                 'room': message['room'],
                 'user': self.user_name}
            self.custom_write_message(d)
            self.connections[message['room']].remove(self)
            self.close()
        elif message['type'] == 'change_room':
            self.connections[message['new_room']].append(self)
            self.connections[message['room']].remove(self)

            users_in_new_room = [conn.user_name for conn in self.connections[message['new_room']]]
            d = {'type': 'all_users',  # шлю себе всех пользователей из новой комнаты
                 'users': users_in_new_room}
            mess = json.dumps(d)
            self.write_message(mess)

            for conn in self.connections[message['new_room']]:
                if conn.user_name != self.user_name:
                    d = {'type': 'add_user',
                         'room': message['new_room'],
                         'user': self.user_name}
                    mess = json.dumps(d)
                    conn.write_message(mess)

            d = {'type': 'remove_user',
                 'user': self.user_name,
                 'room': message['room']}
            mess = json.dumps(d)
            for conn in self.connections[message['room']]:
                conn.write_message(mess)
        elif message['type'] == 'create_room' and self.user.user.has_perm('chat_app.add_room'):
            try:
                created_room = Room(title=message['created_room'])
                created_room.save()
                self.connections[message['created_room']] = []
                d = {'type': 'create_room',
                     'created_room': message['created_room']}
            except IntegrityError:
                d = {'type': 'error',
                     'text': 'Такая комната уже существует'}
            except ReachMaxRoomCount:
                d = {'type': 'error',
                     'text': 'Создано максимально допустимое количество комнат'}
            self.custom_write_message(d)
        elif message['type'] == 'edit_room_name' and self.user.user.has_perm('chat_app.change_room'):
            try:
                room = Room.objects.get(title=message['room'])
                room.title = message['edited_name']
                room.save()
                self.connections[message['edited_name']] = copy(self.connections[message['room']])
                del self.connections[message['room']]
                d = {'type': 'edit_room_name',
                     'room': message['room'],
                     'edited_name': message['edited_name']}
            except ObjectDoesNotExist:
                d = {'type': 'error',
                     'text': 'Такой комнаты не существует'}
            except NotAllowedToChange:
                d = {'type': 'error',
                     'text': 'Нельзя переименовать'}
            self.custom_write_message(d)
        elif message['type'] == 'delete_room' and self.user.user.has_perm('chat_app.delete_room'):
            try:
                if not self.connections[message['deleted_room']]:
                    room = Room.objects.get(title=message['deleted_room'])
                    room.delete()
                    #users_in_main_room = [conn.user_name for conn in self.connections[self.main_room]]
                    #users = users_in_main_room + [conn.user_name for conn in self.connections[message['deleted_room']]]
                    #for conn in self.connections[message['deleted_room']]:
                    #    d = {'type': 'drop_to_main',
                    #         'users': users,
                    #         'room': self.main_room}
                    #    mess = json.dumps(d)
                    #    conn.write_message(d)
                    #self.connections[self.main_room].extend(copy(self.connections[message['deleted_room']]))
                    del self.connections[message['deleted_room']]
                    d = {'type': 'delete_room',
                         'deleted_room': message['deleted_room']}
                else:
                    d = {'type': 'error',
                         'text': 'В комнате еще находятся пользователи'}
            except ObjectDoesNotExist:
                d = {'type': 'error',
                     'text': 'Такой комнаты не существует'}
            except NotAllowedToDelete:
                d = {'type': 'error',
                     'text': 'Нельзя удалить'}
            if d['type'] == 'error':
                mess = json.dumps(d)
                self.write_message(mess)
            else:
                self.custom_write_message(d)