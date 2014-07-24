from celery import task
from celery.utils.log import get_task_logger
from django.db.models import Max

from go_http.send import HttpApiSender
import control.settings as settings
from subscription.models import Subscription, Message

logger = get_task_logger(__name__)


@task()
def process_message_queue(schedule):
    # Get all active and incomplete subscribers for schedule
    with Subscription.objects.filter(
        schedule=schedule, active=True, completed=False).all() as subscribers:
        if subscribers.exists():
            # Make a reusable session to Vumi
            sender = HttpApiSender(
                account_key=settings.VUMI_GO_ACCOUNT_KEY,
                conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
                conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
            )
            # Fire off message processor for each
            for subscriber in subscribers:
                processes_message.delay(subscriber, sender)
        return subscribers.__len__()

@task()
def processes_message(subscriber, sender):
    # Get next message
    message = Message.objects.get(
        message_set=subscriber.message_set, lang=subscriber.lang, 
        sequence_number=subscriber.next_sequence_number)
    # Send message
    response = sender.send_text(subscriber.to_addr, message.content)
    # Post process moving to next message, next set or finished
    advance_to_next.delay(subscriber)
    return response

@task()
def advance_to_next(subscriber):
    # Get set max
    set_max = Message.objects.all().aggregate(Max('sequence_number'))["sequence_number__max"]
    # Compare user position to max
    if subscriber.next_sequence_number == set_max:
        # Mark current as completed
        subscriber.completed = True
        subscriber.active = False
        subscriber.save()
        # If next set defined create new subscription
        message_set = subscriber.message_set
        if message_set.next_set:
            # clone existing minus PK as recommended in 
            # https://docs.djangoproject.com/en/1.6/topics/db/queries/#copying-model-instances
            subscriber.pk = None
            subscription = subscriber
            subscription.message_set = message_set.next_set
            subscription.save()
    else:
        # More in this set so interate by one
        subscriber.next_sequence_number = subscriber.next_sequence_number + 1
        subscriber.save()
