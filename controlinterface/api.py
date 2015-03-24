from tastypie import fields
from tastypie.resources import Resource
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import Authorization
from go_http.metrics import MetricsApiClient
from django.conf import settings
# Resource custom API for bulk load


# We need a generic object to shove data in/get data from.
class MetricObject(object):

    def __init__(self, initial=None):
        self.__dict__['_data'] = {}

        if hasattr(initial, 'items'):
            self.__dict__['_data'] = initial

    def __getattr__(self, name):
        return self._data.get(name, None)

    def __setattr__(self, name, value):
        self.__dict__['_data'][name] = value

    def to_dict(self):
        return self._data


class MetricResource(Resource):
    # Just like a Django ``Form`` or ``Model``, we're defining all the
    # fields we're going to handle with the API here.
    key = fields.CharField(attribute='key')
    values = fields.ListField(attribute='values')

    class Meta:
        resource_name = 'metric'
        list_allowed_methods = ['get']
        object_class = MetricObject
        authentication = ApiKeyAuthentication()
        authorization = Authorization()

    # Specific to this resource, just to get the needed Riak bits.
    def _client(self):
        return MetricsApiClient(settings.VUMI_GO_API_TOKEN,
                                settings.VUMI_GO_API_URL)

    def get_object_list(self, request):
        client = self._client()
        filters = {
            "m": [],
            "start": "",
            "interval": "",
            "nulls": ""
        }

        for k, v in request.GET.lists():
            filters[k] = v

        results = []
        for metric in filters['m']:
            response = client.get_metric(metric,
                                         filters['start'],
                                         filters['interval'],
                                         filters['nulls'])
            new_obj = MetricObject()
            new_obj.key = metric
            if metric in response:
                new_obj.values = response[metric]
            else:
                new_obj.values = []
            results.append(new_obj)

        return results

    def obj_get_list(self, bundle, **kwargs):
        return self.get_object_list(bundle.request)
