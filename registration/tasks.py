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
        """ The attempted task failed because of a non-200 HTTP return
            code.
        """

    def run(self, registration_id, **kwargs):
        """ Load registration, construct Jembi doc and send it off.
        """
        l = self.get_logger(**kwargs)

        l.info("Compiling Jembi data")
        try:
            registration = Registration.objects.get(pk=registration_id)
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
