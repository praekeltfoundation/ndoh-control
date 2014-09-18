from django.conf.urls import patterns, include, url
from control import views

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
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
    url(r'^control/', 'control.views.control_index'),
    url(r'^', include('subscription.urls')),
    url(r'^', include('servicerating.urls')),
    url(r'^', include('snappybouncer.urls')),

)
