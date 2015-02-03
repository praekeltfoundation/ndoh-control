from celery import task
from celery.exceptions import SoftTimeLimitExceeded
from go_http import HttpApiSender
import control.settings as settings
from django.db import connection
import logging
logger = logging.getLogger(__name__)


@task()
def ensure_one_servicerating():
    """
    Fixes issues caused by upstream failures that lead
    to users having multiple recorded serviceratings
    Runs daily
    """
    cursor = connection.cursor()
    cursor.execute("""
        DELETE FROM servicerating_response WHERE contact_id NOT IN
        (SELECT MAX(id) as id FROM servicerating_contact GROUP BY key)
    """)
    affected = cursor.rowcount
    vumi_fire_metric.delay(
        metric="servicerating.duplicates", value=affected, agg="last")
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
        logger.error((
            'Soft time limit exceed processing metric fire to Vumi '
            'HTTP API via Celery'), exc_info=True)
