from celery import task, chain
from celery.exceptions import SoftTimeLimitExceeded
from go_http import HttpApiSender
from go_http.contacts import ContactsApiClient
import control.settings as settings
from django.db import connection
import logging
logger = logging.getLogger(__name__)
from datetime import date, timedelta
from requests import HTTPError


def get_today():
    return date.today()


def get_date_filter(date_filter=None):
    # for getting the provided date in expected string format for extras lookup
    if date_filter is None:
        date_filter = get_today()
    return date_filter.strftime("%Y-%m-%d")


def get_future_date(days, date_current=None):
    # for setting up when next reminder sent
    if date_current is None:
        date_current = get_today()
    future_date = date_current + timedelta(days=days)
    return future_date.strftime("%Y-%m-%d")


@task(ignore_result=True)
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


@task(ignore_result=True)
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


@task(ignore_result=True)
def vumi_send_message(contact_key, message, client=None, sender=None):
    try:
        if client is None:
            client = ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)
        if sender is None:
            sender = HttpApiSender(
                account_key=settings.VUMI_GO_ACCOUNT_KEY,
                conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
                conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
            )
        # get contact
        try:
            contact = client.get_contact(contact_key)
        except HTTPError as err:
            if err.response.status_code == 404:
                logger.error('Contact not found')
            else:
                logger.error('Contacts API error: %s' % err.response.content)
            return False
        # Send message
        try:
            sender.send_text(contact["msisdn"], message)
        except HTTPError as err:
            if err.response.status_code == 404:
                logger.error('Contact not found')
            else:
                logger.error('HTTP API send_text error: %s' %
                             err.response.content)
        # return the contact key for the next chained task
        return contact_key
    except SoftTimeLimitExceeded:
        logger.error((
            'Soft time limit exceed sending message to Vumi '
            'HTTP API via Celery'), exc_info=True)


@task(ignore_result=True)
def vumi_update_contact_extras(contact_key, updates, client=None):
    try:
        if client is None:
            client = ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)
        contact = client.get_contact(contact_key)
        for k, v in updates.iteritems():
            contact["extra"][k] = v
        contact.pop(u"key")  # remove key from existing dict before submission
        contact.pop(u"$VERSION")
        update = client.update_contact(contact_key, contact)
        return update["key"]
    except SoftTimeLimitExceeded:
        logger.error((
            'Soft time limit exceed processing contact extras update to Vumi '
            'HTTP API via Celery'), exc_info=True)


@task(ignore_result=True)
def vumi_update_smart_group_query(group_key, query, client=None):
    try:
        if client is None:
            client = ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)
        group = client.get_group(group_key)
        group[u"query"] = query
        group.pop(u"key")  # remove key from existing dict before submission
        group.pop(u"created_at")
        group.pop(u"$VERSION")
        update = client.update_group(group_key, group)
        return update["key"]
    except SoftTimeLimitExceeded:
        logger.error((
            'Soft time limit exceed processing smart group update to Vumi '
            'HTTP API via Celery'), exc_info=True)


@task(ignore_result=True)
def vumi_get_smart_group_contacts(group_key, client=None):
    try:
        if client is None:
            client = ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)
        contacts = client.group_contacts(group_key)
        return list(contacts)
    except SoftTimeLimitExceeded:
        logger.error((
            'Soft time limit exceed getting smart group contacts from Vumi '
            'HTTP API via Celery'), exc_info=True)


@task(ignore_result=True)
def send_reminders(group_key, client=None, sender=None):
    try:
        reminder = (
            "Thank you for registering. We can only improve if we get "
            "your feedback. Please dial *134*550*4# to rate the "
            "service you received at the clinic you registered at")
        today = get_date_filter()
        if client is not None:  # test mode because Fake doesn't support extra
            query = "name:Nancy"
        else:
            query = ("extras-service_rating_reminder:%s AND "
                     "extras-last_service_rating:never" % today)
        if client is None:
            client = ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)
        contacts = chain(
            vumi_update_smart_group_query.s(group_key, query, client),
            vumi_get_smart_group_contacts.s(client))().get()
        affected = 0
        for contact in contacts:
            affected += 1
            # prepare the contact update if the send message works
            update = {}
            if "service_rating_reminders" in contact["extra"]:
                reminders = int(
                    contact["extra"]["service_rating_reminders"]) + 1
            else:
                reminders = 1
            update["service_rating_reminders"] = unicode(reminders)
            if reminders < 2:  # set a future reminder date
                update["service_rating_reminder"] = get_future_date(7)

            # fire the send message task and contact update chain
            chain(
                vumi_send_message.s(contact["key"], reminder, client=client,
                                    sender=sender),
                vumi_update_contact_extras.s(update, client=client)
            )()

        return "Reminders sent: %s" % affected
    except SoftTimeLimitExceeded:
        logger.error((
            'Soft time limit exceed processing reminders \
             via Celery'), exc_info=True)
