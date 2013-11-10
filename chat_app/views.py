#coding:utf-8
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template import RequestContext
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import login_required
from .models import Room, CustomUser
from forms import SelectRooms


@login_required(login_url='/login')
def main(request):
    cust_user = get_object_or_404(CustomUser, user=request.user.id)
    room_title = cust_user.room.title
    form = SelectRooms(instance=cust_user)
    # form['room'].css_classes('form-control')
    is_forum_page = request.path.startswith('/forum')
    return render(request, 'main.html', {'room_title': room_title,
                                         'form':form,
                                         'is_forum_page': is_forum_page})