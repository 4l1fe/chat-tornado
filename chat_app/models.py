#coding:utf-8
from django.db import models
from django.contrib.auth.models import User
from tornadochat.settings import MAX_ROOMS_COUNT


class CustomUser(models.Model):
    user = models.OneToOneField(User)
    room = models.ForeignKey('Room')
    something_special = models.CharField(max_length=150, blank=True)

    def __unicode__(self):
        return '[{}] {}'.format(self.user.username, self.something_special)


class Room(models.Model):
    title = models.TextField(unique=True)

    def __unicode__(self):
        return '{0}'.format(self.title)

    def save(self, force_insert=False, force_update=False, using=None):
        if self.pk == 1:
            raise NotAllowedToChange
        if Room.objects.count() >= MAX_ROOMS_COUNT:
            raise ReachMaxRoomCount
        super(Room, self).save(force_insert, force_update, using)

    def delete(self, using=None):
        if self.pk == 1:
            raise NotAllowedToDelete
        super(Room, self).delete(using)


class Message(models.Model):
    text = models.TextField()
    username = models.TextField()
    room = models.ForeignKey(Room)
    datetime = models.DateTimeField(auto_now_add=True, db_index=True)


class NotAllowedToChange(Exception):
    """При попытке изменить запись основной комнаты"""
    pass

class NotAllowedToDelete(Exception):
    """При попытке удалить основную комнату"""
    pass

class ReachMaxRoomCount(Exception):
    """При создании комнат больше разрешенного количества"""
    pass