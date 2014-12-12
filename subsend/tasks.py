from celery import task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from django.db.models import Max
from django.core.exceptions import ObjectDoesNotExist

from go_http.send import HttpApiSender, LoggingSender
import control.settings as settings
from subscription.models import Subscription, Message
from djcelery.models import PeriodicTask

logger = get_task_logger(__name__)


@task()
def process_message_queue(schedule, sender=None):
    # Get all active and incomplete subscribers for schedule
    subscribers = Subscription.objects.filter(
        schedule=schedule, active=True, completed=False, process_status=0).all()

    # Make a reusable session to Vumi
    if sender is None:
        sender = HttpApiSender(
            account_key=settings.VUMI_GO_ACCOUNT_KEY,
            conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
            conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
        )
        # sender = LoggingSender('go_http.test')
            # Fire off message processor for each
    for subscriber in subscribers:
        subscriber.process_status = 1 # In Proceses
        subscriber.save()
        processes_message.delay(subscriber, sender)
    return subscribers.count()

@task()
def processes_message(subscriber, sender):
    try:
        # Get next message
        try:
            message = Message.objects.get(
                message_set=subscriber.message_set, lang=subscriber.lang,
                sequence_number=subscriber.next_sequence_number)
            # Send message
            response = sender.send_text(subscriber.to_addr, message.content)
            # Post process moving to next message, next set or finished
            # Get set max
            set_max = Message.objects.filter(
                message_set=subscriber.message_set
                ).aggregate(Max('sequence_number'))["sequence_number__max"]
            # Compare user position to max
            if subscriber.next_sequence_number == set_max:
                # Mark current as completed
                subscriber.completed = True
                subscriber.active = False
                subscriber.process_status = 2 # Completed
                subscriber.save()
                # If next set defined create new subscription
                message_set = subscriber.message_set
                if message_set.next_set:
                    # clone existing minus PK as recommended in
                    # https://docs.djangoproject.com/en/1.6/topics/db/queries/#copying-model-instances
                    subscriber.pk = None
                    subscriber.process_status = 0 # Ready
                    subscriber.active = True
                    subscriber.completed = False
                    subscriber.next_sequence_number = 1
                    subscription = subscriber
                    subscription.message_set = message_set.next_set
                    subscription.schedule = message_set.default_schedule
                    subscription.save()
            else:
                # More in this set so interate by one
                subscriber.next_sequence_number = subscriber.next_sequence_number + 1
                subscriber.process_status = 0 # Ready
                subscriber.save()
            return response
        except ObjectDoesNotExist:
            subscriber.process_status = -1 # Errored
            subscriber.save()
            logger.error('Missing subscription message', exc_info=True)
    except SoftTimeLimitExceeded:
        logger.error('Soft time limit exceed processing message to Vumi HTTP API via Celery', exc_info=True)

