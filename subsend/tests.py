""" Tests for subsend.tasks. """

import json
import logging
import responses
import control.settings as settings
from django.test import TestCase
from django.test.utils import override_settings

from requests_testadapter import TestAdapter, TestSession
from requests.exceptions import HTTPError
from go_http.exceptions import UserOptedOutException

from go_http.send import HttpApiSender, LoggingSender
from subsend.tasks import (process_message_queue, processes_message,
                           vumi_fire_metric, send_message)
from subscription.models import Subscription, MessageSet
from djcelery.models import PeriodicTask


class TestMessageQueueProcessor(TestCase):
    fixtures = ["test_initialdata.json", "test_subsend.json"]

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
        messagesets = MessageSet.objects.all()
        self.assertEqual(len(messagesets), 11)
        subscriptions = Subscription.objects.all()
        self.assertEqual(len(subscriptions), 6)
        schedules = PeriodicTask.objects.all()
        self.assertEqual(len(schedules), 10)

        subscription_momconnect = Subscription.objects.get(id=1)
        self.assertEqual(subscription_momconnect.message_set.conversation_key,
                         "replaceme_momconnect")
        message_set_nurseconnect = MessageSet.objects.get(id=11)
        self.assertEqual(message_set_nurseconnect.conversation_key,
                         "replaceme_nurseconnect")

    def test_multisend(self):
        schedule = 6
        result = process_message_queue.delay(schedule, self.sender)
        self.assertEquals(result.get(), 2)
        self.assertEqual(
            self.handler.logs[2].msg,
            "Metric: 'prd.sum.sms.subscription.outbound' [sum] -> 2")

    def test_multisend_none(self):
        schedule = 2
        result = process_message_queue.delay(schedule, self.sender)
        self.assertEquals(result.get(), 0)

    def test_send_message_1_en_accelerated(self):
        subscriber = Subscription.objects.get(pk=1)
        result = send_message.delay(subscriber, self.sender)
        self.assertEqual(result.get(), {
            "message_id": result.get()["message_id"],
            "to_addr": "+271234",
            "content": "Message 1 on accelerated",
        })

    def test_processes_message_1_en_accelerated(self):
        subscriber = Subscription.objects.get(pk=1)
        result = processes_message.delay(subscriber, self.sender)
        self.assertTrue(result.successful())
        subscriber_updated = Subscription.objects.get(pk=1)
        self.assertEquals(subscriber_updated.next_sequence_number, 2)
        self.assertEquals(subscriber_updated.process_status, 0)

    def test_set_completed_post_send_en_accelerated_2(self):
        subscriber = Subscription.objects.get(pk=1)
        subscriber.next_sequence_number = 2
        subscriber.save()
        result = processes_message.delay(subscriber, self.sender)
        self.assertTrue(result.successful())
        subscriber_updated = Subscription.objects.get(pk=1)
        self.assertEquals(subscriber_updated.completed, True)
        self.assertEquals(subscriber_updated.active, False)

    def test_new_subscription_created_post_send_en_accelerated_2(self):
        twice_a_week = PeriodicTask.objects.get(pk=3)
        subscriber = Subscription.objects.get(pk=1)
        subscriber.next_sequence_number = 2
        subscriber.save()
        result = processes_message.delay(subscriber, self.sender)
        self.assertTrue(result.successful())
        # Check another added and old still there
        all_subscription = Subscription.objects.all()
        self.assertEquals(len(all_subscription), 7)
        # Check new subscription is for baby1
        new_subscription = Subscription.objects.get(pk=101)
        self.assertEquals(new_subscription.message_set.pk, 4)
        self.assertEquals(new_subscription.to_addr, "+271234")
        self.assertEquals(new_subscription.schedule, twice_a_week)
        self.assertEqual(
            self.handler.logs[0].msg,
            "Metric: u'prd.sum.baby1_auto' [sum] -> 1")

    def test_new_subscription_created_post_send_en_baby1(self):
        once_a_week = PeriodicTask.objects.get(pk=2)
        subscriber = Subscription.objects.get(pk=3)
        subscriber.next_sequence_number = 2
        subscriber.save()
        result = processes_message.delay(subscriber, self.sender)
        self.assertTrue(result.successful())
        # Check another added and old still there
        all_subscription = Subscription.objects.all()
        self.assertEquals(len(all_subscription), 7)
        # Check new subscription is for baby2
        new_subscription = Subscription.objects.get(pk=101)
        self.assertEquals(new_subscription.message_set.pk, 5)
        self.assertEquals(new_subscription.to_addr, "+271112")
        self.assertEquals(new_subscription.schedule, once_a_week)

    def test_new_subscription_created_metric_send(self):
        vumi_fire_metric.delay(
            metric="prd.sum.baby1_auto", value=1,
            agg="sum", sender=self.sender)
        self.check_logs("Metric: 'prd.sum.baby1_auto' [sum] -> 1")

    def test_no_new_subscription_created_post_send_en_baby_2(self):
        subscriber = Subscription.objects.get(pk=4)
        result = processes_message.delay(subscriber, self.sender)
        self.assertTrue(result.successful())
        # Check no new subscription added
        all_subscription = Subscription.objects.all()
        self.assertEquals(len(all_subscription), 6)
        # Check old one now inactive and complete
        subscriber_updated = Subscription.objects.get(pk=4)
        self.assertEquals(subscriber_updated.completed, True)
        self.assertEquals(subscriber_updated.active, False)

    def test_send_non_existent_message(self):
        subscriber = Subscription.objects.get(pk=1)
        subscriber.lang = 'fr'
        subscriber.save()
        result = send_message.delay(subscriber, self.sender)
        self.assertTrue(result.successful())
        subscriber_updated = Subscription.objects.get(pk=1)
        self.assertEquals(subscriber_updated.completed, False)
        self.assertEquals(subscriber_updated.active, True)
        self.assertEquals(subscriber_updated.process_status, -1)


class TestMessageFailure(TestCase):
    fixtures = ["test_initialdata.json", "test_subsend.json"]

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                       CELERY_ALWAYS_EAGER=True,
                       BROKER_BACKEND='memory',)
    def setUp(self):
        self.sender = HttpApiSender(
            account_key=settings.VUMI_GO_ACCOUNT_KEY,
            conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
            conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
        )
        self.handler = RecordingHandler()
        logger = logging.getLogger('go_http.test')
        logger.setLevel(logging.INFO)
        logger.addHandler(self.handler)

    def check_logs(self, msg, levelno=logging.INFO):
        [log] = self.handler.logs
        self.assertEqual(log.msg, msg)
        self.assertEqual(log.levelno, levelno)

    def test_data_loaded(self):
        messagesets = MessageSet.objects.all()
        self.assertEqual(len(messagesets), 11)
        subscriptions = Subscription.objects.all()
        self.assertEqual(len(subscriptions), 6)
        schedules = PeriodicTask.objects.all()
        self.assertEqual(len(schedules), 10)

    @responses.activate
    def test_subscriber_opted_out_error(self):
        subscriber = Subscription.objects.get(pk=1)
        exception = UserOptedOutException(subscriber.to_addr,
                                          "Message 1 on accelerated",
                                          "response reason")
        responses.add(responses.PUT,
                      "http://go.vumi.org/api/v1/go/http_api_nostream/"
                      "replaceme/messages.json",
                      content_type='application/json;charset=utf-8',
                      body=exception)
        result = send_message.delay(subscriber, self.sender)
        self.assertEquals(len(responses.calls), 1)
        self.assertEquals(result.get(),
                          u'Subscription deactivated for +271234')

    @responses.activate
    def test_subscriber_three_retries_on_500(self):
        subscriber = Subscription.objects.get(pk=1)
        responses.add(responses.PUT,
                      "http://go.vumi.org/api/v1/go/http_api_nostream/"
                      "replaceme/messages.json",
                      content_type='application/json;charset=utf-8',
                      status=577, body='{"error": "problems"}')
        result = send_message.delay(subscriber, self.sender)
        self.assertEqual(len(responses.calls), 4)

        with self.assertRaises(HTTPError) as cm:
            result.get()
        self.assertEqual(cm.exception.response.status_code, 577)

    @responses.activate
    def test_subscriber_other_httperror_code(self):
        subscriber = Subscription.objects.get(pk=1)
        responses.add(responses.PUT,
                      "http://go.vumi.org/api/v1/go/http_api_nostream/"
                      "replaceme/messages.json",
                      content_type='application/json;charset=utf-8',
                      status=405, body='{"error": "problems"}')
        result = send_message.delay(subscriber, self.sender)
        self.assertEqual(len(responses.calls), 1)

        with self.assertRaises(HTTPError) as cm:
            result.get()
        self.assertEqual(cm.exception.response.status_code, 405)


class RecordingAdapter(TestAdapter):

    """ Record the request that was handled by the adapter.
    """
    request = None

    def send(self, request, *args, **kw):
        self.request = request
        return super(RecordingAdapter, self).send(request, *args, **kw)


class TestHttpApiSender(TestCase):

    def setUp(self):
        self.session = TestSession()
        self.sender = HttpApiSender(
            account_key="acc-key", conversation_key="conv-key",
            api_url="http://example.com/api/v1/go/http_api_nostream",
            conversation_token="conv-token", session=self.session)

    def test_default_session(self):
        import requests
        sender = HttpApiSender(
            account_key="acc-key", conversation_key="conv-key",
            conversation_token="conv-token")
        self.assertTrue(isinstance(sender.session, requests.Session))

    def test_default_api_url(self):
        sender = HttpApiSender(
            account_key="acc-key", conversation_key="conv-key",
            conversation_token="conv-token")
        self.assertEqual(sender.api_url,
                         "http://go.vumi.org/api/v1/go/http_api_nostream")

    def check_request(self, request, method, data=None, headers=None):
        self.assertEqual(request.method, method)
        if data is not None:
            self.assertEqual(json.loads(request.body), data)
        if headers is not None:
            for key, value in headers.items():
                self.assertEqual(request.headers[key], value)

    def test_send_text(self):
        adapter = RecordingAdapter(json.dumps({"message_id": "id-1"}))
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "messages.json", adapter)

        result = self.sender.send_text("to-addr-1", "Hello!")
        self.assertEqual(result, {
            "message_id": "id-1",
        })
        self.check_request(
            adapter.request, 'PUT',
            data={"content": "Hello!", "to_addr": "to-addr-1"},
            headers={"Authorization": u'Basic YWNjLWtleTpjb252LXRva2Vu'})

    def test_fire_metric(self):
        adapter = RecordingAdapter(
            json.dumps({"success": True, "reason": "Yay"}))
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "metrics.json", adapter)

        result = self.sender.fire_metric("metric-1", 5.1, agg="max")
        self.assertEqual(result, {
            "success": True,
            "reason": "Yay",
        })
        self.check_request(
            adapter.request, 'PUT',
            data=[["metric-1", 5.1, "max"]],
            headers={"Authorization": u'Basic YWNjLWtleTpjb252LXRva2Vu'})

    def test_fire_metric_default_agg(self):
        adapter = RecordingAdapter(
            json.dumps({"success": True, "reason": "Yay"}))
        self.session.mount(
            "http://example.com/api/v1/go/http_api_nostream/conv-key/"
            "metrics.json", adapter)

        result = self.sender.fire_metric("metric-1", 5.2)
        self.assertEqual(result, {
            "success": True,
            "reason": "Yay",
        })
        self.check_request(
            adapter.request, 'PUT',
            data=[["metric-1", 5.2, "last"]],
            headers={"Authorization": u'Basic YWNjLWtleTpjb252LXRva2Vu'})


class RecordingHandler(logging.Handler):

    """ Record logs. """
    logs = None

    def emit(self, record):
        if self.logs is None:
            self.logs = []
        self.logs.append(record)


class TestLoggingSender(TestCase):

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

    def test_send_text(self):
        result = self.sender.send_text("to-addr-1", "Hello!")
        self.assertEqual(result, {
            "message_id": result["message_id"],
            "to_addr": "to-addr-1",
            "content": "Hello!",
        })
        self.check_logs("Message: 'Hello!' sent to 'to-addr-1'")

    def test_fire_metric(self):
        result = self.sender.fire_metric("metric-1", 5.1, agg="max")
        self.assertEqual(result, {
            "success": True,
            "reason": "Metrics published",
        })
        self.check_logs("Metric: 'metric-1' [max] -> 5.1")

    def test_fire_metric_default_agg(self):
        result = self.sender.fire_metric("metric-1", 5.2)
        self.assertEqual(result, {
            "success": True,
            "reason": "Metrics published",
        })
        self.check_logs("Metric: 'metric-1' [last] -> 5.2")
