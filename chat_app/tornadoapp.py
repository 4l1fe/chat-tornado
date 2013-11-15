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
logging_formatter = logging.Formatter(fmt='[%(levelname)-8s] %(message)s')
logging_handler.setFormatter(logging_formatter)
logger = logging.getLogger()
logger.addHandler(logging_handler)
logger.setLevel(logging.INFO)

#filename = os.path.realpath('badwords.txt')
with open(r'D:\SCRIPTS\DJANGO\tornado_chat\chat_app\badwords.txt') as file:
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
        d = {'text': 'initialization',
             'rooms': [r.encode() for r in self.room_names],
             'users': users_in_f_room}
        mess = json.dumps(d)
        self.write_message(mess)  # шлю себе начальные данные(комнаты, пользователей в 1й комнате)

        #for user_in_f_room, connection in self.connections[first_room].items():
        #    if user_in_f_room != self.user_name:  # уведомление в чат всем , кроме себя
        #        d = {'room': first_room,
        #             'text': 'new_user',
        #             'user': user_in_f_room}
        #        mess = json.dumps(d)
        #        connection.write_message(mess)

        for connection in self.connections[first_room]:
            if connection.user_name != self.user_name:  # уведомление в чат всем , кроме себя
                d = {'room': first_room,
                     'text': 'new_user',
                     'user': connection.user_name}
                mess = json.dumps(d)
                connection.write_message(mess)

    #def chat_handler(self, message):
    #    if message['text'] == 'disconnect':
    #        d = {'room': message['room'],
    #             'text': 'remove_user',
    #             'user': self.user_name}
    #        mess = json.dumps(d)
    #        all_connections = [con for k in self.connections for con in self.connections[k].values()]
    #        for con in all_connections:
    #            con.write_message(mess)
    #        del self.connections[message['room']][self.user_name]
    #    elif message['text'] == 'change_room':
    #        logger.info('pre_change = '+self.connections)
    #        self.connections[message['new_room']][self.user_name] = self
    #        logger.info('post_change = '+self.connections)
    #        self.connections[message['room']].pop(self.user_name)  # тут чё та валится постоянно
    #        logger.info('post_pop = '+self.connections)
    #    else:
    #        room = Room.objects.get(title=message['room'])
    #        message_obj = Message(room=room, username=self.user_name, text=message['text'])
    #        message_obj.save()
    #        d = {'room': message['room'],
    #             'user': self.user_name,
    #             'text': censor_message_text(message['text'])}
    #        mess = json.dumps(d)
    #        all_connections = [con for k in self.connections for con in self.connections[k].values()]
    #        logger.info('all_coon = '+str(all_connections))
    #        for con in all_connections:
    #            con.write_message(mess)

    def chat_handler(self, message):
        if message['text'] == 'disconnect':
            d = {'room': message['room'],
                 'text': 'remove_user',
                 'user': self.user_name}
            mess = json.dumps(d)
            all_connections = [con for k in self.connections for con in self.connections[k]]
            for con in all_connections:
                con.write_message(mess)
            del self
        elif message['text'] == 'change_room':
            logger.info('pre_change = '+str(self.connections))
            self.connections[message['new_room']].append(self)
            logger.info('post_change = '+str(self.connections))
            self.connections[message['room']].remove(self)  # тут чё та валится постоянно
            logger.info('post_pop = '+str(self.connections))
        else:
            room = Room.objects.get(title=message['room'])
            message_obj = Message(room=room, username=self.user_name, text=message['text'])
            message_obj.save()
            d = {'room': message['room'],
                 'user': self.user_name,
                 'text': censor_message_text(message['text'])}
            mess = json.dumps(d)
            all_connections = [con for k in self.connections for con in self.connections[k]]
            logger.info('all_coon = '+str(all_connections))
            for con in all_connections:
                con.write_message(mess)

    def on_message(self, message):
        parsed = tornado.escape.json_decode(message)
        if parsed['msgtype'] == 'chat':
            self.chat_handler(parsed['msg'])


#            [ERROR   ] Uncaught exception in /websocket
#Traceback (most recent call last):
#  File "C:\Python27\lib\site-packages\tornado\websocket.py", line 303, in wrapper
#    return callback(*args, **kwargs)
#  File "D:\SCRIPTS\DJANGO\tornado_chat\chat_app\tornadoapp.py", line 96, in on_message
#    if parsed['msgtype'] == 'chat':
#  File "D:\SCRIPTS\DJANGO\tornado_chat\chat_app\tornadoapp.py", line 74, in chat_handler
#    del self.connections[message['room']][self.user_name]
#KeyError: u'site_admin'
#[ERROR   ] Uncaught exception in /websocket
#Traceback (most recent call last):
#  File "C:\Python27\lib\site-packages\tornado\websocket.py", line 303, in wrapper
#    return callback(*args, **kwargs)
#  File "D:\SCRIPTS\DJANGO\tornado_chat\chat_app\tornadoapp.py", line 96, in on_message
#    if parsed['msgtype'] == 'chat':
#  File "D:\SCRIPTS\DJANGO\tornado_chat\chat_app\tornadoapp.py", line 74, in chat_handler
#    del self.connections[message['room']][self.user_name]
#KeyError: u'user1'
