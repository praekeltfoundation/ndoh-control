from celery import task
from celery.exceptions import SoftTimeLimitExceeded
from go_http import HttpApiSender
import csv
from subscription.models import Message
import control.settings as settings
from django.db import IntegrityError, transaction, connection
import logging
logger = logging.getLogger(__name__)


@task()
def ingest_csv(csv_data, message_set):
    """ Expecting data in the following format:
    message_id,en,safe,af,safe,zu,safe,xh,safe,ve,safe,tn,safe,ts,safe,ss,safe,st,safe,nso,safe,nr,safe
    """
    records = csv.DictReader(csv_data)
    for line in records:
        for key in line:
            # Ignore non-content keys and empty keys
            if key not in ["message_id", "safe"] and line[key] != "":
                try:
                    with transaction.atomic():
                        message = Message()
                        message.message_set = message_set
                        message.sequence_number = line["message_id"]
                        message.lang = key
                        message.content = line[key]
                        message.save()
                except (IntegrityError, ValueError) as e:
                    message = None
                    # crappy CSV data
                    logger.error(e)


@task()
def ensure_one_subscription():
    """ 
    Fixes issues caused by upstream failures
    that lead to users having multiple active subscriptions
    Runs daily
    """
    cursor = connection.cursor()
    cursor.execute("UPDATE subscription_subscription SET active = False WHERE id NOT IN \
              (SELECT MAX(id) as id FROM subscription_subscription GROUP BY to_addr)")
    affected = cursor.rowcount
    vumi_fire_metric.delay(metric="subscription.duplicates", value=affected, agg="last")
    return affected


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
        logger.error('Soft time limit exceed processing metric fire to Vumi HTTP API via Celery', exc_info=True)
