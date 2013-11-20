from django.db import models
from django.contrib.auth.models import User


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

    def delete(self, using=None):
        if self.pk == 1:
            return
        super(Room, self).delete(using)


class Message(models.Model):
    text = models.TextField()
    username = models.TextField()
    room = models.ForeignKey(Room)
    datetime = models.DateTimeField(auto_now_add=True, db_index=True)
