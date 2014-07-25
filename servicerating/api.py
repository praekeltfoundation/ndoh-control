from tastypie import fields
from tastypie.resources import ModelResource, Resource, ALL, Bundle
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import Authorization
from servicerating.models import Contact, Conversation, Response, UserAccount, Extra
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)

### ModelResource access using standard format

class UserAccountResource(ModelResource):
    class Meta:
        queryset = UserAccount.objects.all()
        resource_name = 'useraccount'
        list_allowed_methods = ['get']
        include_resource_uri = True
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        filtering = {
            'key': ALL,
        }



class ConversationResource(ModelResource):
    user_account = fields.ToOneField(UserAccountResource, 'user_account')
    class Meta:
        queryset = Conversation.objects.all()
        resource_name = 'conversation'
        list_allowed_methods = ['get']
        include_resource_uri = True
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        filtering = {
            'key': ALL,
            'user_account': ALL
        }


class ContactResource(ModelResource):
    user_account = fields.ToOneField(UserAccountResource, 'user_account')
    class Meta:
        queryset = Contact.objects.all()
        resource_name = 'contact'
        list_allowed_methods = ['get']
        include_resource_uri = True
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        filtering = {
            'key': ALL,
            'msisdn': ALL,
            'user_account': ALL
        }


class ResponseResource(ModelResource):
    contact = fields.ToOneField(ContactResource, 'contact')
    class Meta:
        queryset = Response.objects.all()
        resource_name = 'response'
        list_allowed_methods = ['get']
        include_resource_uri = True
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        filtering = {
            'key': ALL,
            'value': ALL
        }


class ExtraResource(ModelResource):
    contact = fields.ToOneField(ContactResource, 'contact')
    class Meta:
        queryset = Extra.objects.all()
        resource_name = 'extra'
        list_allowed_methods = ['get']
        include_resource_uri = True
        always_return_data = True
        authentication = ApiKeyAuthentication()
        authorization = Authorization()
        filtering = {
            'key': ALL,
            'value': ALL
        }

### Resource custom API for bulk load

# We need a generic object to shove data in/get data from.
class ServiceRatingObject(object):
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


class ServiceRatingResource(Resource):
    # Just like a Django ``Form`` or ``Model``, we're defining all the
    # fields we're going to handle with the API here.
    user_account = fields.CharField(attribute='user_account')
    conversation_key = fields.CharField(attribute='conversation_key')
    contact = fields.DictField(attribute='contact')
    answers = fields.DictField(attribute='answers')

    class Meta:
        resource_name = 'rate'
        list_allowed_methods = ['post']
        object_class = ServiceRatingObject
        authentication = ApiKeyAuthentication()
        authorization = Authorization()

    # The following methods need overriding regardless of the
    # data source.
    def detail_uri_kwargs(self, bundle_or_obj):
        kwargs = {}

        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.uuid
        else:
            kwargs['pk'] = bundle_or_obj.uuid

        return kwargs


    def obj_create(self, bundle, **kwargs):
        bundle.obj = ServiceRatingObject(initial=kwargs)
        bundle = self.full_hydrate(bundle)
        # Get the pre-existing User Account, we don't accept everything
        user_account = UserAccount.objects.get(key=bundle.obj.user_account)
        # Get the pre-existing Conversation, we don't accept everything
        conversation = Conversation.objects.get(key=bundle.obj.conversation_key)
        contact = Contact(conversation=conversation,
                          key = bundle.obj.contact["key"],
                          value = bundle.obj.contact,
                          msisdn = bundle.obj.contact["msisdn"])
        contact.save()
        for key, value in bundle.obj.contact["extra"].items():
            extra = Extra(contact=contact, key=key, value=value)
            extra.save()
        for key, value in bundle.obj.answers.items():
            response = Response(contact=contact, key=key, value=value)
            response.save()
        return bundle

        
