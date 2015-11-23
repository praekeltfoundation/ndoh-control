from celery import task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from django.db.models import Max
from django.core.exceptions import ObjectDoesNotExist

from go_http.send import HttpApiSender
from requests.exceptions import HTTPError
from go_http.exceptions import UserOptedOutException
import control.settings as settings
from subscription.models import Subscription, Message

logger = get_task_logger(__name__)


@task()
def vumi_fire_metric(metric, value, agg, sender=None):
    try:
        if sender is None:
            sender = HttpApiSender(
                account_key=settings.VUMI_GO_ACCOUNT_KEY,
                conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
                conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
            )
        sender.fire_metric(metric, value, agg=agg)
        return sender
    except SoftTimeLimitExceeded:
        logger.error(
            'Soft time limit exceed processing metric fire to Vumi HTTP API '
            'via Celery',
            exc_info=True)


@task()
def process_message_queue(schedule, sender=None):
    # Get all active and incomplete subscribers for schedule
    subscribers = Subscription.objects.filter(
        schedule=schedule, active=True, completed=False,
        process_status=0).all()

    # Fire off message processor for each
    for subscriber in subscribers:
        subscriber.process_status = 1  # In Proceses
        subscriber.save()
        send_message.delay(subscriber, sender)
        processes_message.delay(subscriber, sender)
    total_sent = subscribers.count()
    vumi_fire_metric.delay(
        metric="%s.sum.sms.subscription.outbound" %
        settings.VUMI_GO_METRICS_PREFIX,
        value=total_sent, agg="sum", sender=sender)
    return total_sent


@task(bind=True, time_limit=10, ignore_result=True)
def send_message(self, subscriber, sender=None):
    try:
        # send message to subscriber
        try:
            # get message to send
            message = Message.objects.get(
                message_set=subscriber.message_set, lang=subscriber.lang,
                sequence_number=subscriber.next_sequence_number)
            # send message
            try:
                if sender is None:
                    sender = HttpApiSender(
                        account_key=settings.VUMI_GO_ACCOUNT_KEY,
                        conversation_key=subscriber.message_set.conv_key,
                        conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
                    )
                response = sender.send_text(subscriber.to_addr,
                                            message.content)
            except UserOptedOutException:
                # user has opted out so deactivate subscription
                subscriber.active = False
                subscriber.save()
                response = ('Subscription deactivated for %s' %
                            subscriber.to_addr)
            except HTTPError as e:
                # retry message sending if in 500 range (3 default retries)
                if 500 < e.response.status_code < 599:
                    raise self.retry(exc=e)
                else:
                    raise e
            return response
        except ObjectDoesNotExist:
            subscriber.process_status = -1  # Errored
            subscriber.save()
            logger.error('Missing subscription message', exc_info=True)
    except SoftTimeLimitExceeded:
        logger.error(
            ('Soft time limit exceed sending message to Vumi'
             ' HTTP API via Celery'), exc_info=True)


@task()
def processes_message(subscriber, sender, ignore_result=True):
    try:
        # Process moving to next message, next set or finished
        try:
            # Get set max
            set_max = Message.objects.filter(
                message_set=subscriber.message_set
            ).aggregate(Max('sequence_number'))["sequence_number__max"]
            # Compare user position to max
            if subscriber.next_sequence_number == set_max:
                # Mark current as completed
                subscriber.completed = True
                subscriber.active = False
                subscriber.process_status = 2  # Completed
                subscriber.save()
                # If next set defined create new subscription
                message_set = subscriber.message_set
                if message_set.next_set:
                    # clone existing minus PK as recommended in
                    # https://docs.djangoproject.com/en/1.6/topics/db/queries/
                    # copying-model-instances
                    subscriber.pk = None
                    subscriber.process_status = 0  # Ready
                    subscriber.active = True
                    subscriber.completed = False
                    subscriber.next_sequence_number = 1
                    subscription = subscriber
                    subscription.message_set = message_set.next_set
                    subscription.schedule = (
                        subscription.message_set.default_schedule)
                    subscription.save()
                    vumi_fire_metric.delay(
                        metric="%s.sum.%s_auto" %
                        (settings.VUMI_GO_METRICS_PREFIX,
                         subscription.message_set.short_name),
                        value=1, agg="sum", sender=sender)
            else:
                # More in this set so interate by one
                subscriber.next_sequence_number = (
                    subscriber.next_sequence_number + 1)
                subscriber.process_status = 0  # Ready
                subscriber.save()
            # return response
            return "Subscription for %s updated" % subscriber.to_addr
        except ObjectDoesNotExist:
            subscriber.process_status = -1  # Errored
            subscriber.save()
            logger.error('Unexpected error', exc_info=True)
    except SoftTimeLimitExceeded:
        logger.error(
            'Soft time limit exceed updating subscription', exc_info=True)
