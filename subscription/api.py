from tastypie.resources import ModelResource
from tastypie.authentication import ApiKeyAuthentication
from subscription.models import Subscription 

# Auth set up stuff to ensure apikeys are created
# ensures endpoints require username and api_key values to access
from django.contrib.auth.models import User
from django.db import models
# from tastypie.models import create_api_key

# models.signals.post_save.connect(create_api_key, sender=User)

class SubscriptionResource(ModelResource):
    class Meta:
        queryset = Subscription.objects.all()
        resource_name = 'subscription'
        list_allowed_methods = ['post', 'get']
        authentication = ApiKeyAuthentication()
