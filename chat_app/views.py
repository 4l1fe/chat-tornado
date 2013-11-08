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


def room(request, room_name):
    current_room = get_object_or_404(Room, title=room_name)
    room_users = CustomUser.objects.filter(room=current_room).values_list('name', flat=True)

    error = None
    if request.method == 'POST':
        new_username = request.POST['new_username']
        if not new_username:
            error = 'Error empty username'
        elif new_username in room_users:
            error = 'Choose another name...'
        elif not error:
            chatuser = CustomUser(name=new_username, room=current_room)
            CustomUser.save()
            messages = current_room.message_set.filter()[:5]
            d = dict(room_name=room_name, username=new_username, messages=messages)
            return render_to_response('chat.html', d,
                        context_instance=RequestContext(request))
    return render_to_response( 'login.html', {'error':error,
                        'room_users': ', '.join(room_users)},
                        context_instance=RequestContext(request))
