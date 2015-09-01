from celery.task import Task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from django.core.exceptions import ObjectDoesNotExist
from .models import Registration

logger = get_task_logger(__name__)


class Jembi_Post(Task):
    """ Task to send registrations to Jembi
    """
    name = "registrations.tasks.Jembi_Post"

    class FailedEventRequest(Exception):
        """ The attempted task failed because of a non-200 HTTP return code.
        """

    def get_timestamp(self):
        return

    def get_subscription_type(self, edd):
        return

    def build_jembi_json(self, registration):
        """ Compile json to be sent to Jembi. """

        json_template = {
            "mha": 1,
            "swt": 1,
            "dmsisdn": registration.hcw_msisdn,
            "cmsisdn": registration.mom_msisdn,
            "id": registration.mom_id_no,
            "type": self.get_subscription_type(registration),
            "lang": registration.mom_lang,
            "encdate": self.get_timestamp(),
            "faccode": registration.clinic_code,
            "dob": registration.mom_dob
        }

        if registration.authority == 'clinic':
            json_template["edd"] = registration.mom_edd

        return json_template

    def run(self, registration_id, **kwargs):
        """ Load registration, construct Jembi doc(s) and send it off. """
        l = self.get_logger(**kwargs)

        l.info("Compiling Jembi data")
        try:
            json_doc = dict()
            registration = Registration.objects.get(pk=registration_id)
            if registration.authority == 'personal':
                json_doc = self.build_jembi_json(registration)

            print json_doc

            print registration.id
            print registration.mom_edd
            print registration.mom_msisdn

        except ObjectDoesNotExist:
            logger.error('Missing Report object', exc_info=True)

        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceeded processing Jembi send via Celery.',
                exc_info=True)

jembi_post = Jembi_Post()
