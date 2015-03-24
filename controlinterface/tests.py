from django.test import TestCase, Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from subscription.models import Message, Subscription


class MessageEditViewTests(TestCase):

    fixtures = ["test_controlinterface_message.json"]

    def setUp(self):
        # Create a user.
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(
            self.username,
            'testuser@example.com', self.password)
        self.client = Client()

    def login(self):
        self.client.login(username='testuser', password='testpass')

    def test_message_search_view_unauthorized(self):
        response = self.client.get(
            reverse('controlinterface.views.message_edit'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please, log in to continue.")

    def test_message_search_view(self):
        """
        If no params set yet, should ask for search params
        """
        self.login()
        response = self.client.get(
            reverse('controlinterface.views.message_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find a message to edit")

    def test_message_edit_view(self):
        """
        If search params, should ask for edit content
        """
        self.login()
        searchform = {
            "messageaction": "find",
            "message_set": 3,
            "sequence_number": 1,
            "lang": "en"
        }
        response = self.client.post(
            reverse('controlinterface.views.message_edit'), searchform)
        self.assertContains(response, "Edit message")
        self.assertContains(response, "Message 1 on accelerated")

    def test_message_edit_view_not_found(self):
        """
        If search params, but invalid should ask again
        """
        self.login()
        searchform = {
            "messageaction": "find",
            "message_set": 3,
            "sequence_number": 100,
            "lang": "en"
        }
        response = self.client.post(
            reverse('controlinterface.views.message_edit'), searchform)
        self.assertContains(response, "Find a message to edit")
        self.assertContains(response, "Message could not be found")

    def test_message_confirm_view(self):
        """
        If submit changes, should ask for confirm
        """
        self.login()
        editform = {
            "messageaction": "update",
            "message_id": 1,
            "content": "Message 1 on accelerated now edited",
        }
        response = self.client.post(
            reverse('controlinterface.views.message_edit'), editform)
        self.assertContains(response, "Confirm updated message")
        self.assertContains(response, "Message 1 on accelerated now edited")

    def test_message_saved_view(self):
        """
        If confirm changes, should validate
        """
        self.login()
        confirmform = {
            "messageaction": "confirm",
            "message_id": 1,
            "content": "Message 1 on accelerated now edited",
        }
        response = self.client.post(
            reverse('controlinterface.views.message_edit'), confirmform)
        self.assertContains(response, "Message has been updated")
        message = Message.objects.get(pk=1)
        self.assertEqual(
            message.content, "Message 1 on accelerated now edited")


class SubscriptionEditViewTests(TestCase):

    fixtures = ["test_controlinterface_subscription.json"]

    def setUp(self):
        # Create a user.
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(
            self.username,
            'testuser@example.com', self.password)
        self.client = Client()

    def login(self):
        self.client.login(username='testuser', password='testpass')

    def test_subscription_search_view_unauthorized(self):
        response = self.client.get(
            reverse('controlinterface.views.subscription_edit'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please, log in to continue.")

    def test_subscription_search_view(self):
        """
        If no params set yet, should ask for search params
        """
        self.login()
        response = self.client.get(
            reverse('controlinterface.views.subscription_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find a user to edit")

    def test_subscription_edit_view(self):
        """
        If search params, should show list of subs and actions
        """
        self.login()
        searchform = {
            "subaction": "find",
            "msisdn": "+271112"
        }
        response = self.client.post(
            reverse('controlinterface.views.subscription_edit'), searchform)
        self.assertContains(response, "Current Subscriptions")
        self.assertContains(response, "Cancel All Subscriptions")
        self.assertContains(response, "Switch To Baby")

    def test_subscription_edit_view_not_found(self):
        """
        If search params, should show list of subs and actions
        """
        self.login()
        searchform = {
            "subaction": "find",
            "msisdn": "+2788888888"
        }
        response = self.client.post(
            reverse('controlinterface.views.subscription_edit'), searchform)
        self.assertContains(response, "Subscriber could not be found")

    def test_subscription_cancel_all(self):
        """
        If cancel params, should cancel all and confirm
        """
        self.login()
        cancelform = {
            "subaction": "cancel",
            "msisdn": "+271112"
        }
        activebefore = Subscription.objects.filter(
            to_addr="+271112", active=True).count()
        self.assertEqual(activebefore, 1)
        response = self.client.post(
            reverse('controlinterface.views.subscription_edit'), cancelform)
        self.assertContains(response,
                            "All subscriptions for +271112 "
                            "have been cancelled")
        activeafter = Subscription.objects.filter(
            to_addr="+271112", active=True).count()
        self.assertEqual(activeafter, 0)

    def test_subscription_baby_switch(self):
        """
        If baby params, should show cancel all and sub baby
        """
        self.login()
        babyform = {
            "subaction": "baby",
            "msisdn": "+271112",
            "existing_id": 3
        }
        activebefore = Subscription.objects.filter(
            to_addr="+271112", active=True).count()
        self.assertEqual(activebefore, 1)
        response = self.client.post(
            reverse('controlinterface.views.subscription_edit'), babyform)
        self.assertContains(response,
                            "All active subscriptions for +271112 have been "
                            "cancelled and baby subscription added")
        activeafter = Subscription.objects.filter(
            to_addr="+271112", active=True)
        self.assertEqual(activeafter.count(), 1)
        self.assertEqual(activeafter[0].message_set.short_name, "baby1")
