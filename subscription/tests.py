"""
Tests for Subscription Application 
"""
from tastypie.test import ResourceTestCase
from django.contrib.auth.models import User


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

    def test_get_list_json(self):
        resp = self.api_client.get('/api/v1/subscription/', format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 0)
