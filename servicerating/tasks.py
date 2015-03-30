from celery import task, chain
from celery.exceptions import SoftTimeLimitExceeded
from go_http import HttpApiSender
from go_http.contacts import ContactsApiClient
import control.settings as settings
from django.db import connection
import logging
logger = logging.getLogger(__name__)
from datetime import date

def get_date_filter(date_filter=date.today()):
    return date_filter.strftime("%Y-%m-%d")

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


@task()
def vumi_update_smart_group_query(group_key, query, client=None):
    try:
        if client is None:
            client = ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)
        group = client.get_group(group_key)
        group[u"query"] = query
        group.pop(u"key")  # remove key from existing dict before submission
        update = client.update_group(group_key, group)
        return update["key"]
    except SoftTimeLimitExceeded:
        logger.error((
            'Soft time limit exceed processing smart group update to Vumi '
            'HTTP API via Celery'), exc_info=True)

@task()
def vumi_get_smart_group_contacts(group_key, client=None):
    try:
        if client is None:
            client = ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)
        contacts = client.group_contacts(group_key)
        return contacts
    except SoftTimeLimitExceeded:
        logger.error((
            'Soft time limit exceed getting smart group contacts from Vumi '
            'HTTP API via Celery'), exc_info=True)

@task()
def send_reminders(group_key, message, client=None):
    try:
        if client is None:
            client = ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)
        query = 'updated-query'
        result = chain(
            vumi_update_smart_group_query.s(group_key, query, client),
            vumi_get_smart_group_contacts.s())()
        return result.get()
    except SoftTimeLimitExceeded:
        logger.error((
            'Soft time limit exceed processing reminders \
             via Celery'), exc_info=True)
