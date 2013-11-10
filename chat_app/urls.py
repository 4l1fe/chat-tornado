from django.conf.urls import patterns, url
from django.views.generic import TemplateView

urlpatterns = patterns('chat_app.views',
    url(r'^news/$', 'main'),
    url(r'^forum/', 'main'),
    url(r'^shop/', 'main'),
    url(r'^pedia/main/about/', 'main'),
    url(r'^pedia/main/rules/', 'main'),
    url(r'^$', 'main'),
    url(r'^show_tabs/', TemplateView.as_view(template_name='tabs.html')),
)
