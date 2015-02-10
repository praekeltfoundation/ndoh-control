from django.test import TestCase, Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from subscription.models import Message


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
        response = self.client.get(reverse('controlinterface.views.message_edit'), follow=True)
        self.assertEqual(response.status_code, 200) 
        self.assertContains(response, "Please, log in to continue.")

    def test_message_search_view(self):
        """
        If no params set yet, should ask for search params
        """
        self.login()
        response = self.client.get(reverse('controlinterface.views.message_edit'))
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
        response = self.client.post(reverse('controlinterface.views.message_edit'), searchform)
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
        response = self.client.post(reverse('controlinterface.views.message_edit'), searchform)
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
        response = self.client.post(reverse('controlinterface.views.message_edit'), editform)
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
        response = self.client.post(reverse('controlinterface.views.message_edit'), confirmform)
        self.assertContains(response, "Message has been updated")
        message = Message.objects.get(pk=1)
        self.assertEqual(message.content, "Message 1 on accelerated now edited")
