import json
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_framework import status
from .models import Source, Registration


class APITestCase(TestCase):

    def setUp(self):
        self.adminclient = APIClient()
        self.normalclient = APIClient()


class AuthenticatedAPITestCase(APITestCase):

    def setUp(self):
        super(AuthenticatedAPITestCase, self).setUp()
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


# class TestSourcesAPI(AuthenticatedAPITestCase):

#     def test_create_source(self):
#         post_data = {
#             "name": "Test Source",
#         }
#         response = self.adminclient.post('/api/v1/sources/',
#                                          json.dumps(post_data),
#                                          content_type='application/json')

#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)

#         d = Source.objects.last()
#         self.assertEqual(d.name, 'Test Source')
#         self.assertEqual(d.id, 1)


class TestRegistrationsAPI(AuthenticatedAPITestCase):

    def make_source(self, name="Test Source"):
        post_data = {
            "name": name,
        }
        response = self.adminclient.post('/api/v1/sources/',
                                         json.dumps(post_data),
                                         content_type='application/json')
        return response

    def test_create_source(self):
        response = self.make_source()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Source.objects.last()
        self.assertEqual(d.name, 'Test Source')
        self.assertEqual(d.id, 2)

    def test_create_registration(self):
        source = self.make_source()
        source_id = source.data["id"]

        post_data = {
            "hcw_msisdn": None,
            "mom_msisdn": "+27001",
            "mom_id_type": "sa_id",
            "mom_lang": "en",
            "mom_edd": "2015-08-01",
            "mom_id_no": "8009151234001",
            "mom_dob": None,
            "clinic_code": "12345",
            "authority": "clinic",
            "source": "/api/v1/sources/%s/" % source_id
        }
        response = self.adminclient.post('/api/v1/registrations/',
                                         json.dumps(post_data),
                                         content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Registration.objects.last()
        self.assertEqual(d.id, 1)
