from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from control import views

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
    # Examples:
    # url(r'^$', 'skeleton.views.home', name='home'),
    # url(r'^skeleton/', include('skeleton.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/subscription/upload/', 'subscription.views.uploader',
        {'page_name': 'csv_uploader'}, name="csv_uploader"),
    url(r'^admin/subscription/optouts/', 'subscription.views.optout_uploader',
        {'page_name': 'optout_uploader'}, name="optout_uploader"),
    url(r'^', include('subscription.urls')),
    url(r'^', include('servicerating.urls')),
    url(r'^', include('snappybouncer.urls')),
    url(r'^', include('controlinterface.urls')),
    url(r'^', include('registration.urls')),
    # url(r'^api/auth/',
    #     include('rest_framework.urls', namespace='rest_framework')),
    # url(r'^api/token-auth/',
    #     'rest_framework.authtoken.views.obtain_auth_token'),

) + staticfiles_urlpatterns()
