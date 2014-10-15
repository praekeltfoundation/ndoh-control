from django.conf.urls import patterns, url
from controlinterface import views
from controlinterface.forms import AuthLoginForm



urlpatterns = patterns('',
    # Setting the urlpatterns to hook into the api urls
    url(r'^controlinterface/$', views.index, name='index'),
    # url(r'^controlinterface/login/$', views.login, name='login'),
    url(r'^controlinterface/login/$', 'django.contrib.auth.views.login', {'template_name': 'controlinterface/login.html', 'authentication_form' : AuthLoginForm }, name='login'),

)
