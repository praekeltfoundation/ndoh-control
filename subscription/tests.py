"""
Tests for Subscription Application
"""
# Django
from tastypie.test import ResourceTestCase
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from subscription.models import MessageSet, Message, Subscription
from subscription.tasks import (ingest_csv, ensure_one_subscription,
                                vumi_fire_metric, ingest_opt_opts_csv,
                                fire_metrics_active_subscriptions,
                                fire_metrics_all_time_subscriptions,
                                fire_metrics_active_langs,
                                fire_metrics_all_time_langs)
from StringIO import StringIO
import json
import logging
from go_http.send import LoggingSender


class SubscriptionResourceTest(ResourceTestCase):

    def setUp(self):
        super(SubscriptionResourceTest, self).setUp()

        # Create a user.
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(
            self.username,
            'testuser@example.com', self.password)
        self.api_key = self.user.api_key.key

    def get_credentials(self):
        return self.create_apikey(self.username, self.api_key)

    def test_get_list_unauthorzied(self):
        self.assertHttpUnauthorized(
            self.api_client.get('/api/v1/subscription/', format='json'))

    def test_api_keys_created(self):
        self.assertEqual(True, self.api_key is not None)

    def test_get_list_json(self):
        resp = self.api_client.get(
            '/api/v1/subscription/',
            format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 1)

    def test_get_filtered_list_json(self):
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

        filter_data = {
            "user_account": json_item['user_account'],
            "to_addr": json_item['to_addr']
        }

        resp = self.api_client.get(
            '/api/v1/subscription/', data=filter_data,
            format='json', authentication=self.get_credentials())
        self.assertValidJSONResponse(resp)

        # Scope out the data for correctness.
        self.assertEqual(len(self.deserialize(resp)['objects']), 1)

    def test_get_filtered_list_denied_json(self):
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

        filter_data = {
            "user_account": json_item['user_account'],
            "to_addr": json_item['to_addr'],
            "lang": "en"
        }

        resp = self.api_client.get(
            '/api/v1/subscription/', data=filter_data,
            format='json', authentication=self.get_credentials())
        json_item = json.loads(resp.content)
        self.assertHttpBadRequest(resp)
        self.assertEqual(
            "The 'lang' field does not allow filtering.", json_item["error"])

    def test_post_subscription_with_non_existent_schedule_ref(self):
        data = {
            "active": True,
            "completed": False,
            "contact_key": "82309423098",
            "lang": "en",
            "next_sequence_number": 1,
            "resource_uri": "/api/v1/subscription/1/",
            "schedule": "/api/v1/periodic_task/99/",  # Non existent task
            "to_addr": "+271234",
            "user_account": "80493284823"
        }

        response = self.api_client.post('/api/v1/subscription/', format='json',
                                        authentication=self.get_credentials(),
                                        data=data)
        json_item = json.loads(response.content)
        self.assertHttpBadRequest(response)
        self.assertEqual(
            ("Could not find the provided object via resource URI "
             "'/api/v1/periodic_task/99/'."), json_item["error"])

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


class TestUploadCSV(TestCase):

    MSG_HEADER = (
        "message_id,en,safe,af,safe,zu,safe,xh,safe,ve,safe,tn,safe,ts,safe,"
        "ss,safe,st,safe,nso,safe,nr,safe\r\n")
    MSG_LINE_CLEAN_1 = (
        "1,hello,0,hello1,0,hell2,0,,0,,0,,0,,0,,0,,0,,0,hello3,0\r\n")
    MSG_LINE_CLEAN_2 = (
        "2,goodbye,0,goodbye1,0,goodbye2,0,,0,,0,,0,,0,,0,,0,,0,"
        "goodbye3,0\r\n")
    MSG_LINE_DIRTY_1 = (
        "A,sequence_number_is_text,0,goodbye1,0,goodbye2,0,,0,,0,,0,,0,,0,,"
        "0,,0,goodbye3,0\r\n")

    def setUp(self):
        self.admin = User.objects.create_superuser(
            'test', 'test@example.com', "pass123")

    def test_upload_view_not_logged_in_blocked(self):
        response = self.client.get(reverse("csv_uploader"))
        self.assertEqual(response.template_name, "admin/login.html")

    def test_upload_view_logged_in(self):
        self.client.login(username="test", password="pass123")

        response = self.client.get(reverse("csv_uploader"))
        self.assertIn("Upload CSV", response.content)

    def test_upload_csv_clean(self):
        message_set = MessageSet.objects.get(short_name="standard")
        clean_sample = self.MSG_HEADER + \
            self.MSG_LINE_CLEAN_1 + self.MSG_LINE_CLEAN_2
        uploaded = StringIO(clean_sample)
        ingest_csv(uploaded, message_set)
        imported_en = Message.objects.filter(sequence_number="1", lang="en")[0]
        self.assertEquals(imported_en.content, "hello")
        imported_af = Message.objects.filter(sequence_number="1", lang="af")[0]
        self.assertEquals(imported_af.content, "hello1")
        imported_nr = Message.objects.filter(sequence_number="1", lang="nr")[0]
        self.assertEquals(imported_nr.content, "hello3")
        imported_en = Message.objects.filter(sequence_number="2", lang="en")[0]
        self.assertEquals(imported_en.content, "goodbye")
        imported_af2 = Message.objects.filter(
            sequence_number="2", lang="af")[0]
        self.assertEquals(imported_af2.content, "goodbye1")
        imported_nr2 = Message.objects.filter(
            sequence_number="2", lang="nr")[0]
        self.assertEquals(imported_nr2.content, "goodbye3")

    def test_upload_csv_dirty(self):
        message_set = MessageSet.objects.get(short_name="standard")
        dirty_sample = self.MSG_HEADER + \
            self.MSG_LINE_CLEAN_1 + self.MSG_LINE_DIRTY_1
        uploaded = StringIO(dirty_sample)
        ingest_csv(uploaded, message_set)
        imported_en = Message.objects.filter(sequence_number="1", lang="en")[0]
        self.assertEquals(imported_en.content, "hello")
        imported_en_dirty = Message.objects.filter(lang="en")
        self.assertEquals(len(imported_en_dirty), 1)


class TestUploadOptOutCSV(TestCase):

    fixtures = ["test_optout.json"]

    CSV_HEADER = ("Address Type, Address, Message ID, Timestamp\r\n")
    CSV_HEADER2 = ("============================================\r\n")
    CSV_LINE_CLEAN_1 = (
        "msisdn, +271234, 9943d8b8d9ba4fd086fceb43ecc6138d, "
        "2014-09-22 12:21:44.901527\r\n")
    CSV_LINE_CLEAN_2 = (
        "msisdn, 271111, 9943d8b8d9ba4fd086fceb43ecc6138d, "
        "2014-09-22 12:21:44.901527\r\n")

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                       CELERY_ALWAYS_EAGER=True,
                       BROKER_BACKEND='memory',)
    def setUp(self):
        self.admin = User.objects.create_superuser(
            'test', 'test@example.com', "pass123")

    def test_upload_view_not_logged_in_blocked(self):
        response = self.client.get(reverse("optout_uploader"))
        self.assertEqual(response.template_name, "admin/login.html")

    def test_upload_view_logged_in(self):
        self.client.login(username="test", password="pass123")

        response = self.client.get(reverse("optout_uploader"))
        self.assertIn("Upload Optouts CSV", response.content)

    def test_upload_csv(self):
        clean_sample = self.CSV_HEADER + self.CSV_HEADER2 + \
            self.CSV_LINE_CLEAN_1 + self.CSV_LINE_CLEAN_2
        uploaded = StringIO(clean_sample)
        active_count = Subscription.objects.filter(active=True).count()
        # one from initial_data - four from test file
        self.assertEquals(active_count, 5)
        results = ingest_opt_opts_csv.delay(uploaded)
        self.assertEqual(results.get(), 4)
        new_active_count = Subscription.objects.filter(active=True).count()
        self.assertEquals(new_active_count, 1)


class RecordingHandler(logging.Handler):

    """ Record logs. """
    logs = None

    def emit(self, record):
        if self.logs is None:
            self.logs = []
        # print record
        self.logs.append(record)


class TestEnsureCleanSubscriptions(TestCase):

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
        subscriptions = Subscription.objects.all()
        self.assertEqual(len(subscriptions), 4)

    def test_ensure_two_subscriptions(self):
        results = ensure_one_subscription.delay()
        self.assertEqual(results.get(), 2)

    def test_fire_metric(self):
        vumi_fire_metric.delay(
            metric="subscription.duplicates", value=1,
            agg="last", sender=self.sender)
        self.check_logs("Metric: 'subscription.duplicates' [last] -> 1")


class TestFireSummaryMetrics(TestCase):

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

    def check_logs(self, msg):
        if type(self.handler.logs) != list:
            [logs] = self.handler.logs
        else:
            logs = self.handler.logs
        for log in logs:
            if log.msg == msg:
                return True
        return False

    def test_ensure_two_subscriptions(self):
        results = ensure_one_subscription.delay()
        self.assertEqual(results.get(), 2)

    def test_active_subscriptions_metric(self):
        results = fire_metrics_active_subscriptions.delay(sender=self.sender)
        self.assertEqual(results.get(), 2)
        self.assertEqual(True, self.check_logs(
            "Metric: u'prd.subscriptions.baby2.active' [last] -> 1"))
        self.assertEqual(True, self.check_logs(
            "Metric: u'prd.subscriptions.accelerated.active' [last] -> 1"))
        self.assertEqual(True, self.check_logs(
            "Metric: 'prd.subscriptions.active' [last] -> 2"))

    def test_all_time_subscriptions_metric(self):
        results = fire_metrics_all_time_subscriptions.delay(sender=self.sender)
        self.assertEqual(results.get(), 2)
        self.assertEqual(True, self.check_logs(
            "Metric: u'prd.subscriptions.baby2.alltime' [last] -> 1"))
        self.assertEqual(True, self.check_logs(
            "Metric: u'prd.subscriptions.accelerated.alltime' [last] -> 1"))
        self.assertEqual(True, self.check_logs(
            "Metric: 'prd.subscriptions.alltime' [last] -> 2"))

    def test_active_langs_metric(self):
        results = fire_metrics_active_langs.delay(sender=self.sender)
        self.assertEqual(results.get(), 2)
        self.assertEqual(True, self.check_logs(
            "Metric: u'prd.subscriptions.en.active' [last] -> 1"))
        self.assertEqual(True, self.check_logs(
            "Metric: u'prd.subscriptions.af.active' [last] -> 1"))

    def test_all_time_langs_metric(self):
        results = fire_metrics_all_time_langs.delay(sender=self.sender)
        self.assertEqual(results.get(), 2)
        self.assertEqual(True, self.check_logs(
            "Metric: u'prd.subscriptions.af.alltime' [last] -> 1"))
        self.assertEqual(True, self.check_logs(
            "Metric: u'prd.subscriptions.en.alltime' [last] -> 1"))


class TestSetSeqCommand(TestCase):

    def setUp(self):
        pass

    def test_due_date_calc(self):
        pass
        # https://gist.github.com/imsickofmaps/236129fbe7da6300629b
        # https://gist.github.com/imsickofmaps/b9712fde824853d00da3
