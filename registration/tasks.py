import requests
import json
from datetime import datetime
from celery import task
from celery.task import Task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from go_http.contacts import ContactsApiClient
from .models import Registration


logger = get_task_logger(__name__)


# class Jembi_Post_Json(Task):
#     """ Task to send registrations to Jembi
#     """
#     name = "registrations.tasks.jembi_post_json"

# class FailedEventRequest(Exception):
#     """ The attempted task failed because of a non-200 HTTP return code.
#     """

def get_timestamp():
    return datetime.today().strftime("%Y%m%d%H%M%S")


def get_dob(mom_dob):
    if mom_dob is not None:
        return mom_dob.strftime("%Y%m%d")
    else:
        return None


def get_subscription_type(authority):
    authority_map = {
        'personal': 1,
        'chw': 2,
        'clinic': 3
    }
    return authority_map[authority]


def get_patient_id(id_type, id_no, passport_origin, mom_msisdn):
    if id_type == 'sa_id':
        return id_no + "^^^ZAF^NI"
    elif id_type == 'passport':
        return id_no + '^^^' + passport_origin.upper() + '^PPN'
    else:
        return mom_msisdn.replace('+', '') + '^^^ZAF^TEL'


def build_jembi_json(registration):
    """ Compile json to be sent to Jembi. """
    json_template = {
        "mha": 1,
        "swt": 1,
        "dmsisdn": registration.hcw_msisdn,
        "cmsisdn": registration.mom_msisdn,
        "id": get_patient_id(
            registration.mom_id_type, registration.mom_id_no,
            registration.mom_passport_origin, registration.mom_msisdn),
        "type": get_subscription_type(registration.authority),
        "lang": registration.mom_lang,
        "encdate": get_timestamp(),
        "faccode": registration.clinic_code,
        "dob": get_dob(registration.mom_dob)
    }

    if registration.authority == 'clinic':
        json_template["edd"] = registration.mom_edd.strftime("%Y%m%d")

    return json_template


def get_tomorrow():
    return (datetime.date.today() + datetime.timedelta(days=1)
            ).strftime("%Y%m%d")


def define_extras(_extras, registration):
    # Set up the new extras
    _extras[u"is_registered"] = "true"
    _extras[u"is_registered_by"] = registration.authority
    _extras[u"language_choice"] = registration.mom_lang
    _extras[u"source_name"] = registration.source.name
    if registration.hcw_msisdn:
        _extras[u"registered_by"] = registration.hcw_msisdn
    if registration.mom_id_type == "sa_id":
        _extras[u"sa_id"] = registration.mom_id_no
    elif registration.mom_id_type == "passport":
        _extras[u"passport_no"] = registration.mom_id_no
        _extras[u"passport_origin"] = registration.mom_passport_origin
    if registration.authority == 'clinic':
        _extras[u"clinic_code"] = registration.clinic_code
        _extras[u"last_service_rating"] = 'never'
        _extras[u"service_rating_reminders"] = '0'
        _extras[u"service_rating_reminder"] = get_tomorrow()
    if registration.mom_id_type != 'passport':
        _extras[u"dob"] = registration.mom_dob.strftime("%Y-%m-%d")

    # sub_type, sub_rate, seq_start? currently saved but not useful?
    # edd? not currently being saved but useful

    return _extras


def update_contact(contact, registration, client):
    # Setup new values - only extras need updating
    existing_extras = contact["extra"]
    _extras = define_extras(existing_extras, registration)
    update_data = {u"extra": _extras}
    return client.update_contact(contact["key"], update_data)


def create_contact(registration, client):
    contact_data = {
        u"msisdn": registration.mom_msisdn
    }
    _extras = define_extras({}, registration)
    contact_data[u"extra"] = _extras
    return client.create_contact(contact_data)


@task()
def jembi_post_json(registration_id):
    """ Task to send registrations to Jembi"""

    logger.info("Compiling Jembi Json data")
    try:
        registration = Registration.objects.get(pk=registration_id)
        json_doc = build_jembi_json(registration)

        try:
            result = requests.post(
                "%s/json/subscription" % settings.JEMBI_BASE_URL,  # url
                headers={'Content-Type': 'application/json'},
                data=json.dumps(json_doc),
                auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
                verify=False
            )
            return result.text
        except:
            logger.error('Problem connecting to Jembi', exc_info=True)

    except ObjectDoesNotExist:
        logger.error('Missing Registration object', exc_info=True)

    except SoftTimeLimitExceeded:
        logger.error(
            'Soft time limit exceeded processing Jembi send via Celery.',
            exc_info=True)


@task()
def update_create_vumi_contact(registration_id, client=None):
    """ Task to update or create a Vumi contact when a registration
        is created.
    """
    try:
        if client is None:
            client = ContactsApiClient(settings.VUMI_GO_API_TOKEN,
                                       api_url=settings.VUMI_GO_BASE_URL)

        # Load the registration
        try:
            registration = Registration.objects.get(pk=registration_id)

            try:
                # Get and update the contact if it exists
                contact = client.get_contact(
                    msisdn=registration.mom_msisdn)
                updated_contact = update_contact(
                    contact, registration, client)
                return updated_contact

            except:
                # Create the contact as it doesn't exist
                contact = create_contact(registration, client)
                return contact

        except ObjectDoesNotExist:
            logger.error('Missing Registration object', exc_info=True)

    except SoftTimeLimitExceeded:
        logger.error(
            'Soft time limit exceeded processing Jembi send via Celery.',
            exc_info=True)
