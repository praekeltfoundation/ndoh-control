from celery import task
from celery.utils.log import get_task_logger
import requests
import json
import urllib

from go_http.send import HttpApiSender
from go_http.contacts import ContactsApiClient
from besnappy import SnappyApiSender

from django.conf import settings

logger = get_task_logger(__name__)


@task()
def send_helpdesk_response(ticket):
    # Make a session to Vumi
    sender = HttpApiSender(
        account_key=settings.VUMI_GO_ACCOUNT_KEY,
        conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
        conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
    )
    # Send message
    response = sender.send_text(ticket.msisdn, ticket.response)
    # TODO: Log outbound send metric
    return response


def jembi_format_date(date):
    return date.strftime("%Y%m%d%H%M%S")


def build_jembi_helpdesk_json(ticket):
    json_template = {
        "encdate": jembi_format_date(ticket.created_at),
        "repdate": jembi_format_date(ticket.updated_at),
        "mha": 1,
        "swt": 2,  # 1 ussd, 2 sms
        "cmsisdn": ticket.msisdn,
        "dmsisdn": ticket.msisdn,
        "faccode": str(ticket.faccode),
        "data": {
            "question": ticket.message,
            "answer": ticket.response
        },
        "class": ticket.tag,
        "type": 7,  # 7 helpdesk
        "op": str(ticket.operator)
    }
    return json_template


@task()
def send_helpdesk_response_jembi(ticket):
    data = build_jembi_helpdesk_json(ticket)
    api_url = ("%s/helpdesk" % settings.JEMBI_BASE_URL)
    headers = {
        'Content-Type': 'application/json'
    }
    result = requests.post(api_url, headers=headers, data=json.dumps(data),
                           auth=(settings.JEMBI_USERNAME,
                                 settings.JEMBI_PASSWORD),
                           verify=False)
    return result.text


@task()
def create_snappy_ticket(ticket):
    # Make a session to Snappy
    snappy_api = SnappyApiSender(
        api_key=settings.SNAPPY_API_KEY,
        api_url=settings.SNAPPY_BASE_URL
    )
    # Send message
    subject = "Support for %s" % (ticket.msisdn)
    snappy_ticket = snappy_api.create_note(
        mailbox_id=settings.SNAPPY_MAILBOX_ID,
        subject=subject,
        message=ticket.message,
        to_addr=None,
        from_addr=[{"name": ticket.msisdn, "address": settings.SNAPPY_EMAIL}]
    )
    ticket.support_nonce = snappy_ticket
    ticket.save()
    update_snappy_ticket_with_extras.delay(snappy_api, ticket.support_nonce,
                                           ticket.contact_key, subject)
    # TODO: Log ticket created metric
    return True


@task()
def update_snappy_ticket_with_extras(snappy_api, nonce, contact_key, subject):
    # Gets more extras from Vumi and creates a private note with them
    contacts_api = ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)
    contact = contacts_api.get_contact(contact_key)
    extra_info = ""
    for extra in settings.SNAPPY_EXTRAS:
        # Add available contact extras
        if extra in contact["extra"]:
            extra_info += extra + ": " + contact["extra"][extra] + "\n"
    # Add opt-out link
    optout_url = settings.SITE_DOMAIN_URL + \
        "/controlinterface/subscription/?msisdn=" + \
        urllib.quote_plus(contact["msisdn"])
    extra_info += "Opt this user out: " + optout_url + "\n"
    # Send private note
    snappy_api.create_note(
        mailbox_id=settings.SNAPPY_MAILBOX_ID,
        subject=subject,
        message=extra_info,
        to_addr=[{
            "name": "Internal Information",
            "address": settings.SNAPPY_EMAIL}],
        ticket_id=nonce,
        scope="private",
        staff_id=settings.SNAPPY_STAFF_ID
    )
    return True


@task()
def backfill_ticket(ticket_id):
    """
    Does stuff!
    """
    return True
