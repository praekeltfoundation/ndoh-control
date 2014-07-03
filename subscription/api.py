from tastypie.resources import ModelResource
from tastypie.authentication import ApiKeyAuthentication
from subscription.models import Subscription 

class SubscriptionResource(ModelResource):
    class Meta:
        queryset = Subscription.objects.all()
        resource_name = 'subscription'
        list_allowed_methods = ['post', 'get']
        authentication = ApiKeyAuthentication()
