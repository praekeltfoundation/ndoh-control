"""
Tests for Service Rating Application
"""
from tastypie.test import ResourceTestCase
from django.contrib.auth.models import User
from servicerating.models import (
    Contact, Conversation, Response, UserAccount, Extra)
from django.test import TestCase
from django.test.utils import override_settings
from requests import HTTPError
from requests.adapters import HTTPAdapter
from requests_testadapter import TestSession, Resp
from servicerating.tasks import (ensure_one_servicerating,
                                 vumi_fire_metric,
                                 vumi_update_smart_group_query,
                                 vumi_get_smart_group_contacts,
                                 send_reminders,
                                 vumi_update_contact_extras,
                                 vumi_send_message,
                                 get_date_filter,
                                 get_future_date)
import logging
from go_http.send import LoggingSender
from go_http.contacts import ContactsApiClient
from fake_go_contacts import Request, FakeContactsApi
import json
from datetime import date, timedelta


class ServiceRatingResourceTest(ResourceTestCase):
    fixtures = ["test_servicerating.json"]

    def setUp(self):
        super(ServiceRatingResourceTest, self).setUp()

        # Create a user.
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(
            self.username,
            'testuser@example.com', self.password)
        self.api_key = self.user.api_key.key

    def get_credentials(self):
        return self.create_apikey(self.username, self.api_key)

    def test_data_loaded(self):
        useraccounts = UserAccount.objects.all()
        self.assertEqual(useraccounts.count(), 1)
        conversations = Conversation.objects.all()
        self.assertEqual(conversations.count(), 1)
        contacts = Contact.objects.all()
        self.assertEqual(contacts.count(), 2)
        extras = Extra.objects.all()
        self.assertEqual(extras.count(), 2)
        responses = Response.objects.all()
        self.assertEqual(responses.count(), 2)

    def test_get_list_unauthorzied(self):
        self.assertHttpUnauthorized(
            self.api_client.get(
                '/api/v1/servicerating/useraccount/',
                format='json'))

    def test_api_keys_created(self):
        self.assertEqual(True, self.api_key is not None)

    def test_get_useraccount_list_json(self):
        resp = self.api_client.get(
            '/api/v1/servicerating/useraccount/', format='json',
            authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 1)

    def test_get_useraccount_filtered_list_json(self):
        filter_data = {
            "key": "useraccountkey"
        }

        resp = self.api_client.get(
            '/api/v1/servicerating/useraccount/',
            data=filter_data, format='json',
            authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 1)

    def test_get_useraccount_filtered_list_denied_json(self):
        filter_data = {
            "name": "useraccountkey"
        }

        resp = self.api_client.get(
            '/api/v1/servicerating/useraccount/', data=filter_data,
            format='json', authentication=self.get_credentials())
        json_item = json.loads(resp.content)
        self.assertHttpBadRequest(resp)
        self.assertEqual(
            "The 'name' field does not allow filtering.", json_item["error"])

    def test_post_good_json(self):
        data = {
            "user_account": "useraccountkey",
            "conversation_key": "dummyconversation",
            "contact": {
                "extra": {
                    "clinic_code": "123458",
                    "suspect_pregnancy": "yes",
                    "id_type": "none",
                    "ussd_sessions": "5",
                    "last_stage": "states_language",
                    "language_choice": "en",
                    "is_registered": "true",
                    "metric_sessions_to_register": "5"
                },
                "groups": [],
                "subscription": {},
                "msisdn": "+27001",
                "created_at": "2014-06-25 15:37:57.957",
                "user_account": "useraccountkey",
                "key": "dummycontactkeyexternal",
                "name": None,
                "surname": None,
                "email_address": None,
                "dob": None,
                "twitter_handle": None,
                "facebook_id": None,
                "bbm_pin": None,
                "gtalk_id": None
            },
            "answers": {
                "key1": "value1",
                "key2": "value2",
                "key3": "value3"
            }
        }

        self.assertHttpCreated(
            self.api_client.post('/api/v1/servicerating/rate/', format='json',
                                 authentication=self.get_credentials(),
                                 data=data))


class RecordingHandler(logging.Handler):

    """ Record logs. """
    logs = None

    def emit(self, record):
        if self.logs is None:
            self.logs = []
        self.logs.append(record)


class TestEnsureCleanServiceratings(TestCase):

    fixtures = ["test.json"]

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                       CELERY_ALWAYS_EAGER=True,
                       BROKER_BACKEND='memory',)
    def setUp(self):
        self.sender = LoggingSender('go_http.test')
        self.handler = RecordingHandler()
        logger = logging.getLogger('go_http.test')
        logger.setLevel(logging.INFO)
        logger.addHandler(self.handler)

    def check_logs(self, msg, levelno=logging.INFO):
        [log] = self.handler.logs
        self.assertEqual(log.msg, msg)
        self.assertEqual(log.levelno, levelno)

    def test_data_loaded(self):
        responses = Response.objects.all()
        self.assertEqual(len(responses), 10)

    def test_ensure_one_servicerating(self):
        results = ensure_one_servicerating.delay()
        self.assertEqual(results.get(), 5)

    def test_fire_metric(self):
        vumi_fire_metric.delay(
            metric="servicerating.duplicates", value=1,
            agg="last", sender=self.sender)
        self.check_logs("Metric: 'servicerating.duplicates' [last] -> 1")


class FakeContactsApiAdapter(HTTPAdapter):

    """
    Adapter for FakeContactsApi.

    This inherits directly from HTTPAdapter instead of using TestAdapter
    because it overrides everything TestAdaptor does.
    """

    def __init__(self, contacts_api):
        self.contacts_api = contacts_api
        super(FakeContactsApiAdapter, self).__init__()

    def send(self, request, stream=False, timeout=None,
             verify=True, cert=None, proxies=None):
        req = Request(
            request.method, request.path_url, request.body, request.headers)
        resp = self.contacts_api.handle_request(req)
        response = Resp(resp.body, resp.code, resp.headers)
        r = self.build_response(request, response)
        if not stream:
            # force prefetching content unless streaming in use
            r.content
        return r


make_contact_dict = FakeContactsApi.make_contact_dict
make_group_dict = FakeContactsApi.make_group_dict


class TestContactsApiClient(TestCase):
    API_URL = "http://example.com/go"
    AUTH_TOKEN = "auth_token"

    MAX_CONTACTS_PER_PAGE = 10

    def setUp(self):
        self.contacts_data = {}
        self.groups_data = {}
        self.contacts_backend = FakeContactsApi(
            "go/", self.AUTH_TOKEN, self.contacts_data, self.groups_data,
            contacts_limit=self.MAX_CONTACTS_PER_PAGE)
        self.session = TestSession()
        adapter = FakeContactsApiAdapter(self.contacts_backend)
        self.session.mount(self.API_URL, adapter)
        self.sender = LoggingSender('go_http.test')
        self.handler = RecordingHandler()
        logger = logging.getLogger('go_http.test')
        logger.setLevel(logging.INFO)
        logger.addHandler(self.handler)

    def make_client(self, auth_token=AUTH_TOKEN):
        return ContactsApiClient(
            auth_token, api_url=self.API_URL, session=self.session)

    def make_existing_contact(self, contact_data):
        existing_contact = make_contact_dict(contact_data)
        self.contacts_data[existing_contact[u"key"]] = existing_contact
        return existing_contact

    def make_existing_group(self, group_data):
        existing_group = make_group_dict(group_data)
        self.groups_data[existing_group[u'key']] = existing_group
        return existing_group

    def check_logs(self, msg):
        if type(self.handler.logs) != list:
            [logs] = self.handler.logs
        else:
            logs = self.handler.logs
        for log in logs:
            if log.msg == msg:
                return True
        return False

    def assert_http_error(self, expected_status, func, *args, **kw):
        try:
            func(*args, **kw)
        except HTTPError as err:
            self.assertEqual(err.response.status_code, expected_status)
        else:
            self.fail(
                "Expected HTTPError with status %s." % (expected_status,))

    def test_get_date_filter_fixed(self):
        fixed_day = date(2015, 1, 31)
        self.assertEqual(get_date_filter(date_filter=fixed_day), "2015-01-31")

    def test_get_date_filter_auto(self):
        today = date.today()
        stoday = today.strftime("%Y-%m-%d")
        self.assertEqual(get_date_filter(), stoday)

    def test_get_future_date_fixed(self):
        fixed_day = date(2015, 1, 1)
        self.assertEqual(get_future_date(7, date_current=fixed_day),
                         "2015-01-08")

    def test_get_future_date_auto(self):
        future = date.today() + timedelta(days=7)
        sfuture = future.strftime("%Y-%m-%d")
        self.assertEqual(get_future_date(7), sfuture)

    def test_update_smart_group_task(self):
        client = self.make_client()
        existing_group = self.make_existing_group({
            u'name': u'Service Rating Remind',
            u'query': u'test-query',
        })

        expected_group = existing_group.copy()
        expected_group[u'query'] = u'updated-query'

        results = vumi_update_smart_group_query.delay(existing_group["key"],
                                                      'updated-query',
                                                      client=client)
        returned_key = results.get()
        updated_group = self.groups_data[returned_key]
        self.assertEqual(updated_group, expected_group)

    def test_group_contacts_multiple_pages(self):
        expected_contacts = []
        self.make_existing_group({
            u'key': 'frank',
            u'name': 'key',
        })
        self.make_existing_group({
            u'key': 'bob',
            u'name': 'diffkey',
        })
        for i in range(self.MAX_CONTACTS_PER_PAGE + 1):
            expected_contacts.append(self.make_existing_contact({
                u"msisdn": u"+155564%d" % (i,),
                u"name": u"Arthur",
                u"surname": u"of Camelot",
                u"groups": ["frank"],
            }))
        self.make_existing_contact({
            u"msisdn": u"+1234567",
            u"name": u"Nancy",
            u"surname": u"of Camelot",
            u"groups": ["bob"],
        })
        client = self.make_client()
        contacts = list(client.group_contacts("frank"))

        contacts.sort(key=lambda d: d['msisdn'])
        expected_contacts.sort(key=lambda d: d['msisdn'])

        self.assertEqual(contacts, expected_contacts)

    def test_get_smart_group_contacts_task(self):
        client = self.make_client()
        expected_contacts = []
        self.make_existing_group({
            u'key': u'srremind',
            u'name': u'Service Rating Remind',
            u'query': u'name:Arthur',
        })
        for i in range(self.MAX_CONTACTS_PER_PAGE + 1):
            expected_contacts.append(self.make_existing_contact({
                u"msisdn": u"+155564%d" % (i,),
                u"name": u"Arthur",
                u"surname": u"of Camelot",
                u"extra": {
                    u"last_service_rating": u"never",
                    u"service_rating_reminder": "2015-02-01",
                    u"service_rating_reminders": "0",
                }
            }))
        self.make_existing_contact({
            u"msisdn": u"+1234567",
            u"name": u"Nancy",
            u"surname": u"of Camelot",
            u"groups": [u"srnoremind"],
            u"extra": {
                u"last_service_rating": u"never",
                u"service_rating_reminder": "",
                u"service_rating_reminders": "2",
            }
        })
        results = vumi_get_smart_group_contacts.delay(u"srremind",
                                                      client=client)
        contacts = list(results.get())

        contacts.sort(key=lambda d: d['msisdn'])
        expected_contacts.sort(key=lambda d: d['msisdn'])

        self.assertEqual(contacts, expected_contacts)

    def test_update_contact_extras_task(self):
        client = self.make_client()
        existing_contact = self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+155564",
            u"name": u"Arthur",
            u"surname": u"of Camelot",
            u"extra": {
                u"last_service_rating": u"never",
                u"service_rating_reminder": "2015-02-01",
                u"service_rating_reminders": "0",
            }
        })
        # the extras to refresh
        update = {
            u"last_service_rating": u"2015-03-01",
            u"service_rating_reminder": "2015-03-08",
            u"service_rating_reminders": "1",
        }

        expected_contact = existing_contact.copy()
        expected_contact["extra"] = update

        results = vumi_update_contact_extras.delay(u"knownuuid",
                                                   update,
                                                   client=client)

        self.assertEqual(self.contacts_data[results.get()], expected_contact)

    def test_send_message_task(self):
        client = self.make_client()
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+155564",
            u"name": u"Arthur",
            u"surname": u"of Camelot"
        })

        send_message = vumi_send_message.delay(u"knownuuid",
                                               "Hello!",
                                               client=client,
                                               sender=self.sender)
        result = send_message.get()
        self.assertEqual(result, u"knownuuid")
        self.assertEqual(True,
                         self.check_logs(
                             "Message: 'Hello!' sent to u'+155564'"))

    def test_send_message_task_failed(self):
        client = self.make_client()
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+155564",
            u"name": u"Arthur",
            u"surname": u"of Camelot"
        })

        send_message = vumi_send_message.delay(u"unknownuuid",
                                               "Hello!",
                                               client=client,
                                               sender=self.sender)

        self.assertEqual(False,  send_message.get())

    def test_reminders_chain_task(self):
        # This is a more detailed set of grouped asserts because of the chain
        client = self.make_client()
        self.make_existing_group({
            u'key': u'srremind',
            u'name': u'Service Rating Remind',
            u'query': u'name:Arthur',
        })
        # not sent to
        for i in range(self.MAX_CONTACTS_PER_PAGE + 1):
            self.make_existing_contact({
                u"key": u"not%s" % i,
                u"msisdn": u"+155564%d" % (i,),
                u"name": u"Arthur",
                u"surname": u"of Camelot",
                u"extra": {
                    u"last_service_rating": u"never",
                    u"service_rating_reminder": "2015-02-01",
                    u"service_rating_reminders": "0",
                }
            })
        # send to
        for i in range(2):
            self.make_existing_contact({
                u"key": u"key%s" % i,
                u"msisdn": u"+1234567%d" % (i,),
                u"name": u"Nancy",
                u"surname": u"of Camelot",
                u"extra": {
                    u"last_service_rating": u"never",
                    u"service_rating_reminder": "2015-02-01",
                    u"service_rating_reminders": "0",
                }
            })
        results = send_reminders.delay(u"srremind", client=client,
                                       sender=self.sender)
        contacts_affected = results.get()

        self.assertEqual(contacts_affected, "Reminders sent: 2")
        self.assertEqual(True, self.check_logs(
            "Message: 'Thank you for "
            "registering. We can only "
            "improve if we get your feedback. Please dial "
            "*134*550*4# to rate the service you received at the "
            "clinic you registered at' sent to u'+12345670'"))
        self.assertEqual(True, self.check_logs(
            "Message: 'Thank you for "
            "registering. We can only "
            "improve if we get your feedback. Please dial "
            "*134*550*4# to rate the service you received at the "
            "clinic you registered at' sent to u'+12345671'"))
        # Should not send to Arthur contacts
        self.assertEqual(False, self.check_logs(
            "Message: 'Thank you for "
            "registering. We can only "
            "improve if we get your feedback. Please dial "
            "*134*550*4# to rate the service you received at the "
            "clinic you registered at' sent to u'+1555641'"))
        self.assertEqual(
            self.contacts_data["key1"]["extra"]["service_rating_reminders"],
            "1")
        self.assertEqual(
            self.contacts_data["not1"]["extra"]["service_rating_reminders"],
            "0")
