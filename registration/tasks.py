import requests
import json

from datetime import datetime
from celery.task import Task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from .models import Registration

logger = get_task_logger(__name__)


class Jembi_Post_Json(Task):
    """ Task to send registrations to Jembi
    """
    name = "registrations.tasks.Jembi_Post_Json"

    class FailedEventRequest(Exception):
        """ The attempted task failed because of a non-200 HTTP return code.
        """

    def get_timestamp(self):
        if settings.TESTING_TIMESTAMP:
            return settings.TESTING_TIMESTAMP
        else:
            return datetime.today().strftime("%Y%m%d%H%M%S")

    def get_dob(self, mom_dob):
        if type(mom_dob) == str:
            return mom_dob.strftime("%Y%m%d")
        else:
            return None

    def get_subscription_type(self, authority):
        authority_map = {
            'personal': 1,
            'chw': 2,
            'clinic': 3
        }
        return authority_map[authority]

    def build_jembi_json(self, registration):
        """ Compile json to be sent to Jembi. """

        json_template = {
            "mha": 1,
            "swt": 1,
            "dmsisdn": registration.hcw_msisdn,
            "cmsisdn": registration.mom_msisdn,
            "id": registration.mom_id_no,
            "type": self.get_subscription_type(registration.authority),
            "lang": registration.mom_lang,
            "encdate": self.get_timestamp(),
            "faccode": registration.clinic_code,
            "dob": self.get_dob(registration.mom_dob)
        }

        if registration.authority == 'clinic':
            json_template["edd"] = registration.mom_edd.strftime("%Y%m%d")

        return json_template

    def run(self, registration_id, **kwargs):
        """ Load registration, construct Jembi doc(s) and send it off. """
        l = self.get_logger(**kwargs)

        l.info("Compiling Jembi data")
        try:
            registration = Registration.objects.get(pk=registration_id)
            json_doc = self.build_jembi_json(registration)

            result = requests.post(
                "%s/json/subscription" % settings.JEMBI_BASE_URL,  # url
                headers={'Content-Type': 'application/json'},
                data=json.dumps(json_doc),
                auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
                verify=False
            )
            return result.text

        except ObjectDoesNotExist:
            logger.error('Missing Registration object', exc_info=True)

        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceeded processing Jembi send via Celery.',
                exc_info=True)

jembi_post_json = Jembi_Post_Json()
