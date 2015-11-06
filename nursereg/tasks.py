import requests
import json
from requests.exceptions import HTTPError
from datetime import datetime, timedelta
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from celery import task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from djcelery.models import PeriodicTask
from go_http import HttpApiSender
from go_http.contacts import ContactsApiClient
from .models import NurseReg
from subscription.models import Subscription, MessageSet

logger = get_task_logger(__name__)


def get_patient_id(id_type, id_no=None, passport_origin=None, mom_msisdn=None):
    if id_type == 'sa_id':
        return id_no + "^^^ZAF^NI"
    elif id_type == 'passport':
        return id_no + '^^^' + passport_origin.upper() + '^PPN'
    else:
        return mom_msisdn.replace('+', '') + '^^^ZAF^TEL'


def get_subscription_type(authority):
    authority_map = {
        'personal': 1,
        'chw': 2,
        'clinic': 3
    }
    return authority_map[authority]


def get_today():
    return datetime.today()


def get_timestamp():
    return get_today().strftime("%Y%m%d%H%M%S")


def get_dob(mom_dob):
    if mom_dob is not None:
        return mom_dob.strftime("%Y%m%d")
    else:
        return None


def get_sender():
    sender = HttpApiSender(
        account_key=settings.VUMI_GO_ACCOUNT_KEY,
        conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
        conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
    )
    return sender


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

    # Self registrations on all lines should use cmsisdn as dmsisdn too
    if registration.hcw_msisdn is None:
        json_template["dmsisdn"] = registration.mom_msisdn

    if registration.authority == 'clinic':
        json_template["edd"] = registration.mom_edd.strftime("%Y%m%d")

    return json_template


@task(time_limit=10)
def jembi_post_json(registration_id, sender=None):
    """ Task to send registrations Json to Jembi"""

    logger.info("Compiling Jembi Json data")
    try:
        registration = NurseReg.objects.get(pk=registration_id)
        json_doc = build_jembi_json(registration)

        try:
            result = requests.post(
                "%s/subscription" % settings.JEMBI_BASE_URL,  # url
                headers={'Content-Type': 'application/json'},
                data=json.dumps(json_doc),
                auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
                verify=False
            )
            result.raise_for_status()
            vumi_fire_metric.apply_async(
                kwargs={
                    "metric": u"%s.%s.sum.json_to_jembi_success" % (
                        settings.METRIC_ENV, registration.authority),
                    "value": 1,
                    "agg": "sum",
                    "sender": sender}
            )
        except HTTPError as e:
            # retry message sending if in 500 range (3 default retries)
            if 500 < e.response.status_code < 599:
                if jembi_post_json.max_retries == \
                   jembi_post_json.request.retries:
                    vumi_fire_metric.apply_async(
                        kwargs={
                            "metric": u"%s.%s.sum.json_to_jembi_fail" % (
                                settings.METRIC_ENV, registration.authority),
                            "value": 1,
                            "agg": "sum",
                            "sender": None}
                    )
                raise jembi_post_json.retry(exc=e)
            else:
                vumi_fire_metric.apply_async(
                    kwargs={
                        "metric": u"%s.%s.sum.json_to_jembi_fail" % (
                            settings.METRIC_ENV, registration.authority),
                        "value": 1,
                        "agg": "sum",
                        "sender": None}
                )
                raise e
        except:
            logger.error('Problem posting JSON to Jembi', exc_info=True)
        return result.text

    except ObjectDoesNotExist:
        logger.error('Missing NurseReg object', exc_info=True)

    except SoftTimeLimitExceeded:
        logger.error(
            'Soft time limit exceeded processing Jembi send via Celery.',
            exc_info=True)


def get_client():
    return ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)


def define_extras_subscription(_extras, subscription):
    # Set up the new extras
    _extras[u"subscription_type"] = str(subscription.message_set.id)
    _extras[u"subscription_rate"] = str(subscription.schedule.id)
    _extras[u"subscription_seq_start"] = str(subscription.next_sequence_number)
    return _extras


def get_tomorrow():
    return (get_today() + timedelta(days=1)
            ).strftime("%Y-%m-%d")


def define_extras_registration(_extras, registration):
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
        _extras[u"edd"] = registration.mom_edd.strftime("%Y-%m-%d")
        _extras[u"due_date_year"] = registration.mom_edd.strftime("%Y")
        _extras[u"due_date_month"] = registration.mom_edd.strftime("%m")
        _extras[u"due_date_day"] = registration.mom_edd.strftime("%d")
    if (registration.mom_id_type != 'passport' and
            registration.mom_dob is not None):
        _extras[u"dob"] = registration.mom_dob.strftime("%Y-%m-%d")

    return _extras


def update_contact_registration(contact, registration, client):
    # Setup new values - only extras need updating
    existing_extras = contact["extra"]
    _extras = define_extras_registration(existing_extras, registration)

    groups = contact["groups"]
    groups.append(settings.LANG_GROUP_KEYS[registration.mom_lang])

    update_data = {u"extra": _extras,
                   u"groups": groups}
    return client.update_contact(contact["key"], update_data)


def update_contact_subscription(contact, subscription, client):
    # Setup new values - only extras need updating
    existing_extras = contact["extra"]
    _extras = define_extras_subscription(existing_extras, subscription)
    update_data = {u"extra": _extras}
    return client.update_contact(contact["key"], update_data)


def get_pregnancy_week(today, edd):
    """ Calculate how far along the mother's prenancy is in weeks. """
    due_date = datetime.strptime(edd, "%Y-%m-%d")
    time_diff = due_date - today
    time_diff_weeks = time_diff.days / 7
    preg_weeks = 40 - time_diff_weeks
    # You can't be less than two week pregnant
    if preg_weeks <= 1:
        preg_weeks = 2  # changed from JS's 'false' to achieve same result
    return preg_weeks


def clinic_sub_map(weeks):
    """ Calculate clinic message set, sending rate & starting point. """

    # Set commonly used values
    msg_set = "accelerated"
    seq_start = 1

    # Calculate specific values
    if weeks <= 4:
        msg_set = "standard"
        sub_rate = "two_per_week"
    elif weeks <= 31:
        msg_set = "standard"
        sub_rate = "two_per_week"
        seq_start = ((weeks-4)*2)-1
    elif weeks <= 35:
        msg_set = "later"
        sub_rate = "three_per_week"
        seq_start = ((weeks-30)*3)-2
    elif weeks == 36:
        sub_rate = "three_per_week"
    elif weeks == 37:
        sub_rate = "four_per_week"
    elif weeks == 38:
        sub_rate = "five_per_week"
    else:
        sub_rate = "daily"

    return msg_set, sub_rate, seq_start


def get_subscription_details(contact):
    msg_set = None,
    sub_rate = "two_per_week"
    seq_start = 1
    if contact["extra"]["is_registered_by"] == "personal":
        msg_set = "subscription"
    if contact["extra"]["is_registered_by"] == "chw":
        msg_set = "chw"
    if contact["extra"]["is_registered_by"] == "clinic":
        preg_weeks = get_pregnancy_week(get_today(), contact["extra"]["edd"])
        msg_set, sub_rate, seq_start = clinic_sub_map(preg_weeks)

    return msg_set, sub_rate, seq_start


def create_subscription(contact, authority, sender=None):
    """ Create new Control messaging subscription"""

    logger.info("Creating new Control messaging subscription")
    try:
        sub_details = get_subscription_details(contact)

        subscription = Subscription(
            contact_key=contact["key"],
            to_addr=contact["msisdn"],
            user_account=contact["user_account"],
            lang=contact["extra"]["language_choice"],
            message_set=MessageSet.objects.get(short_name=sub_details[0]),
            schedule=PeriodicTask.objects.get(
                id=settings.SUBSCRIPTION_RATES[sub_details[1]]),
            next_sequence_number=sub_details[2],
        )
        subscription.save()
        logger.info("Created subscription for %s" % subscription.to_addr)

        vumi_fire_metric.apply_async(
            kwargs={
                "metric": u"%s.sum.subscriptions" % (
                    settings.METRIC_ENV),
                "value": 1,
                "agg": "sum",
                "sender": sender}
        )
        vumi_fire_metric.apply_async(
            kwargs={
                "metric": u"%s.%s.sum.subscription_to_protocol_success" % (
                    settings.METRIC_ENV, authority),
                "value": 1,
                "agg": "sum",
                "sender": sender}
        )

        return subscription

    except:
        vumi_fire_metric.apply_async(
            kwargs={
                "metric": u"%s.%s.sum.subscription_to_protocol_fail" % (
                    settings.METRIC_ENV, authority),
                "value": 1,
                "agg": "sum",
                "sender": sender}
        )
        logger.error(
            'Error creating Subscription instance',
            exc_info=True)


def create_contact(registration, client):
    contact_data = {
        u"msisdn": registration.mom_msisdn,
        u"groups": [settings.LANG_GROUP_KEYS[registration.mom_lang]]
    }
    _extras = define_extras_registration({}, registration)
    contact_data[u"extra"] = _extras
    return client.create_contact(contact_data)


@task(time_limit=10)
def update_create_vumi_contact(registration_id, client=None, sender=None):
    """ Task to update or create a Vumi contact when a registration
        is created.
    """
    logger.info("Creating / Updating Contact")
    try:
        if client is None:
            client = get_client()

        # Load the registration
        try:
            registration = NurseReg.objects.get(pk=registration_id)

            try:
                # Get and update the contact if it exists
                contact = client.get_contact(
                    msisdn=registration.mom_msisdn)

                logger.info("Contact exists - updating contact")
                updated_contact = update_contact_registration(
                    contact, registration, client)

                # Create new subscription for the contact
                subscription = create_subscription(
                    updated_contact, registration.authority, sender)

                # Update the contact with subscription details
                updated_contact = update_contact_subscription(
                    contact, subscription, client)

            # This exception should rather look for a 404 if the contact is
            # not found, but currently a 400 Bad Request is returned.
            except HTTPError as e:
                if e.response.status_code == 400:
                    # Create the contact as it doesn't exist
                    logger.info("Contact doesn't exist - creating new contact")
                    contact = create_contact(registration, client)

                    # Create new subscription for the contact
                    subscription = create_subscription(
                        contact, registration.authority, sender)

                    # Update the contact with subscription details
                    updated_contact = update_contact_subscription(
                        contact, subscription, client)

                elif 500 < e.response.status_code < 599:
                    # Retry task if 500 error
                    raise update_create_vumi_contact.retry(exc=e)
                else:
                    raise e
            except:
                logger.error('Problem contacting http_api', exc_info=True)

            return updated_contact

        except ObjectDoesNotExist:
            logger.error('Missing Registration object', exc_info=True)

    except SoftTimeLimitExceeded:
        logger.error(
            'Soft time limit exceeded processing Jembi send via Celery.',
            exc_info=True)


@task()
def vumi_fire_metric(metric, value, agg, sender=None):
    try:
        if sender is None:
            sender = get_sender()
        sender.fire_metric(metric, value, agg=agg)
        return sender
    except SoftTimeLimitExceeded:
        logger.error(
            'Soft time limit exceed processing metric fire to Vumi HTTP API '
            'via Celery',
            exc_info=True)
