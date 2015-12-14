import json
import responses
import logging
from datetime import datetime
from django.contrib.auth.models import User
from django.test import TestCase
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from django.core.exceptions import MultipleObjectsReturned
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status
from requests.adapters import HTTPAdapter
from requests_testadapter import TestSession, Resp
from requests.exceptions import HTTPError
from go_http.contacts import ContactsApiClient
from go_http.send import LoggingSender
from fake_go_contacts import Request, FakeContactsApi
from .models import NurseReg, NurseSource, nursereg_postsave
from subscription.models import Subscription
from nursereg import tasks


def override_get_today():
    return datetime.strptime("20130819144811", "%Y%m%d%H%M%S")


def override_get_tomorrow():
    return "2013-08-20"


def override_get_sender():
    return LoggingSender('go_http.test')


TEST_REG_DATA = {
    # SA ID self registration
    "sa_id": {
        "cmsisdn": "+27821234444",
        "dmsisdn": "+27821234444",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "5101025009086",
        "dob": "1951-01-02",
        "sanc_reg_no": None,
        "persal_no": None
    },
    # Passport other registration
    "passport": {
        "cmsisdn": "+27821235555",
        "dmsisdn": "+27821234444",
        "faccode": "123456",
        "id_type": "passport",
        "id_no": "Cub1234",
        "dob": "1976-03-07",
        "passport_origin": "cu",
        "sanc_reg_no": None,
        "persal_no": None
    },
    "change_faccode": {
        "cmsisdn": "+27821237777",
        "dmsisdn": "+27821237777",
        "faccode": "234567",
        "id_type": "sa_id",
        "id_no": "5101025009086",
        "dob": "1951-01-02",
        "sanc_reg_no": None,
        "persal_no": None
    },
    "change_sanc": {
        "cmsisdn": "+27821237777",
        "dmsisdn": "+27821237777",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "5101025009086",
        "dob": "1951-01-02",
        "sanc_reg_no": "34567890",
        "persal_no": None
    },
    "change_persal": {
        "cmsisdn": "+27821237777",
        "dmsisdn": "+27821237777",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "5101025009086",
        "dob": "1951-01-02",
        "sanc_reg_no": None,
        "persal_no": "11114444"
    },
    "change_old_nr": {
        "cmsisdn": "+27821234444",
        "dmsisdn": "+27821234444",
        "rmsisdn": "+27821237777",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "5101025009086",
        "dob": "1951-01-02",
        "sanc_reg_no": None,
        "persal_no": None
    },
    "change_old_nr_multiple_active_subs": {
        "cmsisdn": "+27821234444",
        "dmsisdn": "+27821234444",
        "rmsisdn": "+27821232222",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "5101025009086",
        "dob": "1951-01-02",
        "sanc_reg_no": None,
        "persal_no": None
    },
    "switch_to_new_nr": {
        "cmsisdn": "+27821238888",
        "dmsisdn": "+27821237777",
        "rmsisdn": "+27821237777",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "5101025009086",
        "dob": "1951-01-02",
        "sanc_reg_no": None,
        "persal_no": None
    }
}
TEST_NURSE_SOURCE_DATA = {
    "name": "Test Nurse Source"
}
TEST_REG_DATA_BROKEN = {
    # single field null-violation test
    "no_msisdn": {
        "cmsisdn": None,
        "dmsisdn": None,
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "8009151234001",
        "dob": "1980-09-15",
    },
    # data below is for combination validation testing
    "sa_id_no_id_no": {
        "cmsisdn": "+27001",
        "dmsisdn": "+27001",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": None,
        "dob": "1980-09-15"
    },
    "passport_no_id_no": {
        "cmsisdn": "+27001",
        "dmsisdn": "+27001",
        "faccode": "123456",
        "id_type": "passport",
        "id_no": None,
        "dob": "1980-09-15"
    },
    "no_passport_origin": {
        "cmsisdn": "+27001",
        "dmsisdn": "+27001",
        "faccode": "123456",
        "id_type": "passport",
        "id_no": "SA12345",
        "dob": "1980-09-15"
    },
    "no_optout_reason": {
        "cmsisdn": "+27001",
        "dmsisdn": "+27001",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "8009151234001",
        "dob": "1980-09-15",
        "opted_out": True,
        "optout_reason": None,
        "optout_count": 1,
    },
    "zero_optout_count": {
        "cmsisdn": "+27001",
        "dmsisdn": "+27001",
        "faccode": "123456",
        "id_type": "sa_id",
        "id_no": "8009151234001",
        "dob": "1980-09-15",
        "opted_out": True,
        "optout_reason": "job_change",
        "optout_count": 0,
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

    fixtures = ["test_initialdata.json", "nursereg_test.json"]

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


class AuthenticatedAPITestCase(APITestCase):

    def _replace_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(NurseReg)
        assert has_listeners(), (
            "NurseReg model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(nursereg_postsave, sender=NurseReg)
        assert not has_listeners(), (
            "NurseReg model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(NurseReg)
        assert not has_listeners(), (
            "NurseReg model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests.")
        post_save.connect(nursereg_postsave, sender=NurseReg)

    def make_nursesource(self, post_data=TEST_NURSE_SOURCE_DATA):
        # Make source for the normal user who submits data but using admin user
        user = User.objects.get(username='testnormaluser')
        post_data["user"] = user
        nurse_source = NurseSource.objects.create(**post_data)
        return nurse_source

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
        self.assertEqual(d.cmsisdn, '+27821234444')
        self.assertEqual(d.dmsisdn, '+27821234444')
        self.assertEqual(d.faccode, '123456')
        self.assertEqual(d.id_type, 'sa_id')
        self.assertEqual(d.id_no, '5101025009086')
        self.assertEqual(d.dob.strftime("%Y-%m-%d"), "1951-01-02")
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

    @responses.activate
    def test_create_registration_fires_tasks(self):
        # restore the post_save hooks just for this test
        post_save.connect(nursereg_postsave, sender=NurseReg)

        # Check number of subscriptions before task fire
        self.assertEqual(Subscription.objects.all().count(), 6)

        # Check there are no pre-existing registration objects
        self.assertEqual(NurseReg.objects.all().count(), 0)

        responses.add(responses.POST,
                      "http://test/v2/nurse",
                      body='jembi_post_json task', status=201,
                      content_type='application/json')

        # Set up the client
        tasks.get_client = self.override_get_client

        # Make a new registration
        reg_response = self.make_nursereg(
            post_data=TEST_REG_DATA["sa_id"])

        # Test registration object has been created successfully
        self.assertEqual(reg_response.status_code, status.HTTP_201_CREATED)

        # Test there is now a registration object in the database
        d = NurseReg.objects.all()
        self.assertEqual(NurseReg.objects.all().count(), 1)

        # Test the registration object is the one you added
        d = NurseReg.objects.last()
        self.assertEqual(d.id_type, 'sa_id')

        # Test post requests have been made to Jembi
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            responses.calls[0].request.url,
            "http://test/v2/nurse")

        # Test number of subscriptions after task fire
        self.assertEqual(Subscription.objects.all().count(), 7)

        # Test subscription object is the one you added
        d = Subscription.objects.last()
        self.assertEqual(d.to_addr, "+27821234444")

        # Test metrics have fired
        self.assertEqual(True, self.check_logs(
            "Metric: u'test.nursereg.sum.json_to_jembi_success' [sum] -> 1"))
        self.assertEqual(True, self.check_logs(
            "Metric: u'test.sum.nc_subscriptions' [sum] -> 1"))
        self.assertEqual(True, self.check_logs(
            "Metric: u'test.nurseconnect.sum.nc_subscription_to_protocol_" +
            "success' [sum] -> 1"))
        self.assertEqual(3, self.check_logs_number_of_entries())

        # remove post_save hooks to prevent teardown errors
        post_save.disconnect(nursereg_postsave, sender=NurseReg)


class TestNurseRegistrationAPI(AuthenticatedAPITestCase):

    def test_get_nurseregistration(self):
        # Setup
        self.make_nursereg(post_data=TEST_REG_DATA["sa_id"])
        last_nursereg = NurseReg.objects.last()
        # Execute
        response = self.adminclient.get(
            '/api/v2/nurseregistrations/%s/' % last_nursereg.id,
            content_type='application/json')
        # Check
        self.assertEqual(response.status_code, 200)

    def test_patch_nurseregistration(self):
        # Setup
        self.make_nursereg(post_data=TEST_REG_DATA["sa_id"])
        last_nursereg = NurseReg.objects.last()
        # Execute
        response = self.adminclient.patch(
            '/api/v2/nurseregistrations/%s/' % last_nursereg.id,
            json.dumps({"persal_no": 88888888}),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        nursereg = NurseReg.objects.get(id=last_nursereg.id)
        self.assertEqual(nursereg.persal_no, 88888888)


class TestJembiPostJsonTask(AuthenticatedAPITestCase):

    def test_build_jembi_json_sa_id(self):
        # Setup
        nursereg_sa_id = self.make_nursereg(
            post_data=TEST_REG_DATA["sa_id"])
        reg = NurseReg.objects.get(pk=nursereg_sa_id.data["id"])
        expected_json_clinic_self = {
            "mha": 1,
            "swt": 3,
            "type": 7,
            "dmsisdn": "+27821234444",
            "cmsisdn": "+27821234444",
            "rmsisdn": None,
            "faccode": "123456",
            "id": '5101025009086^^^ZAF^NI',
            "dob": "19510102",
            "persal": None,
            "sanc": None,
            "encdate": '20130819144811'
        }
        # Execute
        payload = tasks.build_jembi_json(reg)
        # Check
        self.assertEqual(expected_json_clinic_self, payload)

    def test_build_jembi_json_passport(self):
        # Setup
        nursereg_passport = self.make_nursereg(
            post_data=TEST_REG_DATA["passport"])
        reg = NurseReg.objects.get(pk=nursereg_passport.data["id"])
        expected_json_clinic_self = {
            "mha": 1,
            "swt": 3,
            "type": 7,
            "dmsisdn": "+27821234444",
            "cmsisdn": "+27821235555",
            "rmsisdn": None,
            "faccode": "123456",
            "id": "Cub1234^^^CU^PPN",
            "dob": "19760307",
            "persal": None,
            "sanc": None,
            "encdate": '20130819144811'
        }
        # Execute
        payload = tasks.build_jembi_json(reg)
        # Check
        self.assertEqual(expected_json_clinic_self, payload)

    def test_build_jembi_json_change_old_nr(self):
        # Setup
        nursereg_change_old_nr = self.make_nursereg(
            post_data=TEST_REG_DATA["change_old_nr"])
        reg = NurseReg.objects.get(pk=nursereg_change_old_nr.data["id"])
        expected_json_clinic_self = {
            "mha": 1,
            "swt": 3,
            "type": 7,
            "dmsisdn": "+27821234444",
            "cmsisdn": "+27821234444",
            "rmsisdn": "+27821237777",
            "faccode": "123456",
            "id": '5101025009086^^^ZAF^NI',
            "dob": "19510102",
            "persal": None,
            "sanc": None,
            "encdate": '20130819144811'
        }
        # Execute
        payload = tasks.build_jembi_json(reg)
        # Check
        self.assertEqual(expected_json_clinic_self, payload)

    def test_build_jembi_json_change_faccode(self):
        # Setup
        nursereg_change_faccode = self.make_nursereg(
            post_data=TEST_REG_DATA["change_faccode"])
        reg = NurseReg.objects.get(pk=nursereg_change_faccode.data["id"])
        expected_json_clinic_self = {
            "mha": 1,
            "swt": 3,
            "type": 7,
            "dmsisdn": "+27821237777",
            "cmsisdn": "+27821237777",
            "rmsisdn": None,
            "faccode": "234567",
            "id": '5101025009086^^^ZAF^NI',
            "dob": "19510102",
            "persal": None,
            "sanc": None,
            "encdate": '20130819144811'
        }
        # Execute
        payload = tasks.build_jembi_json(reg)
        # Check
        self.assertEqual(expected_json_clinic_self, payload)

    def test_build_jembi_json_change_persal(self):
        # Setup
        nursereg_change_persal = self.make_nursereg(
            post_data=TEST_REG_DATA["change_persal"])
        reg = NurseReg.objects.get(pk=nursereg_change_persal.data["id"])
        expected_json_clinic_self = {
            "mha": 1,
            "swt": 3,
            "type": 7,
            "dmsisdn": "+27821237777",
            "cmsisdn": "+27821237777",
            "rmsisdn": None,
            "faccode": "123456",
            "id": '5101025009086^^^ZAF^NI',
            "dob": "19510102",
            "persal": 11114444,
            "sanc": None,
            "encdate": '20130819144811'
        }
        # Execute
        payload = tasks.build_jembi_json(reg)
        # Check
        self.assertEqual(expected_json_clinic_self, payload)

    @responses.activate
    def test_jembi_post_json(self):
        # Setup
        nursereg = self.make_nursereg(
            post_data=TEST_REG_DATA["sa_id"])

        responses.add(responses.POST,
                      "http://test/v2/nurse",
                      body='jembi_post_json task', status=201,
                      content_type='application/json')

        task_response = tasks.jembi_post_json.apply_async(
            kwargs={"nursereg_id": nursereg.data["id"],
                    "sender": self.sender})
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(task_response.get(), 'jembi_post_json task')
        self.assertEqual(True, self.check_logs(
            "Metric: u'test.nursereg.sum.json_to_jembi_success' [sum] -> 1"))
        self.assertEqual(1, self.check_logs_number_of_entries())

    @responses.activate
    def test_jembi_post_json_retries(self):
        nursereg = self.make_nursereg(
            post_data=TEST_REG_DATA["sa_id"])

        responses.add(responses.POST,
                      "http://test/v2/nurse",
                      body='{"error": "jembi json problems"}', status=531,
                      content_type='application/json')

        task_response = tasks.jembi_post_json.apply_async(
            kwargs={"nursereg_id": nursereg.data["id"]})
        self.assertEqual(len(responses.calls), 4)
        with self.assertRaises(HTTPError) as cm:
            task_response.get()
        self.assertEqual(cm.exception.response.status_code, 531)
        self.assertEqual(True, self.check_logs(
            "Metric: u'test.nursereg.sum.json_to_jembi_fail' [sum] -> 1"))
        self.assertEqual(1, self.check_logs_number_of_entries())

    @responses.activate
    def test_jembi_post_json_other_httperror(self):
        nursereg = self.make_nursereg(
            post_data=TEST_REG_DATA["sa_id"])

        responses.add(responses.POST,
                      "http://test/v2/nurse",
                      body='{"error": "jembi json problems"}', status=404,
                      content_type='application/json')

        task_response = tasks.jembi_post_json.apply_async(
            kwargs={"nursereg_id": nursereg.data["id"]})
        self.assertEqual(len(responses.calls), 1)
        with self.assertRaises(HTTPError) as cm:
            task_response.get()
        self.assertEqual(cm.exception.response.status_code, 404)
        self.assertEqual(True, self.check_logs(
            "Metric: u'test.nursereg.sum.json_to_jembi_fail' [sum] -> 1"))
        self.assertEqual(1, self.check_logs_number_of_entries())


class TestUpdateCreateVumiContactTask(AuthenticatedAPITestCase):

    def test_sub_details(self):
        # Setup
        # Execute
        sub_details = tasks.get_subscription_details()
        # Check
        self.assertEqual(sub_details, ("nurseconnect", "three_per_week", 1))

    def test_update_vumi_contact_sa_id(self):
        # Test mocks a JS nurse registration - existing Vumi contact
        # Setup
        # make existing contact with msisdn 27821234444
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+27821234444",
            u"groups": [u"672442947cdf4a2aae0f96ccb688df05"],
            u"user_account": u"knownaccount",
            u"extra": {}
        })
        # nurse registration for contact 27001
        nursereg = self.make_nursereg(
            post_data=TEST_REG_DATA["sa_id"])
        client = self.make_client()
        presubs = Subscription.objects.all().count()
        last_nursereg = NurseReg.objects.last()
        # Execute
        contact = tasks.update_create_vumi_contact.apply_async(
            kwargs={"nursereg_id": nursereg.data["id"],
                    "client": client})
        result = contact.get()
        # Check
        self.assertEqual(result["msisdn"], "+27821234444")
        self.assertEqual(result["groups"],
                         [u"672442947cdf4a2aae0f96ccb688df05"])
        self.assertEqual(result["key"], "knownuuid")
        self.assertEqual(result["user_account"], "knownaccount")
        self.assertEqual(result["extra"], {
            "nc_last_reg_id": str(last_nursereg.id),
            "nc_dob": "1951-01-02",
            "nc_sa_id_no": "5101025009086",
            "nc_is_registered": "true",
            "nc_id_type": "sa_id",
            "nc_faccode": "123456",
            "nc_source_name": "Test Nurse Source",
            "nc_subscription_type": "11",
            "nc_subscription_rate": "4",
            "nc_subscription_seq_start": "1",
        })
        postsubs = Subscription.objects.all().count()
        self.assertEqual(postsubs, presubs+1)

    def test_create_vumi_contact_passport(self):
        # Test mocks an external registration - no existing Vumi contact
        # Setup
        # make existing contact with msisdn 27001
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+27001",
            u"user_account": u"knownaccount",
            u"extra": {}
        })
        # nurse registration for contact 27821235555
        nursereg = self.make_nursereg(
            post_data=TEST_REG_DATA["passport"])
        client = self.make_client()
        presubs = Subscription.objects.all().count()
        last_nursereg = NurseReg.objects.last()
        # Execute
        contact = tasks.update_create_vumi_contact.apply_async(
            kwargs={"nursereg_id": nursereg.data["id"],
                    "client": client})
        result = contact.get()
        # Check
        self.assertEqual(result["msisdn"], "+27821235555")
        self.assertEqual(result["groups"], [])
        self.assertEqual(result["extra"], {
            "nc_last_reg_id": str(last_nursereg.id),
            "nc_dob": "1976-03-07",
            "nc_passport_num": "Cub1234",
            "nc_passport_country": "cu",
            "nc_is_registered": "true",
            "nc_id_type": "passport",
            "nc_faccode": "123456",
            "nc_source_name": "Test Nurse Source",
            "nc_registered_by": "+27821234444",
            "nc_subscription_type": "11",
            "nc_subscription_rate": "4",
            "nc_subscription_seq_start": "1"
        })
        postsubs = Subscription.objects.all().count()
        self.assertEqual(postsubs, presubs+1)

    def test_create_vumi_contact_change_faccode(self):
        # Test mocks an external registration - no existing Vumi contact
        # Setup
        # make existing contact with msisdn 27821237777
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+27821237777",
            u"user_account": u"knownaccount",
            u"extra": {
                "nc_last_reg_id": "last nursereg id",
                "nc_dob": "1951-01-02",
                "nc_sa_id_no": "5101025009086",
                "nc_is_registered": "true",
                "nc_id_type": "sa_id",
                "nc_faccode": "123456",
                "nc_source_name": "Test Nurse Source",
                "nc_subscription_type": "11",
                "nc_subscription_rate": "4",
                "nc_subscription_seq_start": "1",
            }
        })
        # nurse registration for contact 27821237777 -change faccode
        nursereg = self.make_nursereg(
            post_data=TEST_REG_DATA["change_faccode"])
        client = self.make_client()
        presubs = Subscription.objects.all().count()
        last_nursereg = NurseReg.objects.last()
        # Execute
        contact = tasks.update_create_vumi_contact.apply_async(
            kwargs={"nursereg_id": nursereg.data["id"],
                    "client": client})
        result = contact.get()
        # Check
        self.assertEqual(result["msisdn"], "+27821237777")
        self.assertEqual(result["groups"], [])
        self.assertEqual(result["extra"], {
            "nc_last_reg_id": str(last_nursereg.id),
            "nc_dob": "1951-01-02",
            "nc_sa_id_no": "5101025009086",
            "nc_is_registered": "true",
            "nc_id_type": "sa_id",
            "nc_faccode": "234567",
            "nc_source_name": "Test Nurse Source",
            "nc_subscription_type": "11",
            "nc_subscription_rate": "4",
            "nc_subscription_seq_start": "1",
        })
        postsubs = Subscription.objects.all().count()
        # check no additional subscription created
        self.assertEqual(postsubs, presubs)

    def test_create_vumi_contact_change_sanc(self):
        # Test mocks an external registration - no existing Vumi contact
        # Setup
        # make existing contact with msisdn 27821237777
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+27821237777",
            u"user_account": u"knownaccount",
            u"extra": {
                "nc_last_reg_id": "last nursereg id",
                "nc_dob": "1951-01-02",
                "nc_sa_id_no": "5101025009086",
                "nc_is_registered": "true",
                "nc_id_type": "sa_id",
                "nc_faccode": "123456",
                "nc_source_name": "Test Nurse Source",
                "nc_subscription_type": "11",
                "nc_subscription_rate": "4",
                "nc_subscription_seq_start": "1",
            }
        })
        # nurse registration for contact 27821237777 -change sanc nr
        nursereg = self.make_nursereg(
            post_data=TEST_REG_DATA["change_sanc"])
        client = self.make_client()
        presubs = Subscription.objects.all().count()
        last_nursereg = NurseReg.objects.last()
        # Execute
        contact = tasks.update_create_vumi_contact.apply_async(
            kwargs={"nursereg_id": nursereg.data["id"],
                    "client": client})
        result = contact.get()
        # Check
        self.assertEqual(result["msisdn"], "+27821237777")
        self.assertEqual(result["groups"], [])
        self.assertEqual(result["extra"], {
            "nc_last_reg_id": str(last_nursereg.id),
            "nc_dob": "1951-01-02",
            "nc_sa_id_no": "5101025009086",
            "nc_is_registered": "true",
            "nc_id_type": "sa_id",
            "nc_faccode": "123456",
            "nc_source_name": "Test Nurse Source",
            "nc_sanc": "34567890",
            "nc_subscription_type": "11",
            "nc_subscription_rate": "4",
            "nc_subscription_seq_start": "1",
        })
        postsubs = Subscription.objects.all().count()
        # check no additional subscription created
        self.assertEqual(postsubs, presubs)

    def test_create_vumi_contact_change_persal(self):
        # Test mocks an external registration - no existing Vumi contact
        # Setup
        # make existing contact with msisdn 27821237777
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+27821237777",
            u"user_account": u"knownaccount",
            u"extra": {
                "nc_last_reg_id": "last nursereg id",
                "nc_dob": "1951-01-02",
                "nc_sa_id_no": "5101025009086",
                "nc_is_registered": "true",
                "nc_id_type": "sa_id",
                "nc_faccode": "123456",
                "nc_source_name": "Test Nurse Source",
                "nc_subscription_type": "11",
                "nc_subscription_rate": "4",
                "nc_subscription_seq_start": "1",
            }
        })
        # nurse registration for contact 27821237777 -change persal
        nursereg = self.make_nursereg(
            post_data=TEST_REG_DATA["change_persal"])
        client = self.make_client()
        presubs = Subscription.objects.all().count()
        last_nursereg = NurseReg.objects.last()
        # Execute
        contact = tasks.update_create_vumi_contact.apply_async(
            kwargs={"nursereg_id": nursereg.data["id"],
                    "client": client})
        result = contact.get()
        # Check
        self.assertEqual(result["msisdn"], "+27821237777")
        self.assertEqual(result["groups"], [])
        self.assertEqual(result["extra"], {
            "nc_last_reg_id": str(last_nursereg.id),
            "nc_dob": "1951-01-02",
            "nc_sa_id_no": "5101025009086",
            "nc_is_registered": "true",
            "nc_id_type": "sa_id",
            "nc_faccode": "123456",
            "nc_source_name": "Test Nurse Source",
            "nc_persal": "11114444",
            "nc_subscription_type": "11",
            "nc_subscription_rate": "4",
            "nc_subscription_seq_start": "1",
        })
        postsubs = Subscription.objects.all().count()
        # check no additional subscription created
        self.assertEqual(postsubs, presubs)

    def test_create_vumi_contact_change_old_nr(self):
        # Setup
        # make existing contact with msisdn 27821237777
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+27821237777",
            u"user_account": u"knownaccount",
            u"extra": {
                "nc_last_reg_id": "last nursereg id",
                "nc_dob": "1951-01-02",
                "nc_sa_id_no": "5101025009086",
                "nc_is_registered": "true",
                "nc_id_type": "sa_id",
                "nc_faccode": "123456",
                "nc_source_name": "Test Nurse Source",
                "nc_subscription_type": "11",
                "nc_subscription_rate": "4",
                "nc_subscription_seq_start": "11",
            }
        })
        # nurse registration - change old nr
        nursereg = self.make_nursereg(
            post_data=TEST_REG_DATA["change_old_nr"])
        client = self.make_client()
        presubs = Subscription.objects.all().count()
        last_nursereg = NurseReg.objects.last()
        # Execute
        contact = tasks.update_create_vumi_contact.apply_async(
            kwargs={"nursereg_id": nursereg.data["id"],
                    "client": client})
        result = contact.get()
        # Check
        self.assertEqual(result["msisdn"], "+27821234444")
        self.assertEqual(result["groups"], [])
        self.assertEqual(result["extra"], {
            "nc_last_reg_id": str(last_nursereg.id),
            "nc_dob": "1951-01-02",
            "nc_sa_id_no": "5101025009086",
            "nc_is_registered": "true",
            "nc_id_type": "sa_id",
            "nc_faccode": "123456",
            "nc_source_name": "Test Nurse Source",
            "nc_subscription_type": "11",
            "nc_subscription_rate": "4",
            "nc_subscription_seq_start": "13",
        })
        postsubs = Subscription.objects.all().count()
        # check one additional subscriptions created
        self.assertEqual(postsubs, presubs+1)

    def test_create_vumi_contact_multiple_active_subscriptions(self):
        # Setup
        # make existing contact with msisdn 27821232222
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+27821232222",
            u"user_account": u"knownaccount",
            u"extra": {
                "nc_last_reg_id": "last nursereg id",
                "nc_dob": "1951-01-02",
                "nc_sa_id_no": "5101025009086",
                "nc_is_registered": "true",
                "nc_id_type": "sa_id",
                "nc_faccode": "123456",
                "nc_source_name": "Test Nurse Source",
                "nc_subscription_type": "11",
                "nc_subscription_rate": "4",
                "nc_subscription_seq_start": "11",
            }
        })
        # nurse registration - change old nr
        nursereg = self.make_nursereg(
            post_data=TEST_REG_DATA["change_old_nr_multiple_active_subs"])
        client = self.make_client()
        presubs = Subscription.objects.all().count()
        # Execute
        # Check
        with self.assertRaises(MultipleObjectsReturned):
            contact = tasks.update_create_vumi_contact.apply_async(
                kwargs={"nursereg_id": nursereg.data["id"],
                        "client": client})
            contact.get()

        postsubs = Subscription.objects.all().count()
        # check no additional subscriptions created
        self.assertEqual(postsubs, presubs)

    def test_create_vumi_contact_switch_to_new_nr(self):
        # Setup
        # make existing contact with msisdn 27821237777
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+27821237777",
            u"user_account": u"knownaccount",
            u"extra": {
                "nc_last_reg_id": "last nursereg id",
                "nc_dob": "1951-01-02",
                "nc_sa_id_no": "5101025009086",
                "nc_is_registered": "true",
                "nc_id_type": "sa_id",
                "nc_faccode": "123456",
                "nc_source_name": "Test Nurse Source",
                "nc_subscription_type": "11",
                "nc_subscription_rate": "4",
                "nc_subscription_seq_start": "1",
            }
        })
        # nurse registration - switch to new nr
        nursereg = self.make_nursereg(
            post_data=TEST_REG_DATA["switch_to_new_nr"])
        client = self.make_client()
        presubs = Subscription.objects.all().count()
        last_nursereg = NurseReg.objects.last()
        # Execute
        contact = tasks.update_create_vumi_contact.apply_async(
            kwargs={"nursereg_id": nursereg.data["id"],
                    "client": client})
        result = contact.get()
        # Check
        self.assertEqual(result["msisdn"], "+27821238888")
        self.assertEqual(result["groups"], [])
        self.assertEqual(result["extra"], {
            "nc_last_reg_id": str(last_nursereg.id),
            "nc_dob": "1951-01-02",
            "nc_sa_id_no": "5101025009086",
            "nc_is_registered": "true",
            "nc_id_type": "sa_id",
            "nc_faccode": "123456",
            "nc_source_name": "Test Nurse Source",
            "nc_subscription_type": "11",
            "nc_subscription_rate": "4",
            "nc_subscription_seq_start": "13",
            "nc_registered_by": "+27821237777"
        })
        postsubs = Subscription.objects.all().count()
        # check one additional subscriptions created
        self.assertEqual(postsubs, presubs+1)

    def test_create_subscription(self):
        contact = {
            "key": "knownkey",
            "msisdn": "knownaddr",
            "user_account": "knownaccount",
            "extra": {}
        }
        subscription = tasks.create_subscription(contact)
        self.assertEqual(subscription.to_addr, "knownaddr")

    def test_create_subscription_fail_fires_metric(self):
        broken_contact = {
            "key": "wherestherestoftheinfo"
        }
        tasks.create_subscription(broken_contact)
        self.assertEqual(True, self.check_logs(
            "Metric: u'test.nurseconnect.sum.nc_subscription_to_protocol_" +
            "fail' [sum] -> 1"))
        self.assertEqual(1, self.check_logs_number_of_entries())
