import requests
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from celery import task
from lxml import etree
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from django.core.exceptions import ObjectDoesNotExist
from requests.exceptions import HTTPError
from django.conf import settings
from go_http.contacts import ContactsApiClient
from go_http import HttpApiSender
from .models import Registration
from djcelery.models import PeriodicTask
from subscription.models import Subscription, MessageSet


logger = get_task_logger(__name__)


def get_client():
    return ContactsApiClient(auth_token=settings.VUMI_GO_API_TOKEN)


def get_sender():
    sender = HttpApiSender(
        account_key=settings.VUMI_GO_ACCOUNT_KEY,
        conversation_key=settings.VUMI_GO_CONVERSATION_KEY,
        conversation_token=settings.VUMI_GO_ACCOUNT_TOKEN
    )
    return sender


def get_today():
    return datetime.today()


def get_tomorrow():
    return (get_today() + timedelta(days=1)
            ).strftime("%Y-%m-%d")


def get_timestamp():
    return get_today().strftime("%Y%m%d%H%M%S")


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


def get_patient_id(id_type, id_no=None, passport_origin=None, mom_msisdn=None):
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

    # Self registrations on all lines should use cmsisdn as dmsisdn too
    if registration.hcw_msisdn is None:
        json_template["dmsisdn"] = registration.mom_msisdn

    if registration.authority == 'clinic':
        json_template["edd"] = registration.mom_edd.strftime("%Y%m%d")

    return json_template


def get_uuid():
    return '%s' % uuid.uuid4()


def get_oid():
    return '2.25.%s' % uuid.uuid4().int


def get_clinic_code(clinic_code):
    if clinic_code:
        return clinic_code
    else:
        # Temp hardcode instructed
        return '11399'


def get_pregnancy_code(authority):
    if authority == 'chw':
        return '102874004'
    else:
        return '77386006'


def get_preg_display_name(authority):
    if authority == 'chw':
        return 'Unconfirmed pregnancy'
    else:
        return 'Pregnancy confirmed'


def get_due_date(edd):
    if edd:
        return edd.strftime("%Y%m%d")
    else:
        return '17000101'


def prep_xml_strings(registration):
    uuid = get_uuid()
    patient_id = get_patient_id(
        registration.mom_id_type, registration.mom_id_no,
        registration.mom_passport_origin, registration.mom_msisdn)
    contact_msisdn = registration.mom_msisdn
    birth_time = get_dob(registration.mom_dob)
    lang_code = registration.mom_lang
    hcw_cell_number = registration.hcw_msisdn
    clinic_code = get_clinic_code(registration.clinic_code)
    author_timestamp = get_timestamp()
    effective_timestamp = get_timestamp()
    app_code = 'PF'
    app_name = 'Vumi'
    preg_status_code = get_pregnancy_code(registration.authority)
    preg_display_name = get_preg_display_name(registration.authority)
    due_date = get_due_date(registration.mom_edd)

    return (uuid, patient_id, contact_msisdn, birth_time, lang_code,
            hcw_cell_number, clinic_code, author_timestamp,
            effective_timestamp, app_code, app_name, preg_status_code,
            preg_display_name, due_date)


def build_jembi_xml(registration):
    xml_strings = prep_xml_strings(registration)
    cda = make_cda(*xml_strings)
    return cda


def make_cda(record_uuid, patient_id, contact_msisdn, birth_time, lang_code,
             hcw_cell_number, clinic_code, author_timestamp,
             effective_timestamp, app_code, app_name, preg_status_code,
             preg_display_name, due_date):

    tree = etree.parse('registration/CDA_template.xml')
    root = tree.getroot()

    # # id uniqueId
    root_id = root.find('id')
    root_id.set('root', record_uuid)

    record_target_element = root.find('recordTarget')
    patient_role_element = record_target_element.find('patientRole')

    # id patient
    patient_id_element = patient_role_element.find('id')
    patient_id_element.set('extension', patient_id)

    # patient cell number
    contact_msisdn_element = patient_role_element.find('telecom')
    contact_msisdn_element.set('value', "tel:%s" % contact_msisdn)

    # birth time
    patient_element = patient_role_element.find('patient')
    birth_time_element = patient_element.find('birthTime')
    if birth_time is not None:
        birth_time_element.set('value', birth_time)
    else:
        birth_time_element.set('nullFlavor', "NI")

    # language code
    lang_comm_element = patient_element.find('languageCommunication')
    lang_code_element = lang_comm_element.find('languageCode')
    lang_code_element.set('code', lang_code)

    # hcw cell number
    hcw_author_element = root.find('author')
    assigned_author_element = hcw_author_element.find('assignedAuthor')
    hcw_msisdn_element = assigned_author_element.find('telecom')
    if hcw_cell_number is not None:
        hcw_msisdn_element.set('value', "tel:%s" % hcw_cell_number)
    else:
        hcw_msisdn_element.set('nullFlavor', "NI")

    # id clinic
    rep_org_element = assigned_author_element.find('representedOrganization')
    clinic_code_element = rep_org_element.find('id')
    clinic_code_element.set('extension', clinic_code)

    # author time
    for time_element in root.iter('time'):
        time_element.set('value', author_timestamp)

    # effective time
    for effective_time_element in root.iter('effectiveTime'):
        effective_time_element.set('value', effective_timestamp)

    # application code & software name
    for authoring_device_element in root.iter('assignedAuthoringDevice'):
        application_code_element = authoring_device_element.find('code')
        application_code_element.set('code', app_code)
        software_name_element = authoring_device_element.find('softwareName')
        software_name_element.text = app_name

    # pregnancy status code, pregnancy display name, due date
    for entry_element in root.iter('entry'):
        observation_element = entry_element.find('observation')
        value_element = observation_element.find('value')
        value_element.set('code', preg_status_code)
        value_element.set('displayName', preg_display_name)

        entry_relationship_element = \
            observation_element.find('entryRelationship')
        for value_element in entry_relationship_element.iter('value'):
            value_element.set('value', due_date)

    root.set("xmlns", "urn:hl7-org:v3")

    return etree.tostring(tree, pretty_print=True, encoding='UTF-8',
                          xml_declaration=True)


def build_multipart_data(boundary, parts):
    response = []
    for part in parts:
        response.append("\n".join([
            '--' + boundary,
            'Content-Disposition: form-data; name="' +
            part["name"] + '"; filename="' + part["file_name"] + '"',
            'Content-Type: ' + part["content_type"],
            '',
            part["body"]
        ]))
    return "\n".join(response)


def build_multipart_parts(json_body, xml_body):
    return [
        {
            "name": "ihe-mhd-metadata",
            "file_name": "MHDMetadata.json",
            "content_type": "application/json",
            "body": json_body
        },
        {
            "name": "content",
            "file_name": "CDARequest.xml",
            "content_type": "text/xml",
            "body": xml_body
        }
    ]


def build_metadata(cda, patient_id, oid, eid):
    shasum = hashlib.sha1()
    shasum.update(cda)

    return {
        "documentEntry": {
            "patientId": patient_id,
            "uniqueId": oid,
            "entryUUID": "urn:uuid:%s" % eid,
            # NOTE: these need to be these hard coded values according to
            #       https://jembiprojects.jira.com/wiki/display/NPRE/Save+Registration+Encounter
            "classCode": {
                "code": "51855-5", "codingScheme": "2.16.840.1.113883.6.1",
                "codeName": "Patient Note"
            },
            "typeCode": {
                "code": "51855-5", "codingScheme": "2.16.840.1.113883.6.1",
                "codeName": "Patient Note"
            },
            "formatCode": {
                "code": "npr-pn-cda",
                "codingScheme": "4308822c-d4de-49db-9bb8-275394ee971d",
                "codeName": "NPR Patient Note CDA"
            },
            "mimeType": "text/xml",
            "hash": shasum.hexdigest(),
            "size": len(cda)
        }
    }


def build_json_body(cda, registration):
    patient_id = get_patient_id(
        registration.mom_id_type, registration.mom_id_no,
        registration.mom_passport_origin, registration.mom_msisdn)
    oid = get_oid()
    eid = get_uuid()
    return json.dumps(build_metadata(cda, patient_id, oid, eid))


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


def define_extras_subscription(_extras, subscription):
    # Set up the new extras
    _extras[u"subscription_type"] = str(subscription.message_set.id)
    _extras[u"subscription_rate"] = str(subscription.schedule.id)
    _extras[u"subscription_seq_start"] = str(subscription.next_sequence_number)
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


def create_contact(registration, client):
    contact_data = {
        u"msisdn": registration.mom_msisdn,
        u"groups": [settings.LANG_GROUP_KEYS[registration.mom_lang]]
    }
    _extras = define_extras_registration({}, registration)
    contact_data[u"extra"] = _extras
    return client.create_contact(contact_data)


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


@task(time_limit=10, ignore_result=True)
def jembi_post_json(registration_id, sender=None):
    """ Task to send registrations Json to Jembi"""

    logger.info("Compiling Jembi Json data")
    try:
        registration = Registration.objects.get(pk=registration_id)
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
        logger.error('Missing Registration object', exc_info=True)

    except SoftTimeLimitExceeded:
        logger.error(
            'Soft time limit exceeded processing Jembi send via Celery.',
            exc_info=True)


@task(time_limit=10, ignore_result=True)
def jembi_post_xml(registration_id, sender=None):
    """ Task to send clinic & chw registrations XML to Jembi"""

    logger.info("Compiling Jembi XML data")
    try:
        registration = Registration.objects.get(pk=registration_id)
        xml_body = build_jembi_xml(registration)
        json_body = build_json_body(xml_body, registration)
        data = build_multipart_data("yolo", build_multipart_parts(json_body,
                                                                  xml_body))

        api_url = "%s/registration/net.ihe/DocumentDossier" % (
            settings.JEMBI_BASE_URL)
        headers = {
            'Accept-Encoding': 'gzip',
            'Content-Type': 'multipart/form-data; boundary=yolo'
        }
        auth = (settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD)

        try:
            result = requests.post(api_url, headers=headers, data=data,
                                   auth=auth, verify=False)
            result.raise_for_status()
            vumi_fire_metric.apply_async(
                kwargs={
                    "metric": u"%s.%s.sum.doc_to_jembi_success" % (
                        settings.METRIC_ENV, registration.authority),
                    "value": 1,
                    "agg": "sum",
                    "sender": sender}
            )
        except HTTPError as e:
            # retry message sending if in 500 range (3 default retries)
            if 500 < e.response.status_code < 599:
                if jembi_post_xml.max_retries == \
                   jembi_post_xml.request.retries:
                    vumi_fire_metric.apply_async(
                        kwargs={
                            "metric": u"%s.%s.sum.doc_to_jembi_fail" % (
                                settings.METRIC_ENV, registration.authority),
                            "value": 1,
                            "agg": "sum",
                            "sender": None}
                    )
                raise jembi_post_xml.retry(exc=e)
            else:
                vumi_fire_metric.apply_async(
                    kwargs={
                        "metric": u"%s.%s.sum.doc_to_jembi_fail" % (
                            settings.METRIC_ENV, registration.authority),
                        "value": 1,
                        "agg": "sum",
                        "sender": None}
                )
                raise e
        except:
            logger.error('Problem posting XML to Jembi', exc_info=True)
        return result.text

    except ObjectDoesNotExist:
        logger.error('Missing Registration object', exc_info=True)

    except SoftTimeLimitExceeded:
        logger.error(
            'Soft time limit exceeded processing Jembi send via Celery.',
            exc_info=True)


@task(time_limit=10, ignore_result=True)
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
            registration = Registration.objects.get(pk=registration_id)

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


@task(ignore_result=True)
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
