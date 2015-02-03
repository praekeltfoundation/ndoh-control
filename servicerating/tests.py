"""
Tests for Service Rating Application
"""
from tastypie.test import ResourceTestCase
from django.contrib.auth.models import User
from servicerating.models import (
    Contact, Conversation, Response, UserAccount, Extra)
from django.test import TestCase
from django.test.utils import override_settings
from servicerating.tasks import ensure_one_servicerating, vumi_fire_metric
import logging
from go_http.send import LoggingSender
import json


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
        print record
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
