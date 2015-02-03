from celery import task
from celery.exceptions import SoftTimeLimitExceeded
from go_http import HttpApiSender
import csv
from subscription.models import Message, Subscription
import control.settings as settings
from django.db import IntegrityError, transaction, connection
import logging
logger = logging.getLogger(__name__)


@task()
def ingest_csv(csv_data, message_set):
    """ Expecting data in the following format:
    message_id,en,safe,af,safe,zu,safe,xh,safe,ve,safe,tn,safe,ts,safe,
        ss,safe,st,safe,nso,safe,nr,safe
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
    cursor.execute(
        "UPDATE subscription_subscription SET active = False WHERE id NOT IN \
        (SELECT MAX(id) as id FROM subscription_subscription GROUP BY to_addr)"
    )
    affected = cursor.rowcount
    vumi_fire_metric.delay(
        metric="subscription.duplicates", value=affected, agg="last")
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
        logger.error(
            'Soft time limit exceed processing metric fire to Vumi HTTP API '
            'via Celery',
            exc_info=True)


def clean_msisdn(msisdn):
    if msisdn.strip()[0] == "+":
        return msisdn.strip()
    else:
        return "+%s" % (msisdn.strip())


@task()
def ingest_opt_opts_csv(csv_data):
    """ Expecting data in the following format:
    # CSV file format
    # Address Type, Address, Message ID, Timestamp
    #============================================
    # msisdn, +2712345678, 9943d8b8d9ba4fd086fceb43ecc6138d,
    #     2014-09-22 12:21:44.901527
    """
    records = csv.DictReader(csv_data)
    msisdns = []
    for line in records:
        # build a list of affected users
        if "Address Type" in line \
                and " Address" in line \
                and line["Address Type"] == "msisdn":

            msisdn = clean_msisdn(line[" Address"])
            msisdns.append(msisdn)
    subs = Subscription.objects.filter(to_addr__in=msisdns).filter(
        active=True).update(active=False)
    # return affected count
    return subs
