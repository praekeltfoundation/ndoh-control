from django.conf.urls import url, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'nursesources', views.NurseSourceViewSet)


# Wire up our API using automatic URL routing.
urlpatterns = [
    url(r'^api/v2/', include(router.urls)),
    url(r'^api/v2/nurseregs/', views.NurseRegPost.as_view()),
]
