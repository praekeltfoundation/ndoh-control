from uuid import UUID
from celery import task
from celery.utils.log import get_task_logger
import requests
import json
import urllib

from go_http.send import HttpApiSender
from go_http.contacts import ContactsApiClient
from besnappy import SnappyApiSender

from django.conf import settings

from snappybouncer.models import Ticket

logger = get_task_logger(__name__)


@task(ignore_result=True)
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


@task(ignore_result=True)
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


@task(ignore_result=True)
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


@task(ignore_result=True)
def create_casepro_ticket(ticket):
    if not getattr(settings, 'CASEPRO_BASE_URL', None):
        return

    casepro_payload = {
        'from': ticket.msisdn,
        'message_id': UUID(int=ticket.pk).hex,
        'content': ticket.message,
    }
    response = requests.post(settings.CASEPRO_BASE_URL, json=casepro_payload)
    response.raise_for_status()

    # NOTE: this should only be updated once Casepro is the defacto helpdesk
    #       backend, otherwise we're just overwriting two backends' values
    # data = response.json()
    # ticket.support_id = data['id']
    # ticket.save()


@task(ignore_result=True)
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
    extra_info += (
        "Manage user subscriptions (opt out, unsubscribe or switch "
        "to baby): %s\n" % optout_url)
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


def extract_tag(tags):
    """
    Takes a list of tags and extracts the first hastagged item
    in the list, returning it as a string without the hashtag.
    eg. ["@person", "#coffee", "#payment"] -> "coffee"
    """
    for tag in tags:
        if tag[0] == "#":
            return tag[1::]
    return None


def extract_operator(tags, operators):
    """
    Takes a list of tags and a dict of operator names mapped to their
    numbers and returns the operator number of the operator name in
    the list of tags.
    eg. ["@barry", "#question"] -> barry's operator number
    """
    for tag in tags:
        if tag[0] == "@":
            return operators[tag[1::]]
    return None


@task(ignore_result=True)
def backfill_ticket(ticket_id, operators):
    """
    Looks up the Ticket's operator number and first tag and saves it
    to the ticket, then fires a follow-up task that saves the faccode
    to the ticket if available.
    """
    # Make a session to Snappy
    snappy_api = SnappyApiSender(
        api_key=settings.SNAPPY_API_KEY,
        api_url=settings.SNAPPY_BASE_URL
    )
    # Get the ticket object
    ticket = Ticket.objects.get(id=ticket_id)
    # Look up the ticket on Snappy (get request)
    response = snappy_api._api_request(
        'GET', 'ticket/%s/' % ticket.support_id).json()
    # Save the operator & tag to the Ticket
    ticket.tag = extract_tag(response["tags"])
    ticket.operator = extract_operator(response["tags"], operators)
    ticket.save()
    # Fire off a task to look up the facility_code on the contact
    backfill_ticket_faccode.delay(ticket_id)

    return "Ticket %s backfilled" % ticket.support_id


def get_ticket_faccode(contact_key):
    """
    Looks up and returns a contact's clinic code extra if they have one.
    """
    contacts_api = ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)
    contact = contacts_api.get_contact(contact_key)
    if "clinic_code" in contact["extra"]:
        return contact["extra"]["clinic_code"]
    return None


@task(ignore_result=True)
def backfill_ticket_faccode(ticket_id):
    """
    Looks up a Ticket contact's clinic code and stores it in the ticket
    """
    # Get the ticket object
    ticket = Ticket.objects.get(id=ticket_id)
    # Get and save the faccode
    ticket.faccode = get_ticket_faccode(ticket.contact_key)
    ticket.save()

    return "Ticket %s faccode backfilled" % ticket.support_id
