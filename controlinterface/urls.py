from django.conf.urls import patterns, url, include
from controlinterface import views, api
from controlinterface.forms import AuthLoginForm
from tastypie.api import Api

# Setting the API base name and registering the API resources using
# Tastypies API function
api_resources = Api(api_name='v1/controlinterface')
api_resources.register(api.MetricResource())
api_resources.prepend_urls()

urlpatterns = patterns('',
    # Setting the urlpatterns to hook into the api urls
    url(r'^api/', include(api_resources.urls)),
    url(r'^controlinterface/$', views.index, name='index'),
    url(r'^controlinterface/servicerating/download/', views.servicerating_report, name='servicerating_report'),
    url(r'^controlinterface/servicerating/', views.servicerating, name='servicerating'),
    url(r'^controlinterface/login/$', 'django.contrib.auth.views.login', {'template_name': 'controlinterface/login.html', 'authentication_form' : AuthLoginForm }, name='login'),

)
