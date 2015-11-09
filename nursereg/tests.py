import json
import responses
import logging
from datetime import datetime
from django.contrib.auth.models import User
from django.test import TestCase
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status
from requests.adapters import HTTPAdapter
from requests_testadapter import TestSession, Resp
from requests.exceptions import HTTPError
from go_http.contacts import ContactsApiClient
from go_http.send import LoggingSender
from fake_go_contacts import Request, FakeContactsApi
from .models import NurseReg, NurseSource, fire_jembi_post
from subscription.models import Subscription
from nursereg import tasks


def override_get_today():
    return datetime.strptime("20130819144811", "%Y%m%d%H%M%S")


def override_get_tomorrow():
    return "2013-08-20"


def override_get_sender():
    return LoggingSender('go_http.test')


TEST_REG_DATA = {
    "sa_id": {
        "msisdn": "+27001",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "8009151234001",
        "dob": "1980-09-15",
        # "passport_origin": None,
        # "nurse_source": None,
        # "persal_no": 12345678,
        # "opted_out": None,
        # "optout_reason": None,
        # "optout_count": None,
        # "sanc_reg_no": None,
    },
    # "clinic_hcw": {
    #     "hcw_msisdn": "+27820010001",
    #     "mom_msisdn": "+27001",
    #     "mom_id_type": "passport",
    #     "mom_passport_origin": "zw",
    #     "mom_lang": "af",
    #     "mom_edd": "2015-09-01",
    #     "mom_id_no": "5551111",
    #     "mom_dob": None,
    #     "clinic_code": "12345",
    #     "authority": "clinic"
    # },
    # "chw_self": {
    #     "hcw_msisdn": None,
    #     "mom_msisdn": "+27002",
    #     "mom_id_type": "none",
    #     "mom_passport_origin": None,
    #     "mom_lang": "xh",
    #     "mom_edd": None,
    #     "mom_id_no": None,
    #     "mom_dob": "1980-10-15",
    #     "clinic_code": None,
    #     "authority": "chw"
    # },
    # "chw_hcw": {
    #     "hcw_msisdn": "+27820020002",
    #     "mom_msisdn": "+27002",
    #     "mom_id_type": "sa_id",
    #     "mom_passport_origin": None,
    #     "mom_lang": "zu",
    #     "mom_edd": None,
    #     "mom_id_no": "8011151234001",
    #     "mom_dob": "1980-11-15",
    #     "clinic_code": None,
    #     "authority": "chw"
    # },
    # "personal_detailed": {
    #     "hcw_msisdn": None,
    #     "mom_msisdn": "+27003",
    #     "mom_id_type": "passport",
    #     "mom_passport_origin": "mz",
    #     "mom_lang": "st",
    #     "mom_edd": None,
    #     "mom_id_no": "5552222",
    #     "mom_dob": None,
    #     "clinic_code": None,
    #     "authority": "personal"
    # },
    # "personal_simple": {
    #     "hcw_msisdn": None,
    #     "mom_msisdn": "+27004",
    #     "mom_id_type": "none",
    #     "mom_passport_origin": None,
    #     "mom_lang": "ss",
    #     "mom_edd": None,
    #     "mom_id_no": None,
    #     "mom_dob": None,
    #     "clinic_code": None,
    #     "authority": "personal"
    # }
}
TEST_NURSE_SOURCE_DATA = {
    "name": "Test Nurse Source"
}
TEST_REG_DATA_BROKEN = {
    # single field null-violation test
    "no_msisdn": {
        "msisdn": None,
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "8009151234001",
        "dob": "1980-09-15",
    },
    # data below is for combination validation testing
    "sa_id_no_id_no": {
        "msisdn": "+27001",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": None,
        "dob": "1980-09-15"
    },
    "passport_no_id_no": {
        "msisdn": "+27001",
        "faccode": "123456",
        "id_type": "passport",
        "id_no": None,
        "dob": "1980-09-15"
    },
    "no_passport_origin": {
        "msisdn": "+27001",
        "faccode": "123456",
        "id_type": "passport",
        "id_no": "SA12345",
        "dob": "1980-09-15"
    },
    "no_optout_reason": {
        "msisdn": "+27001",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "8009151234001",
        "dob": "1980-09-15",
        # "passport_origin": None,
        # "nurse_source": None,
        # "persal_no": 12345678,
        "opted_out": True,
        "optout_reason": None,
        "optout_count": 1,
        # "sanc_reg_no": None,
    },
    "zero_optout_count": {
        "msisdn": "+27001",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "8009151234001",
        "dob": "1980-09-15",
        # "passport_origin": None,
        # "nurse_source": None,
        # "persal_no": 12345678,
        "opted_out": True,
        "optout_reason": "job_change",
        "optout_count": 0,
        # "sanc_reg_no": None,
    },
}
TEST_CONTACT_DATA = {
    u"key": u"knownuuid",
    u"msisdn": u"+155564",
    u"user_account": u"knownaccount",
    u"extra": {
        u"an_extra": u"1"
    }
}
API_URL = "http://example.com/go"
AUTH_TOKEN = "auth_token"
MAX_CONTACTS_PER_PAGE = 10


class RecordingHandler(logging.Handler):
    """ Record logs. """
    logs = None

    def emit(self, record):
        if self.logs is None:
            self.logs = []
        self.logs.append(record)


class APITestCase(TestCase):

    def setUp(self):
        self.adminclient = APIClient()
        self.normalclient = APIClient()
        self.sender = LoggingSender('go_http.test')
        self.handler = RecordingHandler()
        logger = logging.getLogger('go_http.test')
        logger.setLevel(logging.INFO)
        logger.addHandler(self.handler)

        tasks.get_today = override_get_today
        tasks.get_tomorrow = override_get_tomorrow
        tasks.get_sender = override_get_sender


class FakeContactsApiAdapter(HTTPAdapter):

    """
    Adapter for FakeContactsApi.

    This inherits directly from HTTPAdapter instead of using TestAdapter
    because it overrides everything TestAdaptor does.
    """

    def __init__(self, contacts_api):
        self.contacts_api = contacts_api
        super(FakeContactsApiAdapter, self).__init__()

    def send(self, request, stream=False, timeout=None, verify=True,
             cert=None, proxies=None):
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


class TestNurseRegHelperFunctions(TestCase):

    def test_get_tomorrow(self):
        tasks.get_today = override_get_today
        self.assertEqual(tasks.get_tomorrow(), '2013-08-20')


class AuthenticatedAPITestCase(APITestCase):

    def _replace_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(NurseReg)
        assert has_listeners(), (
            "NurseReg model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(fire_jembi_post, sender=NurseReg)
        assert not has_listeners(), (
            "NurseReg model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(NurseReg)
        assert not has_listeners(), (
            "NurseReg model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests.")
        post_save.connect(fire_jembi_post, sender=NurseReg)

    def make_nursesource(self, post_data=TEST_NURSE_SOURCE_DATA):
        # Make source for the normal user who submits data but using admin user
        user = User.objects.get(username='testnormaluser')
        post_data["user"] = "/api/v2/users/%s/" % user.id

        response = self.adminclient.post('/api/v2/nursesources/',
                                         json.dumps(post_data),
                                         content_type='application/json')
        return response

    def make_nursereg(self, post_data):
        response = self.normalclient.post('/api/v2/nurseregs/',
                                          json.dumps(post_data),
                                          content_type='application/json')
        return response

    def make_client(self):
        return ContactsApiClient(auth_token=AUTH_TOKEN, api_url=API_URL,
                                 session=self.session)

    def override_get_client(self):
            return self.make_client()

    def make_existing_contact(self, contact_data=TEST_CONTACT_DATA):
        # TODO CHANGE EXTRAS
        existing_contact = make_contact_dict(contact_data)
        self.contacts_data[existing_contact[u"key"]] = existing_contact
        return existing_contact

    def setUp(self):
        super(AuthenticatedAPITestCase, self).setUp()
        self._replace_post_save_hooks()

        # adminclient setup
        self.adminusername = 'testadminuser'
        self.adminpassword = 'testadminpass'
        self.adminuser = User.objects.create_superuser(
            self.adminusername,
            'testadminuser@example.com',
            self.adminpassword)
        admintoken = Token.objects.create(user=self.adminuser)
        self.admintoken = admintoken.key
        self.adminclient.credentials(
            HTTP_AUTHORIZATION='Token ' + self.admintoken)

        # normalclient setup
        self.normalusername = 'testnormaluser'
        self.normalpassword = 'testnormalpass'
        self.normaluser = User.objects.create_user(
            self.normalusername,
            'testnormaluser@example.com',
            self.normalpassword)
        normaltoken = Token.objects.create(user=self.normaluser)
        self.normaltoken = normaltoken.key
        self.normalclient.credentials(
            HTTP_AUTHORIZATION='Token ' + self.normaltoken)
        self.make_nursesource()

        # contacts client setup
        self.contacts_data = {}
        self.groups_data = {}
        self.contacts_backend = FakeContactsApi(
            "go/", AUTH_TOKEN, self.contacts_data, self.groups_data,
            contacts_limit=MAX_CONTACTS_PER_PAGE)
        self.session = TestSession()
        adapter = FakeContactsApiAdapter(self.contacts_backend)
        self.session.mount(API_URL, adapter)

    def tearDown(self):
        self._restore_post_save_hooks()

    def check_logs(self, msg):
        if type(self.handler.logs) != list:
            logs = [self.handler.logs]
        else:
            logs = self.handler.logs
        for log in logs:
            if log.msg == msg:
                return True
        return False

    def check_logs_number_of_entries(self):
        if type(self.handler.logs) != list:
            logs = [self.handler.logs]
        else:
            logs = self.handler.logs
        return len(logs)


class TestContactsAPI(AuthenticatedAPITestCase):

    def test_get_contact_by_key(self):
        client = self.make_client()
        existing_contact = self.make_existing_contact()
        contact = client.get_contact(u"knownuuid")
        self.assertEqual(contact, existing_contact)

    def test_get_contact_by_msisdn(self):
        client = self.make_client()
        existing_contact = self.make_existing_contact()
        contact = client.get_contact(msisdn="+155564")
        self.assertEqual(contact, existing_contact)

    def test_update_contact(self):
        client = self.make_client()
        existing_contact = self.make_existing_contact()
        expected_contact = existing_contact.copy()
        expected_contact[u"name"] = u"Bob"
        updated_contact = client.update_contact(
            u"knownuuid", {u"name": u"Bob"})

        self.assertEqual(updated_contact, expected_contact)

    def test_update_contact_extras(self):
        client = self.make_client()
        existing_contact = self.make_existing_contact()
        expected_contact = existing_contact.copy()
        expected_contact[u"extra"][u"an_extra"] = u"2"
        updated_contact = client.update_contact(
            u"knownuuid", {
                # Note the whole extra dict needs passing in
                u"extra": {
                    u"an_extra": u"2"
                }
            }
        )
        self.assertEqual(updated_contact, expected_contact)

    def test_create_contact(self):
        client = self.make_client()
        created_contact = client.create_contact({
            u"msisdn": "+111",
            u"groups": ['en'],
            u"extra": {
                u'clinic_code': u'12345',
                u'dob': '1980-09-15',
                u'due_date_day': '01',
                u'due_date_month': '08',
                u'due_date_year': '2015',
                u'edd': '2015-08-01',
                u'is_registered': 'true',
                u'is_registered_by': u'clinic',
                u'language_choice': u'en',
                u'last_service_rating': 'never',
                u'sa_id': u'8009151234001',
                u'service_rating_reminder': "2013-08-20",
                u'service_rating_reminders': '0',
                u'source_name': u'Test Source'
            }
        })
        self.assertEqual(created_contact["msisdn"], "+111")
        self.assertIsNotNone(created_contact["key"])

    def test_get_group_by_key(self):
        client = self.make_client()
        existing_group = client.create_group({
            "name": 'groupname'
            })
        group = client.get_group(existing_group[u'key'])
        self.assertEqual(group, existing_group)


class TestNurseRegAPI(AuthenticatedAPITestCase):

    def test_create_nursesource_deny_normaluser(self):
        # Setup
        user = User.objects.get(username='testnormaluser')
        post_data = TEST_NURSE_SOURCE_DATA
        post_data["user"] = "/api/v2/users/%s/" % user.id
        # Execute
        response = self.normalclient.post('/api/v2/nursesources/',
                                          json.dumps(post_data),
                                          content_type='application/json')
        # Check
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_nursereg(self):
        # Setup
        last_nurse_source = NurseSource.objects.last()
        # Execute
        reg_response = self.make_nursereg(
            post_data=TEST_REG_DATA["sa_id"])
        # Check
        self.assertEqual(reg_response.status_code, status.HTTP_201_CREATED)
        d = NurseReg.objects.last()
        self.assertEqual(d.msisdn, '+27001')
        self.assertEqual(d.faccode, '123456')
        self.assertEqual(d.id_type, 'sa_id')
        self.assertEqual(d.id_no, '8009151234001')
        self.assertEqual(d.dob.strftime("%Y-%m-%d"), "1980-09-15")
        self.assertEqual(d.nurse_source, last_nurse_source)
        self.assertEqual(d.passport_origin, None)
        self.assertEqual(d.persal_no, None)
        self.assertEqual(d.opted_out, False)
        self.assertEqual(d.optout_reason, None)
        self.assertEqual(d.optout_count, 0)
        self.assertEqual(d.sanc_reg_no, None)

    def test_create_broken_nursereg_no_msisdn(self):
        # Setup
        # Execute
        reg_response = self.make_nursereg(
            post_data=TEST_REG_DATA_BROKEN["no_msisdn"])
        # Check
        self.assertEqual(reg_response.status_code, status.HTTP_400_BAD_REQUEST)
        d = NurseReg.objects.last()
        self.assertEqual(d, None)

    def test_create_broken_registration_sa_id_no_id_no(self):
        # Setup
        # Execute
        # Check
        self.assertRaises(ValidationError, lambda: self.make_nursereg(
            post_data=TEST_REG_DATA_BROKEN["sa_id_no_id_no"]))
        d = NurseReg.objects.last()
        self.assertEqual(d, None)

    def test_create_broken_registration_no_passport_no(self):
        # Setup
        # Execute
        # Check
        self.assertRaises(ValidationError, lambda: self.make_nursereg(
            post_data=TEST_REG_DATA_BROKEN["passport_no_id_no"]))
        d = NurseReg.objects.last()
        self.assertEqual(d, None)

    def test_create_broken_registration_no_passport_origin(self):
        # Setup
        # Execute
        # Check
        self.assertRaises(ValidationError, lambda: self.make_nursereg(
            post_data=TEST_REG_DATA_BROKEN["no_passport_origin"]))
        d = NurseReg.objects.last()
        self.assertEqual(d, None)

    def test_create_broken_no_optout_reason(self):
        # Setup
        # Execute
        # Check
        self.assertRaises(ValidationError, lambda: self.make_nursereg(
            post_data=TEST_REG_DATA_BROKEN["no_optout_reason"]))
        d = NurseReg.objects.last()
        self.assertEqual(d, None)

    def test_create_broken_zero_optout_count(self):
        # Setup
        # Execute
        # Check
        self.assertRaises(ValidationError, lambda: self.make_nursereg(
            post_data=TEST_REG_DATA_BROKEN["zero_optout_count"]))
        d = NurseReg.objects.last()
        self.assertEqual(d, None)

    def test_fire_metric(self):
        # Setup
        # Execute
        tasks.vumi_fire_metric.apply_async(
            kwargs={
                "metric": "test.metric",
                "value": 1,
                "agg": "sum",
                "sender": self.sender}
            )
        # Check
        self.assertEqual(True,
                         self.check_logs("Metric: 'test.metric' [sum] -> 1"))
        self.assertEqual(1, self.check_logs_number_of_entries())

#     @responses.activate
#     def test_create_registration_fires_tasks(self):
#         # restore the post_save hooks just for this test
#         post_save.connect(fire_jembi_post, sender=Registration)

#         # Check number of subscriptions before task fire
#         self.assertEqual(Subscription.objects.all().count(), 1)

#         # Check there are no pre-existing registration objects
#         self.assertEqual(Registration.objects.all().count(), 0)

#         responses.add(responses.POST,
#                       "http://test/v2/subscription",
#                       body='jembi_post_json task', status=201,
#                       content_type='application/json')
#         responses.add(responses.POST,
#                       "http://test/v2/registration/net.ihe/DocumentDossier",
#                       body="Request added to queue", status=202,
#                       content_type='application/json')

#         # Set up the client
#         tasks.get_client = self.override_get_client

#         # Make a new registration
#         reg_response = self.make_nursereg(
#             post_data=TEST_REG_DATA["clinic_self"])

#         # Test registration object has been created successfully
#         self.assertEqual(reg_response.status_code, status.HTTP_201_CREATED)

#         # Test there is now a registration object in the database
#         d = Registration.objects.all()
#         self.assertEqual(Registration.objects.all().count(), 1)

#         # Test the registration object is the one you added
#         d = Registration.objects.last()
#         self.assertEqual(d.mom_id_type, 'sa_id')

#         # Test post requests has been made to Jembi
#         self.assertEqual(len(responses.calls), 2)
#         self.assertEqual(
#             responses.calls[0].request.url,
#             "http://test/v2/subscription")
#         self.assertEqual(
#             responses.calls[1].request.url,
#             "http://test/v2/registration/net.ihe/DocumentDossier")

#         # Test number of subscriptions after task fire
#         self.assertEqual(Subscription.objects.all().count(), 2)

#         # Test subscription object is the one you added
#         d = Subscription.objects.last()
#         self.assertEqual(d.to_addr, "+27001")

#         # Test metrics have fired
#         self.assertEqual(True, self.check_logs(
#             "Metric: u'test.clinic.sum.json_to_jembi_success' [sum] -> 1"))
#         self.assertEqual(True, self.check_logs(
#             "Metric: u'test.clinic.sum.doc_to_jembi_success' [sum] -> 1"))
#         self.assertEqual(True, self.check_logs(
#             "Metric: u'test.sum.subscriptions' [sum] -> 1"))
#         self.assertEqual(True, self.check_logs(
#             "Metric: u'test.clinic.sum.subscription_to_protocol_success' " +
#             "[sum] -> 1"))
#         self.assertEqual(4, self.check_logs_number_of_entries())

#         # remove post_save hooks to prevent teardown errors
#         post_save.disconnect(fire_jembi_post, sender=Registration)


# class TestJembiPostJsonTask(AuthenticatedAPITestCase):

#     def test_build_jembi_json_clinic_self(self):
#         registration_clinic_self = self.make_nursereg(
#             post_data=TEST_REG_DATA["clinic_self"])
#         reg = Registration.objects.get(pk=registration_clinic_self.data["id"])
#         expected_json_clinic_self = {
#             'edd': '20150801',
#             'id': '8009151234001^^^ZAF^NI',
#             'lang': 'en',
#             'dob': "19800915",
#             'dmsisdn': '+27001',
#             'mha': 1,
#             'cmsisdn': '+27001',
#             'faccode': '12345',
#             'encdate': '20130819144811',
#             'type': 3,
#             'swt': 1
#         }
#         payload = tasks.build_jembi_json(reg)
#         self.assertEqual(expected_json_clinic_self, payload)

#     def test_build_jembi_json_clinic_hcw(self):
#         registration_clinic_hcw = self.make_nursereg(
#             post_data=TEST_REG_DATA["clinic_hcw"])
#         reg = Registration.objects.get(pk=registration_clinic_hcw.data["id"])
#         expected_json_clinic_hcw = {
#             'edd': '20150901',
#             'id': '5551111^^^ZW^PPN',
#             'lang': 'af',
#             'dob': None,
#             'dmsisdn': "+27820010001",
#             'mha': 1,
#             'cmsisdn': '+27001',
#             'faccode': '12345',
#             'encdate': '20130819144811',
#             'type': 3,
#             'swt': 1
#         }
#         payload = tasks.build_jembi_json(reg)
#         self.assertEqual(expected_json_clinic_hcw, payload)

#     def test_build_jembi_json_chw_self(self):
#         registration_chw_self = self.make_nursereg(
#             post_data=TEST_REG_DATA["chw_self"])
#         reg = Registration.objects.get(pk=registration_chw_self.data["id"])
#         expected_json_chw_self = {
#             'id': '27002^^^ZAF^TEL',
#             'lang': 'xh',
#             'dob': "19801015",
#             'dmsisdn': '+27002',
#             'mha': 1,
#             'cmsisdn': '+27002',
#             'faccode': None,
#             'encdate': '20130819144811',
#             'type': 2,
#             'swt': 1
#         }
#         payload = tasks.build_jembi_json(reg)
#         self.assertEqual(expected_json_chw_self, payload)

#     def test_build_jembi_json_chw_hcw(self):
#         registration_chw_hcw = self.make_nursereg(
#             post_data=TEST_REG_DATA["chw_hcw"])
#         reg = Registration.objects.get(pk=registration_chw_hcw.data["id"])
#         expected_json_chw_hcw = {
#             'id': '8011151234001^^^ZAF^NI',
#             'lang': 'zu',
#             'dob': "19801115",
#             'dmsisdn': "+27820020002",
#             'mha': 1,
#             'cmsisdn': '+27002',
#             'faccode': None,
#             'encdate': '20130819144811',
#             'type': 2,
#             'swt': 1
#         }
#         payload = tasks.build_jembi_json(reg)
#         self.assertEqual(expected_json_chw_hcw, payload)

#     def test_build_jembi_json_personal_detailed(self):
#         registration_personal = self.make_nursereg(
#             post_data=TEST_REG_DATA["personal_detailed"])
#         reg = Registration.objects.get(pk=registration_personal.data["id"])
#         expected_json_personal = {
#             'id': '5552222^^^MZ^PPN',
#             'lang': 'st',
#             'dob': None,
#             'dmsisdn': '+27003',
#             'mha': 1,
#             'cmsisdn': '+27003',
#             'faccode': None,
#             'encdate': '20130819144811',
#             'type': 1,
#             'swt': 1
#         }
#         payload = tasks.build_jembi_json(reg)
#         self.assertEqual(expected_json_personal, payload)

#     def test_build_jembi_json_personal_simple(self):
#         registration_personal = self.make_nursereg(
#             post_data=TEST_REG_DATA["personal_simple"])
#         reg = Registration.objects.get(pk=registration_personal.data["id"])
#         expected_json_personal = {
#             'id': '27004^^^ZAF^TEL',
#             'lang': 'ss',
#             'dob': None,
#             'dmsisdn': '+27004',
#             'mha': 1,
#             'cmsisdn': '+27004',
#             'faccode': None,
#             'encdate': '20130819144811',
#             'type': 1,
#             'swt': 1
#         }
#         payload = tasks.build_jembi_json(reg)
#         self.assertEqual(expected_json_personal, payload)

#     @responses.activate
#     def test_jembi_post_json(self):
#         registration = self.make_nursereg(
#             post_data=TEST_REG_DATA["clinic_self"])

#         responses.add(responses.POST,
#                       "http://test/v2/subscription",
#                       body='jembi_post_json task', status=201,
#                       content_type='application/json')

#         task_response = tasks.jembi_post_json.apply_async(
#             kwargs={"registration_id": registration.data["id"],
#                     "sender": self.sender})
#         self.assertEqual(len(responses.calls), 1)
#         self.assertEqual(task_response.get(), 'jembi_post_json task')
#         self.assertEqual(True, self.check_logs(
#             "Metric: u'test.clinic.sum.json_to_jembi_success' [sum] -> 1"))
#         self.assertEqual(1, self.check_logs_number_of_entries())

#     @responses.activate
#     def test_jembi_post_json_retries(self):
#         registration = self.make_nursereg(
#             post_data=TEST_REG_DATA["clinic_self"])

#         responses.add(responses.POST,
#                       "http://test/v2/subscription",
#                       body='{"error": "jembi json problems"}', status=531,
#                       content_type='application/json')

#         task_response = tasks.jembi_post_json.apply_async(
#             kwargs={"registration_id": registration.data["id"]})
#         self.assertEqual(len(responses.calls), 4)
#         with self.assertRaises(HTTPError) as cm:
#             task_response.get()
#         self.assertEqual(cm.exception.response.status_code, 531)
#         self.assertEqual(True, self.check_logs(
#             "Metric: u'test.clinic.sum.json_to_jembi_fail' [sum] -> 1"))
#         self.assertEqual(1, self.check_logs_number_of_entries())

#     @responses.activate
#     def test_jembi_post_json_other_httperror(self):
#         registration = self.make_nursereg(
#             post_data=TEST_REG_DATA["clinic_self"])

#         responses.add(responses.POST,
#                       "http://test/v2/subscription",
#                       body='{"error": "jembi json problems"}', status=404,
#                       content_type='application/json')

#         task_response = tasks.jembi_post_json.apply_async(
#             kwargs={"registration_id": registration.data["id"]})
#         self.assertEqual(len(responses.calls), 1)
#         with self.assertRaises(HTTPError) as cm:
#             task_response.get()
#         self.assertEqual(cm.exception.response.status_code, 404)
#         self.assertEqual(True, self.check_logs(
#             "Metric: u'test.clinic.sum.json_to_jembi_fail' [sum] -> 1"))
#         self.assertEqual(1, self.check_logs_number_of_entries())


# class TestJembiPostXmlTask(AuthenticatedAPITestCase):

#     def test_get_dob(self):
#         self.make_nursereg(post_data=TEST_REG_DATA["clinic_self"])
#         reg = Registration.objects.last()
#         birth_time = tasks.get_dob(reg.mom_dob)
#         self.assertEqual(birth_time, "19800915")

#         self.make_nursereg(post_data=TEST_REG_DATA["clinic_hcw"])
#         reg = Registration.objects.last()
#         birth_time = tasks.get_dob(reg.mom_dob)
#         self.assertEqual(birth_time, None)

#     @responses.activate
#     def test_jembi_post_xml_retries(self):
#         registration = self.make_nursereg(
#             post_data=TEST_REG_DATA["clinic_self"])

#         responses.add(responses.POST,
#                       "http://test/v2/registration/net.ihe/DocumentDossier",
#                       body='{"error": "jembi xml problems"}', status=531,
#                       content_type='application/json')

#         task_response = tasks.jembi_post_xml.apply_async(
#             kwargs={"registration_id": registration.data["id"]})
#         self.assertEqual(len(responses.calls), 4)
#         with self.assertRaises(HTTPError) as cm:
#             task_response.get()
#         self.assertEqual(cm.exception.response.status_code, 531)
#         self.assertEqual(True, self.check_logs(
#             "Metric: u'test.clinic.sum.doc_to_jembi_fail' [sum] -> 1"))
#         self.assertEqual(1, self.check_logs_number_of_entries())

#     @responses.activate
#     def test_jembi_post_xml_other_httperror(self):
#         registration = self.make_nursereg(
#             post_data=TEST_REG_DATA["clinic_self"])

#         responses.add(responses.POST,
#                       "http://test/v2/registration/net.ihe/DocumentDossier",
#                       body='{"error": "jembi xml problems"}', status=404,
#                       content_type='application/json')

#         task_response = tasks.jembi_post_xml.apply_async(
#             kwargs={"registration_id": registration.data["id"]})
#         self.assertEqual(len(responses.calls), 1)
#         with self.assertRaises(HTTPError) as cm:
#             task_response.get()
#         self.assertEqual(cm.exception.response.status_code, 404)
#         self.assertEqual(True, self.check_logs(
#             "Metric: u'test.clinic.sum.doc_to_jembi_fail' [sum] -> 1"))
#         self.assertEqual(1, self.check_logs_number_of_entries())


# class TestUpdateCreateVumiContactTask(AuthenticatedAPITestCase):

#     def test_week_calc(self):
#         weeks = tasks.get_pregnancy_week(datetime(2014, 7, 13), "2014-07-14")
#         self.assertEqual(weeks, 40)
#         weeks = tasks.get_pregnancy_week(datetime(2014, 7, 6), "2014-07-14")
#         self.assertEqual(weeks, 39)
#         weeks = tasks.get_pregnancy_week(datetime(2014, 6, 29), "2014-07-14")
#         self.assertEqual(weeks, 38)
#         weeks = tasks.get_pregnancy_week(datetime(2014, 1, 1), "2014-09-21")
#         self.assertEqual(weeks, 3)
#         weeks = tasks.get_pregnancy_week(datetime(2014, 1, 1), "2014-10-03")
#         self.assertEqual(weeks, 2)

#         weeks = tasks.get_pregnancy_week(datetime(2013, 8, 19), "2013-08-20")
#         self.assertEqual(weeks, 40)
#         weeks = tasks.get_pregnancy_week(datetime(2013, 8, 19), "2013-08-27")
#         self.assertEqual(weeks, 39)
#         weeks = tasks.get_pregnancy_week(datetime(2013, 8, 19), "2013-09-03")
#         self.assertEqual(weeks, 38)
#         weeks = tasks.get_pregnancy_week(datetime(2013, 8, 19), "2013-09-10")
#         self.assertEqual(weeks, 37)
#         weeks = tasks.get_pregnancy_week(datetime(2013, 8, 19), "2013-09-17")
#         self.assertEqual(weeks, 36)
#         weeks = tasks.get_pregnancy_week(datetime(2013, 8, 19), "2013-09-24")
#         self.assertEqual(weeks, 35)
#         weeks = tasks.get_pregnancy_week(datetime(2013, 8, 19), "2013-10-15")
#         self.assertEqual(weeks, 32)
#         weeks = tasks.get_pregnancy_week(datetime(2013, 8, 19), "2013-10-22")
#         self.assertEqual(weeks, 31)
#         weeks = tasks.get_pregnancy_week(datetime(2013, 8, 19), "2014-04-24")
#         self.assertEqual(weeks, 5)
#         weeks = tasks.get_pregnancy_week(datetime(2013, 8, 19), "2014-05-07")
#         self.assertEqual(weeks, 3)

#     def test_sub_details(self):
#         contact = {"extra": {"is_registered_by": "personal"}}
#         sub_details = tasks.get_subscription_details(contact)
#         self.assertEqual(sub_details, ("subscription", "two_per_week", 1))

#         contact = {"extra": {"is_registered_by": "chw"}}
#         sub_details = tasks.get_subscription_details(contact)
#         self.assertEqual(sub_details, ("chw", "two_per_week", 1))

#         contact_40 = {"extra": {"is_registered_by": "clinic",
#                                 "edd": "2013-08-20"}}
#         sub_details = tasks.get_subscription_details(contact_40)
#         self.assertEqual(sub_details, ("accelerated", "daily", 1))

#         contact_39 = {"extra": {"is_registered_by": "clinic",
#                                 "edd": "2013-08-27"}}
#         sub_details = tasks.get_subscription_details(contact_39)
#         self.assertEqual(sub_details, ("accelerated", "daily", 1))

#         contact_38 = {"extra": {"is_registered_by": "clinic",
#                                 "edd": "2013-09-03"}}
#         sub_details = tasks.get_subscription_details(contact_38)
#         self.assertEqual(sub_details, ("accelerated", "five_per_week", 1))

#         contact_37 = {"extra": {"is_registered_by": "clinic",
#                                 "edd": "2013-09-10"}}
#         sub_details = tasks.get_subscription_details(contact_37)
#         self.assertEqual(sub_details, ("accelerated", "four_per_week", 1))

#         contact_36 = {"extra": {"is_registered_by": "clinic",
#                                 "edd": "2013-09-17"}}
#         sub_details = tasks.get_subscription_details(contact_36)
#         self.assertEqual(sub_details, ("accelerated", "three_per_week", 1))

#         contact_35 = {"extra": {"is_registered_by": "clinic",
#                                 "edd": "2013-09-24"}}
#         sub_details = tasks.get_subscription_details(contact_35)
#         self.assertEqual(sub_details, ("later", "three_per_week", 13))

#         contact_32 = {"extra": {"is_registered_by": "clinic",
#                                 "edd": "2013-10-15"}}
#         sub_details = tasks.get_subscription_details(contact_32)
#         self.assertEqual(sub_details, ("later", "three_per_week", 4))

#         contact_31 = {"extra": {"is_registered_by": "clinic",
#                                 "edd": "2013-10-22"}}
#         sub_details = tasks.get_subscription_details(contact_31)
#         self.assertEqual(sub_details, ("standard", "two_per_week", 53))

#         contact_05 = {"extra": {"is_registered_by": "clinic",
#                                 "edd": "2014-04-24"}}
#         sub_details = tasks.get_subscription_details(contact_05)
#         self.assertEqual(sub_details, ("standard", "two_per_week", 1))

#         contact_03 = {"extra": {"is_registered_by": "clinic",
#                                 "edd": "2014-05-07"}}
#         sub_details = tasks.get_subscription_details(contact_03)
#         self.assertEqual(sub_details, ("standard", "two_per_week", 1))

#     def test_update_vumi_contact_clinic_self(self):
#         registration = self.make_nursereg(
#             post_data=TEST_REG_DATA["clinic_self"])

#         client = self.make_client()
#         self.make_existing_contact({
#             u"key": u"knownuuid",
#             u"msisdn": u"+27001",
#             u"groups": [u"672442947cdf4a2aae0f96ccb688df05"],
#             u"user_account": u"knownaccount",
#             u"extra": {}
#         })

#         contact = tasks.update_create_vumi_contact.apply_async(
#             kwargs={"registration_id": registration.data["id"],
#                     "client": client})
#         result = contact.get()
#         self.assertEqual(result["msisdn"], "+27001")
#         self.assertEqual(result["groups"],
#                          [u"672442947cdf4a2aae0f96ccb688df05",
#                           u"ee47385f0c954fc6b614ec3961dbf30b"])
#         self.assertEqual(result["key"], "knownuuid")
#         self.assertEqual(result["user_account"], "knownaccount")
#         self.assertEqual(result["extra"], {
#             "is_registered": "true",
#             "is_registered_by": "clinic",
#             "language_choice": "en",
#             "source_name": "Test Source",
#             "sa_id": "8009151234001",
#             "clinic_code": "12345",
#             "dob": "1980-09-15",
#             "last_service_rating": "never",
#             "service_rating_reminders": "0",
#             "service_rating_reminder": "2013-08-20",
#             "edd": "2015-08-01",
#             "due_date_year": "2015",
#             "due_date_month": "08",
#             "due_date_day": "01",
#             "subscription_type": "1",
#             "subscription_rate": "3",
#             "subscription_seq_start": "1"
#         })

#     def test_create_vumi_contact_chw_self(self):
#         # make registration for contact with msisdn +27002
#         registration = self.make_nursereg(
#             post_data=TEST_REG_DATA["chw_self"])
#         client = self.make_client()
#         # make different existing contact
#         self.make_existing_contact({
#             u"key": u"knownuuid",
#             u"msisdn": u"+27001",
#             u"user_account": u"knownaccount",
#             u"extra": {}
#         })

#         contact = tasks.update_create_vumi_contact.apply_async(
#             kwargs={"registration_id": registration.data["id"],
#                     "client": client})
#         result = contact.get()
#         self.assertEqual(result["msisdn"], "+27002")
#         self.assertEqual(result["groups"],
#                          [u"13140076f49f4e84a752a5d5ab961091"])
#         self.assertEqual(result["extra"], {
#             "is_registered": "true",
#             "is_registered_by": "chw",
#             "language_choice": "xh",
#             "source_name": "Test Source",
#             "dob": "1980-10-15",
#             "subscription_type": "10",
#             "subscription_rate": "3",
#             "subscription_seq_start": "1"
#         })

#     def test_create_vumi_contact_clinic_hcw(self):
#         # make registration for contact with msisdn +27001
#         registration = self.make_nursereg(
#             post_data=TEST_REG_DATA["clinic_hcw"])
#         client = self.make_client()
#         # make different existing contact
#         self.make_existing_contact({
#             u"key": u"knownuuid",
#             u"msisdn": u"+27005",
#             u"user_account": u"knownaccount",
#             u"extra": {}
#         })

#         contact = tasks.update_create_vumi_contact.apply_async(
#             kwargs={"registration_id": registration.data["id"],
#                     "client": client})
#         result = contact.get()
#         self.assertEqual(result["msisdn"], "+27001")
#         self.assertEqual(result["groups"],
#                          [u"672442947cdf4a2aae0f96ccb688df05"])
#         self.assertEqual(result["extra"], {
#             "is_registered": "true",
#             "is_registered_by": "clinic",
#             "language_choice": "af",
#             "source_name": "Test Source",
#             "passport_no": "5551111",
#             "passport_origin": "zw",
#             "clinic_code": "12345",
#             "last_service_rating": "never",
#             "service_rating_reminders": "0",
#             "service_rating_reminder": "2013-08-20",
#             "registered_by": "+27820010001",
#             "edd": "2015-09-01",
#             "due_date_year": "2015",
#             "due_date_month": "09",
#             "due_date_day": "01",
#             "subscription_type": "1",
#             "subscription_rate": "3",
#             "subscription_seq_start": "1"
#         })

#     def test_create_vumi_contact_personal_detailed(self):
#         # make registration for contact with msisdn +27003
#         registration = self.make_nursereg(
#             post_data=TEST_REG_DATA["personal_detailed"])
#         client = self.make_client()
#         # make completely seperate existing contact
#         self.make_existing_contact({
#             u"key": u"knownuuid",
#             u"msisdn": u"+27005",
#             u"user_account": u"knownaccount",
#             u"extra": {}
#         })

#         contact = tasks.update_create_vumi_contact.apply_async(
#             kwargs={"registration_id": registration.data["id"],
#                     "client": client})
#         result = contact.get()
#         self.assertEqual(result["msisdn"], "+27003")
#         self.assertEqual(result["groups"],
#                          [u"f4738d01b4f74e41b9a6e804fc7eda56"])
#         self.assertEqual(result["extra"], {
#             "is_registered": "true",
#             "is_registered_by": "personal",
#             "language_choice": "st",
#             "source_name": "Test Source",
#             "passport_no": "5552222",
#             "passport_origin": "mz",
#             "subscription_type": "9",
#             "subscription_rate": "3",
#             "subscription_seq_start": "1"
#         })

#     def test_create_vumi_contact_personal_simple(self):
#         # make registration for contact with msisdn +27004
#         registration = self.make_nursereg(
#             post_data=TEST_REG_DATA["personal_simple"])
#         client = self.make_client()
#         # make completely seperate existing contact
#         self.make_existing_contact({
#             u"key": u"knownuuid",
#             u"msisdn": u"+27005",
#             u"user_account": u"knownaccount",
#             u"extra": {}
#         })

#         contact = tasks.update_create_vumi_contact.apply_async(
#             kwargs={"registration_id": registration.data["id"],
#                     "client": client})
#         result = contact.get()
#         self.assertEqual(result["msisdn"], "+27004")
#         self.assertEqual(result["groups"],
#                          [u"b1e6bbd5d28b477aabb9cce43de7e9d1"])
#         self.assertEqual(result["extra"], {
#             "is_registered": "true",
#             "is_registered_by": "personal",
#             "language_choice": "ss",
#             "source_name": "Test Source",
#             "subscription_type": "9",
#             "subscription_rate": "3",
#             "subscription_seq_start": "1"
#         })

#     def test_create_subscription(self):
#         contact_35 = {
#             "key": "knownkey",
#             "msisdn": "knownaddr",
#             "user_account": "knownaccount",
#             "extra": {
#                 "language_choice": "en",
#                 "is_registered_by": "clinic",
#                 "edd": "2013-09-24"
#             }
#         }
#         subscription = tasks.create_subscription(contact_35, 'clinic')
#         self.assertEqual(subscription.to_addr, "knownaddr")

#     def test_create_subscription_fail_fires_metric(self):
#         broken_contact = {
#             "key": "wherestherestoftheinfo"
#         }
#         tasks.create_subscription(broken_contact, 'clinic')
#         self.assertEqual(True, self.check_logs(
#             "Metric: u'test.clinic.sum.subscription_to_protocol_fail' " +
#             "[sum] -> 1"))
#         self.assertEqual(1, self.check_logs_number_of_entries())
