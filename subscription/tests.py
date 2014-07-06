"""
Tests for Subscription Application 
"""
from tastypie.test import ResourceTestCase
from django.contrib.auth.models import User
import json


class SubscriptionResourceTest(ResourceTestCase):

    def setUp(self):
        super(SubscriptionResourceTest, self).setUp()

        # Create a user.
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(self.username,
            'testuser@example.com', self.password)
        self.api_key = self.user.api_key.key

    def get_credentials(self):
        return self.create_apikey(self.username, self.api_key)

    def test_get_list_unauthorzied(self):
        self.assertHttpUnauthorized(self.api_client.get('/api/v1/subscription/', format='json'))

    def test_api_keys_created(self):
        self.assertEqual(True, self.api_key is not None) 

    def test_get_list_json(self):
        resp = self.api_client.get('/api/v1/subscription/', format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 0)

    def test_post_subscription_with_non_existent_schedule_ref(self):
        data = {
            "active": True,
            "completed": False,
            "contact_key": "82309423098",
            "lang": "en",
            "next_sequence_number": 1,
            "resource_uri": "/api/v1/subscription/1/",
            "schedule": "/api/v1/periodic_task/10/", # Non existent task
            "to_addr": "+271234",
            "user_account": "80493284823"
        }

        response = self.api_client.post('/api/v1/subscription/', format='json',
                                        authentication=self.get_credentials(),
                                        data=data)
        json_item = json.loads(response.content)
        self.assertHttpBadRequest(response)
        self.assertEqual("Could not find the provided object via resource URI " \
                         "'/api/v1/periodic_task/10/'.", json_item["error"])

    def test_post_subscription_good(self):
        data = {
            "contact_key": "82309423098",
            "lang": "en",
            "message_set": "/api/v1/message_set/3/",
            "next_sequence_number": 1,
            "resource_uri": "/api/v1/subscription/1/",
            "schedule": "/api/v1/periodic_task/1/",
            "to_addr": "+271234",
            "user_account": "80493284823"
        }

        response = self.api_client.post('/api/v1/subscription/', format='json',
                                        authentication=self.get_credentials(),
                                        data=data)
        json_item = json.loads(response.content)
        self.assertEqual("82309423098", json_item["contact_key"])
        self.assertEqual(True, json_item["active"])
        self.assertEqual(False, json_item["completed"])
        self.assertEqual("en", json_item["lang"])
        self.assertEqual("/api/v1/message_set/3/", json_item["message_set"])
        self.assertEqual(1, json_item["next_sequence_number"])
        self.assertEqual("/api/v1/periodic_task/1/", json_item["schedule"])
        self.assertEqual("+271234", json_item["to_addr"])
        self.assertEqual("80493284823", json_item["user_account"])
