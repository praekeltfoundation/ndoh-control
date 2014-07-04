from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.authentication import ApiKeyAuthentication
from subscription.models import Subscription 
from djcelery.models import PeriodicTask

class PeriodicTaskResource(ModelResource):
    class Meta:
        queryset = PeriodicTask.objects.all()
        resource_name = 'periodic_task'
        list_allowed_methods = ['get']
        include_resource_uri = True
        always_return_data = True
        authentication = ApiKeyAuthentication()

class SubscriptionResource(ModelResource):
    schedule = fields.ToOneField(PeriodicTaskResource, 'schedule')
    class Meta:
        queryset = Subscription.objects.all()
        resource_name = 'subscription'
        list_allowed_methods = ['post', 'get']
        include_resource_uri = True
        always_return_data = True
        authentication = ApiKeyAuthentication()
