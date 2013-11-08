from django.conf.urls import patterns, url

urlpatterns = patterns('chat_app.views',
    url(r'^news/$', 'main'),
    url(r'^forum/', 'main'),
    url(r'^shop/', 'main'),
    url(r'^pedia/main/about/', 'main'),
    url(r'^pedia/main/rules/', 'main'),
    url(r'^$', 'main'),

    url(r'^rooms/(.+)/', 'room'),
)
