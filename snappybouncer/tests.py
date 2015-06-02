"""
Tests for Service Rating Application
"""
from tastypie.test import ResourceTestCase
from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core import management
from snappybouncer.models import (
    Conversation, UserAccount, Ticket, fire_snappy_if_new)
from snappybouncer.tasks import (send_helpdesk_response_jembi,
                                 build_jembi_helpdesk_json)
import json
import responses


class SnappyBouncerResourceTest(ResourceTestCase):
    # fixtures = ["test_snappybouncer.json"]

    def _replace_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(Ticket)
        assert has_listeners(), (
            "Ticket model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(fire_snappy_if_new,
                             sender=Ticket)
        assert not has_listeners(), (
            "Ticket model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(Ticket)
        assert not has_listeners(), (
            "Ticket model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests.")
        post_save.connect(
            fire_snappy_if_new,
            sender=Ticket)

    def setUp(self):
        super(SnappyBouncerResourceTest, self).setUp()
        self._replace_post_save_hooks()
        management.call_command(
            'loaddata', 'test_snappybouncer.json', verbosity=0)

        # Create a user.
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(
            self.username,
            'testuser@example.com', self.password)
        self.api_key = self.user.api_key.key

    def tearDown(self):
        self._restore_post_save_hooks()

    def get_credentials(self):
        return self.create_apikey(self.username, self.api_key)

    def test_data_loaded(self):
        useraccounts = UserAccount.objects.all()
        self.assertEqual(useraccounts.count(), 1)
        conversations = Conversation.objects.all()
        self.assertEqual(conversations.count(), 1)

        tickets = Ticket.objects.all()
        self.assertEqual(tickets.count(), 5)

    def test_get_list_unauthorzied(self):
        self.assertHttpUnauthorized(
            self.api_client.get('/api/v1/snappybouncer/useraccount/',
                                format='json'))

    def test_api_keys_created(self):
        self.assertEqual(True, self.api_key is not None)

    def test_get_useraccount_list_json(self):
        resp = self.api_client.get(
            '/api/v1/snappybouncer/useraccount/',
            format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 1)

    def test_get_useraccount_filtered_list_json(self):
        filter_data = {
            "key": "useraccountkey"
        }

        resp = self.api_client.get(
            '/api/v1/snappybouncer/useraccount/', data=filter_data,
            format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 1)

    def test_get_useraccount_filtered_list_denied_json(self):
        filter_data = {
            "name": "useraccountkey"
        }

        resp = self.api_client.get(
            '/api/v1/snappybouncer/useraccount/', data=filter_data,
            format='json', authentication=self.get_credentials())
        json_item = json.loads(resp.content)
        self.assertHttpBadRequest(resp)
        self.assertEqual(
            "The 'name' field does not allow filtering.", json_item["error"])

    def test_post_ticket_good(self):
        data = {
            "contact_key": "dummycontactkey2",
            "conversation": "/api/v1/snappybouncer/conversation/1/",
            "msisdn": "+271234",
            "message": "New item to send to snappy"
        }

        response = self.api_client.post(
            '/api/v1/snappybouncer/ticket/', format='json',
            authentication=self.get_credentials(),
            data=data)
        json_item = json.loads(response.content)
        self.assertEqual("dummycontactkey2", json_item["contact_key"])
        self.assertEqual(
            "/api/v1/snappybouncer/conversation/1/", json_item["conversation"])
        self.assertEqual("+271234", json_item["msisdn"])
        self.assertEqual(
            "/api/v1/snappybouncer/ticket/6/", json_item["resource_uri"])

    def test_post_ticket_bad_conversation(self):
        data = {
            "contact_key": "dummycontactkey2",
            "conversation": "/api/v1/snappybouncer/conversation/2/",
            "msisdn": "+271234",
            "message": "New item to send to snappy"
        }

        response = self.api_client.post(
            '/api/v1/snappybouncer/ticket/', format='json',
            authentication=self.get_credentials(),
            data=data)
        self.assertHttpBadRequest(response)


class JembiSubmissionTest(TestCase):
    # fixtures = ["test_snappybouncer.json"]

    def _replace_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(Ticket)
        assert has_listeners(), (
            "Ticket model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(fire_snappy_if_new,
                             sender=Ticket)
        assert not has_listeners(), (
            "Ticket model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(Ticket)
        assert not has_listeners(), (
            "Ticket model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests.")
        post_save.connect(
            fire_snappy_if_new,
            sender=Ticket)

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                       CELERY_ALWAYS_EAGER=True,
                       BROKER_BACKEND='memory',)
    def setUp(self):
        super(JembiSubmissionTest, self).setUp()
        self._replace_post_save_hooks()
        self.conversation = self.mk_convo()

    def mk_user_account(self):
        ua = UserAccount()
        ua.key = "fakeuakey"
        ua.name = "Fake UserAccount"
        ua.save()
        return ua

    def mk_convo(self):
        convo = Conversation()
        convo.user_account = self.mk_user_account()
        convo.key = "fakeconvokey"
        convo.name = "Fake Conversation"
        convo.save()
        return convo

    def mk_ticket(self, support_nonce, support_id, message, response):
        ticket = Ticket()
        ticket.conversation = self.conversation
        ticket.support_nonce = support_nonce
        ticket.support_id = support_id
        ticket.message = message
        ticket.response = response
        ticket.contact_key = "fakekey"
        ticket.msisdn = "+27123"
        ticket.save()
        return ticket

    def tearDown(self):
        self._restore_post_save_hooks()

    @responses.activate
    def test_generate_jembi_json(self):
        ticket = self.mk_ticket("supportnonce", 100,
                                "Inbound Message", "Outbound Response")
        tags = ["@tester", "#compliment"]
        responses.add(responses.GET,
                      "http://go.vumi.org/api/v1/go/contacts/fakekey",
                      json.dumps({"extra": {"clinic_code": "123456"}}),
                      status=200, content_type='application/json')

        jembi_post = build_jembi_helpdesk_json(ticket, tags, 2)
        self.assertEqual(jembi_post["dmsisdn"], "+27123")
        self.assertEqual(jembi_post["cmsisdn"], "+27123")
        self.assertEqual(jembi_post["data"]["question"], "Inbound Message")
        self.assertEqual(jembi_post["data"]["answer"], "Outbound Response")
        self.assertEqual(jembi_post["class"], "compliment")
        self.assertEqual(jembi_post["op"], "2")
        self.assertEqual(jembi_post["faccode"], "123456")
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[
            0].request.url,
            "http://go.vumi.org/api/v1/go/contacts/fakekey")

    @responses.activate
    def test_generate_jembi_post(self):
        ticket = self.mk_ticket("supportnonce1", 101,
                                "In Message Send", "Out Response Send")
        tags = ["@tester", "#compliment"]

        responses.add(responses.POST,
                      "http://npr-staging.jembi.org:5001/ws/rest/v1/helpdesk",
                      body='Request added to queue', status=202,
                      content_type='application/json')
        responses.add(responses.GET,
                      "http://go.vumi.org/api/v1/go/contacts/fakekey",
                      json.dumps({"extra": {"clinic_code": "123456"}}),
                      status=200, content_type='application/json')

        resp = send_helpdesk_response_jembi.delay(ticket, tags, 2)

        self.assertEqual(resp.get(), "Request added to queue")

        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(
            responses.calls[1].request.url,
            'http://npr-staging.jembi.org:5001/ws/rest/v1/helpdesk')
        self.assertEqual(responses.calls[1].response.text,
                         'Request added to queue')
