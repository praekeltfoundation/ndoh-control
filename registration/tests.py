import json
import responses
from django.contrib.auth.models import User
from django.test import TestCase
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status
from requests.adapters import HTTPAdapter
from requests_testadapter import TestSession, Resp
from go_http.contacts import ContactsApiClient
from fake_go_contacts import Request, FakeContactsApi
from .models import Source, Registration, fire_jembi_post
from registration import tasks


def override_get_timestamp():
    return "20130819144811"

tasks.get_timestamp = override_get_timestamp


def override_get_tomorrow():
    return "2014-01-02"

tasks.get_tomorrow = override_get_tomorrow


TEST_REG_DATA = {
    "clinic_self": {
        "hcw_msisdn": None,
        "mom_msisdn": "+27001",
        "mom_id_type": "sa_id",
        "mom_passport_origin": None,
        "mom_lang": "en",
        "mom_edd": "2015-08-01",
        "mom_id_no": "8009151234001",
        "mom_dob": "1980-09-15",
        "clinic_code": "12345",
        "authority": "clinic"
    },
    "clinic_hcw": {
        "hcw_msisdn": "+27820010001",
        "mom_msisdn": "+27001",
        "mom_id_type": "passport",
        "mom_passport_origin": "zw",
        "mom_lang": "af",
        "mom_edd": "2015-09-01",
        "mom_id_no": "5551111",
        "mom_dob": None,
        "clinic_code": "12345",
        "authority": "clinic"
    },
    "chw_self": {
        "hcw_msisdn": None,
        "mom_msisdn": "+27002",
        "mom_id_type": "none",
        "mom_passport_origin": None,
        "mom_lang": "xh",
        "mom_edd": None,
        "mom_id_no": None,
        "mom_dob": "1980-10-15",
        "clinic_code": None,
        "authority": "chw"
    },
    "chw_hcw": {
        "hcw_msisdn": "+27820020002",
        "mom_msisdn": "+27002",
        "mom_id_type": "sa_id",
        "mom_passport_origin": None,
        "mom_lang": "zu",
        "mom_edd": None,
        "mom_id_no": "8011151234001",
        "mom_dob": "1980-11-15",
        "clinic_code": None,
        "authority": "chw"
    },
    "personal": {
        "hcw_msisdn": None,
        "mom_msisdn": "+27003",
        "mom_id_type": "passport",
        "mom_passport_origin": "mz",
        "mom_lang": "st",
        "mom_edd": None,
        "mom_id_no": "5552222",
        "mom_dob": None,
        "clinic_code": None,
        "authority": "personal"
    }
}
TEST_SOURCE_DATA = {
    "name": "Test Source"
}
TEST_REG_DATA_BROKEN = {
    # single field null-violation test
    "no_msisdn": {
        "hcw_msisdn": None,
        "mom_msisdn": None,
        "mom_id_type": "sa_id",
        "mom_passport_origin": None,
        "mom_lang": "en",
        "mom_edd": "2015-08-01",
        "mom_id_no": "555111",
        "mom_dob": "1980-09-15",
        "clinic_code": "12345",
        "authority": "clinic"
    },
    # data below is for combination validation testing
    "no_sa_id_no": {
        "hcw_msisdn": None,
        "mom_msisdn": "+27001",
        "mom_id_type": "sa_id",
        "mom_passport_origin": None,
        "mom_lang": "en",
        "mom_edd": "2015-08-01",
        "mom_id_no": None,
        "mom_dob": "1980-09-15",
        "clinic_code": "12345",
        "authority": "clinic"
    },
    "no_passport_no": {
        "hcw_msisdn": None,
        "mom_msisdn": "+27001",
        "mom_id_type": "passport",
        "mom_passport_origin": "zw",
        "mom_lang": "en",
        "mom_edd": "2015-08-01",
        "mom_id_no": None,
        "mom_dob": "1980-09-15",
        "clinic_code": "12345",
        "authority": "clinic"
    },
    "no_passport_origin": {
        "hcw_msisdn": None,
        "mom_msisdn": "+27001",
        "mom_id_type": "passport",
        "mom_passport_origin": None,
        "mom_lang": "en",
        "mom_edd": "2015-08-01",
        "mom_id_no": "555111",
        "mom_dob": "1980-09-15",
        "clinic_code": "12345",
        "authority": "clinic"
    },
    "no_dob": {
        "hcw_msisdn": None,
        "mom_msisdn": "+27001",
        "mom_id_type": "none",
        "mom_passport_origin": None,
        "mom_lang": "en",
        "mom_edd": "2015-08-01",
        "mom_id_no": "555111",
        "mom_dob": None,
        "clinic_code": "12345",
        "authority": "clinic"
    },
    "no_edd": {
        "hcw_msisdn": None,
        "mom_msisdn": "+27001",
        "mom_id_type": "none",
        "mom_passport_origin": None,
        "mom_lang": "en",
        "mom_edd": None,
        "mom_id_no": "555111",
        "mom_dob": "1980-09-15",
        "clinic_code": "12345",
        "authority": "clinic"
    },
    "no_clinic_code": {
        "hcw_msisdn": None,
        "mom_msisdn": "+27001",
        "mom_id_type": "none",
        "mom_passport_origin": None,
        "mom_lang": "en",
        "mom_edd": "2015-08-01",
        "mom_id_no": "555111",
        "mom_dob": "1980-09-15",
        "clinic_code": None,
        "authority": "clinic"
    }
}
TEST_CONTACT_DATA = {
    u"key": u"knownuuid",
    u"msisdn": u"+155564",
    u"user_account": u"knownaccount",
    u"extra": {
        u"last_service_rating": u"now",
        u"service_rating_reminder": "2015-02-01",
        u"service_rating_reminders": "0",
    }
}
API_URL = "http://example.com/go"
AUTH_TOKEN = "auth_token"
MAX_CONTACTS_PER_PAGE = 10


class APITestCase(TestCase):

    def setUp(self):
        self.adminclient = APIClient()
        self.normalclient = APIClient()


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
        has_listeners = lambda: post_save.has_listeners(Registration)
        assert has_listeners(), (
            "Registration model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(fire_jembi_post, sender=Registration)
        assert not has_listeners(), (
            "Registration model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(Registration)
        assert not has_listeners(), (
            "Registration model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests.")
        post_save.connect(fire_jembi_post, sender=Registration)

    def make_source(self, post_data=TEST_SOURCE_DATA):
        user = User.objects.get(username='testadminuser')
        post_data["user"] = "/api/v2/users/%s/" % user.id

        response = self.adminclient.post('/api/v2/sources/',
                                         json.dumps(post_data),
                                         content_type='application/json')
        return response

    def make_registration(self, post_data):
        source = self.make_source()
        post_data["source"] = "/api/v2/sources/%s/" % source.data["id"]

        response = self.normalclient.post('/api/v2/registrations/',
                                          json.dumps(post_data),
                                          content_type='application/json')
        return response

    def make_client(self):
        return ContactsApiClient(auth_token=AUTH_TOKEN, api_url=API_URL,
                                 session=self.session)

    def make_existing_contact(self, contact_data=TEST_CONTACT_DATA):
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
        expected_contact[u"extra"][u"last_service_rating"] = u"now"
        updated_contact = client.update_contact(
            u"knownuuid", {
                # Note the whole extra dict needs passing in
                u"extra": {
                    u"last_service_rating": u"now",
                    u"service_rating_reminder": "2015-02-01",
                    u"service_rating_reminders": "0",
                }
            }
        )
        self.assertEqual(updated_contact, expected_contact)

    def test_create_contact(self):
        client = self.make_client()
        created_contact = client.create_contact({
            u"msisdn": "+111"
        })
        self.assertEqual(created_contact["msisdn"], "+111")
        self.assertIsNotNone(created_contact["key"])


class TestRegistrationsAPI(AuthenticatedAPITestCase):

    def test_create_source(self):
        response = self.make_source()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        d = Source.objects.last()
        self.assertEqual(d.name, 'Test Source')

    def test_create_source_deny_normaluser(self):
        user = User.objects.get(username='testnormaluser')
        post_data = TEST_SOURCE_DATA
        post_data["user"] = "/api/v2/users/%s/" % user.id
        response = self.normalclient.post('/api/v2/sources/',
                                          json.dumps(post_data),
                                          content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_registration(self):
        reg_response = self.make_registration(
            post_data=TEST_REG_DATA["clinic_self"])
        self.assertEqual(reg_response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.mom_id_type, 'sa_id')

    def test_create_broken_registration_no_mom_msisdn(self):
        reg_response = self.make_registration(
            post_data=TEST_REG_DATA_BROKEN["no_msisdn"])
        self.assertEqual(reg_response.status_code, status.HTTP_400_BAD_REQUEST)

        d = Registration.objects.last()
        self.assertEqual(d, None)

    def test_create_broken_registration_no_sa_id_no(self):
        self.assertRaises(ValidationError, lambda: self.make_registration(
            post_data=TEST_REG_DATA_BROKEN["no_sa_id_no"]))

        d = Registration.objects.last()
        self.assertEqual(d, None)

    def test_create_broken_registration_no_passport_no(self):
        self.assertRaises(ValidationError, lambda: self.make_registration(
            post_data=TEST_REG_DATA_BROKEN["no_passport_no"]))

        d = Registration.objects.last()
        self.assertEqual(d, None)

    def test_create_broken_registration_no_passport_origin(self):
        self.assertRaises(ValidationError, lambda: self.make_registration(
            post_data=TEST_REG_DATA_BROKEN["no_passport_origin"]))

        d = Registration.objects.last()
        self.assertEqual(d, None)

    def test_create_broken_registration_no_dob(self):
        self.assertRaises(ValidationError, lambda: self.make_registration(
            post_data=TEST_REG_DATA_BROKEN["no_dob"]))

        d = Registration.objects.last()
        self.assertEqual(d, None)

    def test_create_broken_registration_no_edd(self):
        self.assertRaises(ValidationError, lambda: self.make_registration(
            post_data=TEST_REG_DATA_BROKEN["no_edd"]))

        d = Registration.objects.last()
        self.assertEqual(d, None)

    def test_create_broken_registration_no_clinic_code(self):
        self.assertRaises(ValidationError, lambda: self.make_registration(
            post_data=TEST_REG_DATA_BROKEN["no_clinic_code"]))

        d = Registration.objects.last()
        self.assertEqual(d, None)

    @responses.activate
    def test_create_registration_fires_tasks(self):
        # restore the post_save hooks just for this test
        post_save.connect(fire_jembi_post, sender=Registration)

        responses.add(responses.POST,
                      "http://test/v2/json/subscription",
                      body='jembi_post_json task', status=201,
                      content_type='application/json')

        # Make a new registration
        reg_response = self.make_registration(
            post_data=TEST_REG_DATA["clinic_self"])

        # Test registration object has been created
        self.assertEqual(reg_response.status_code, status.HTTP_201_CREATED)
        d = Registration.objects.last()
        self.assertEqual(d.mom_id_type, 'sa_id')

        # Test post has been made to jembi
        self.assertEqual(len(responses.calls), 3)
        self.assertEqual(
            responses.calls[0].request.url,
            "http://test/v2/json/subscription")
        self.assertEqual(
            responses.calls[1].request.url,
            "http://vumi_go_test/contacts/?query=msisdn%3D%2B27001")
        self.assertEqual(
            responses.calls[2].request.url,
            "http://vumi_go_test/contacts/")

        # remove post_save hooks to prevent teardown errors
        post_save.disconnect(fire_jembi_post, sender=Registration)


class TestJembiPostJsonTask(AuthenticatedAPITestCase):

    def test_build_jembi_json_clinic_self(self):
        registration_clinic_self = self.make_registration(
            post_data=TEST_REG_DATA["clinic_self"])
        reg = Registration.objects.get(pk=registration_clinic_self.data["id"])
        expected_json_clinic_self = {
            'edd': '20150801',
            'id': '8009151234001^^^ZAF^NI',
            'lang': 'en',
            'dob': "19800915",
            'dmsisdn': None,
            'mha': 1,
            'cmsisdn': '+27001',
            'faccode': '12345',
            'encdate': '20130819144811',
            'type': 3,
            'swt': 1
        }
        json = tasks.build_jembi_json(reg)
        self.assertEqual(expected_json_clinic_self, json)

    def test_build_jembi_json_clinic_hcw(self):
        registration_clinic_hcw = self.make_registration(
            post_data=TEST_REG_DATA["clinic_hcw"])
        reg = Registration.objects.get(pk=registration_clinic_hcw.data["id"])
        expected_json_clinic_hcw = {
            'edd': '20150901',
            'id': '5551111^^^ZW^PPN',
            'lang': 'af',
            'dob': None,
            'dmsisdn': "+27820010001",
            'mha': 1,
            'cmsisdn': '+27001',
            'faccode': '12345',
            'encdate': '20130819144811',
            'type': 3,
            'swt': 1
        }
        json = tasks.build_jembi_json(reg)
        self.assertEqual(expected_json_clinic_hcw, json)

    def test_build_jembi_json_chw_self(self):
        registration_chw_self = self.make_registration(
            post_data=TEST_REG_DATA["chw_self"])
        reg = Registration.objects.get(pk=registration_chw_self.data["id"])
        expected_json_chw_self = {
            'id': '27002^^^ZAF^TEL',
            'lang': 'xh',
            'dob': "19801015",
            'dmsisdn': None,
            'mha': 1,
            'cmsisdn': '+27002',
            'faccode': None,
            'encdate': '20130819144811',
            'type': 2,
            'swt': 1
        }
        json = tasks.build_jembi_json(reg)
        self.assertEqual(expected_json_chw_self, json)

    def test_build_jembi_json_chw_hcw(self):
        registration_chw_hcw = self.make_registration(
            post_data=TEST_REG_DATA["chw_hcw"])
        reg = Registration.objects.get(pk=registration_chw_hcw.data["id"])
        expected_json_chw_hcw = {
            'id': '8011151234001^^^ZAF^NI',
            'lang': 'zu',
            'dob': "19801115",
            'dmsisdn': "+27820020002",
            'mha': 1,
            'cmsisdn': '+27002',
            'faccode': None,
            'encdate': '20130819144811',
            'type': 2,
            'swt': 1
        }
        json = tasks.build_jembi_json(reg)
        self.assertEqual(expected_json_chw_hcw, json)

    def test_build_jembi_json_personal(self):
        registration_personal = self.make_registration(
            post_data=TEST_REG_DATA["personal"])
        reg = Registration.objects.get(pk=registration_personal.data["id"])
        expected_json_personal = {
            'id': '5552222^^^MZ^PPN',
            'lang': 'st',
            'dob': None,
            'dmsisdn': None,
            'mha': 1,
            'cmsisdn': '+27003',
            'faccode': None,
            'encdate': '20130819144811',
            'type': 1,
            'swt': 1
        }
        json = tasks.build_jembi_json(reg)
        self.assertEqual(expected_json_personal, json)

    @responses.activate
    def test_jembi_post_json(self):
        registration = self.make_registration(
            post_data=TEST_REG_DATA["clinic_self"])

        responses.add(responses.POST,
                      "http://test/v2/json/subscription",
                      body='jembi_post_json task', status=201,
                      content_type='application/json')

        task_response = tasks.jembi_post_json.apply_async(
            kwargs={"registration_id": registration.data["id"]})
        self.assertEqual(task_response.get(), 'jembi_post_json task')


class TestUpdateCreateVumiContactTask(AuthenticatedAPITestCase):

    def test_update_vumi_contact(self):
        registration = self.make_registration(
            post_data=TEST_REG_DATA["clinic_self"])
        client = self.make_client()
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+27001",
            u"user_account": u"knownaccount",
            u"extra": {}
        })

        contact = tasks.update_create_vumi_contact.apply_async(
            kwargs={"registration_id": registration.data["id"],
                    "client": client})
        self.assertEqual(contact.get()["msisdn"], "+27001")
        self.assertEqual(contact.get()["key"], "knownuuid")
        self.assertEqual(contact.get()["user_account"], "knownaccount")
        self.assertEqual(contact.get()["extra"], {
            "is_registered": "true",
            "is_registered_by": "clinic",
            "language_choice": "en",
            "source_name": "Test Source",
            "sa_id": "8009151234001",
            "clinic_code": "12345",
            "dob": "1980-09-15",
            "last_service_rating": "never",
            "service_rating_reminders": "0",
            "service_rating_reminder": "2014-01-02"
        })

    def test_create_vumi_contact_1(self):
        # make registration for contact with msisdn +27002
        registration = self.make_registration(
            post_data=TEST_REG_DATA["chw_self"])
        client = self.make_client()
        # make different existing contact
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+27001",
            u"user_account": u"knownaccount",
            u"extra": {}
        })

        contact = tasks.update_create_vumi_contact.apply_async(
            kwargs={"registration_id": registration.data["id"],
                    "client": client})
        self.assertEqual(contact.get()["msisdn"], "+27002")
        self.assertEqual(contact.get()["extra"], {
            "is_registered": "true",
            "is_registered_by": "chw",
            "language_choice": "xh",
            "source_name": "Test Source",
            "dob": "1980-10-15",
        })
        self.assertEqual(contact.get()["extra"]["is_registered"], "true")
        self.assertEqual(contact.get()["extra"]["is_registered_by"], "chw")
        self.assertEqual(contact.get()["extra"]["language_choice"], "xh")
        self.assertEqual(contact.get()["extra"]["source_name"], "Test Source")
        self.assertEqual(contact.get()["extra"]["dob"], "1980-10-15")

    def test_create_vumi_contact_2(self):
        # make registration for contact with msisdn +27001
        registration = self.make_registration(
            post_data=TEST_REG_DATA["clinic_hcw"])
        client = self.make_client()
        # make different existing contact
        self.make_existing_contact({
            u"key": u"knownuuid",
            u"msisdn": u"+27005",
            u"user_account": u"knownaccount",
            u"extra": {}
        })

        contact = tasks.update_create_vumi_contact.apply_async(
            kwargs={"registration_id": registration.data["id"],
                    "client": client})
        self.assertEqual(contact.get()["msisdn"], "+27001")
        self.assertEqual(contact.get()["extra"], {
            "is_registered": "true",
            "is_registered_by": "clinic",
            "language_choice": "af",
            "source_name": "Test Source",
            "passport_no": "5551111",
            "passport_origin": "zw",
            "clinic_code": "12345",
            "last_service_rating": "never",
            "service_rating_reminders": "0",
            "service_rating_reminder": "2014-01-02",
            "registered_by": "+27820010001"
        })
        self.assertEqual(contact.get()["extra"]["is_registered"], "true")
        self.assertEqual(contact.get()["extra"]["is_registered_by"], "clinic")
        self.assertEqual(contact.get()["extra"]["language_choice"], "af")
        self.assertEqual(contact.get()["extra"]["source_name"], "Test Source")
