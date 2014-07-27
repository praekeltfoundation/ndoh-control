from celery import task
from celery.utils.log import get_task_logger

from go_http.send import HttpApiSender
from snappy import SnappyApiSender
import control.settings as settings

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
    ## TODO: Log outbound send metric
    return response

@task()
def create_snappy_ticket(ticket):
    # Make a session to Vumi
    snappy_api = SnappyApiSender(
        api_key=settings.SNAPPY_API_KEY
    )
    # Send message
    snappy_ticket = snappy_api.note(settings.SNAPPY_MAILBOX_ID, 
        "Support for %s" % (ticket.msisdn), ticket.message, None, 
        [{"name": ticket.msisdn, "address": settings.SNAPPY_EMAIL}])
    ticket.support_nonce = snappy_ticket
    ticket.save()
    ## TODO: Log ticket created metric
    return True

