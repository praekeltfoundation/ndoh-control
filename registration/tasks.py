import requests
import json

from datetime import datetime
from celery.task import Task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from .models import Registration


logger = get_task_logger(__name__)


class Jembi_Post_Json(Task):
    """ Task to send registrations to Jembi
    """
    name = "registrations.tasks.Jembi_Post_Json"

    class FailedEventRequest(Exception):
        """ The attempted task failed because of a non-200 HTTP return code.
        """

    def get_timestamp(self):
        return datetime.today().strftime("%Y%m%d%H%M%S")

    def get_dob(self, mom_dob):
        if type(mom_dob) == str:
            return mom_dob.strftime("%Y%m%d")
        else:
            return None

    def get_subscription_type(self, authority):
        authority_map = {
            'personal': 1,
            'chw': 2,
            'clinic': 3
        }
        return authority_map[authority]

    def build_jembi_json(self, registration):
        """ Compile json to be sent to Jembi. """

        json_template = {
            "mha": 1,
            "swt": 1,
            "dmsisdn": registration.hcw_msisdn,
            "cmsisdn": registration.mom_msisdn,
            "id": registration.mom_id_no,
            "type": self.get_subscription_type(registration.authority),
            "lang": registration.mom_lang,
            "encdate": self.get_timestamp(),
            "faccode": registration.clinic_code,
            "dob": self.get_dob(registration.mom_dob)
        }

        if registration.authority == 'clinic':
            json_template["edd"] = registration.mom_edd.strftime("%Y%m%d")

        return json_template

    def run(self, registration_id, **kwargs):
        """ Load registration, construct Jembi Json doc and send it off. """
        l = self.get_logger(**kwargs)

        l.info("Compiling Jembi Json data")
        try:
            registration = Registration.objects.get(pk=registration_id)
            json_doc = self.build_jembi_json(registration)

            result = requests.post(
                "%s/json/subscription" % settings.JEMBI_BASE_URL,  # url
                headers={'Content-Type': 'application/json'},
                data=json.dumps(json_doc),
                auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
                verify=False
            )
            return result.text

        except ObjectDoesNotExist:
            logger.error('Missing Registration object', exc_info=True)

        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceeded processing Jembi send via Celery.',
                exc_info=True)

jembi_post_json = Jembi_Post_Json()


class Jembi_Post_Xml(Task):
    """ Task to send registrations to Jembi
    """
    name = "registrations.tasks.Jembi_Post_Xml"

    class FailedEventRequest(Exception):
        """ The attempted task failed because of a non-200 HTTP return code.
        """

    def build_jembi_xml(self, registration):
        """ Compile XML to be sent to Jembi. """
        import xml.etree.ElementTree as ET

        ET.register_namespace('', "urn:hl7-org:v3")
        ET.register_namespace('voc', "urn:hl7-org:v3/voc")
        tree = ET.parse('./registration/CDA_template.xml')
        # root = tree.getroot()

        # # id uniqueId
        # root_id = root.find('{urn:hl7-org:v3}id')
        # root_id.set('root', 'uuid')

        # record_target = root.find('{urn:hl7-org:v3}recordTarget')
        # patient_role = record_target.find('{urn:hl7-org:v3}patientRole')

        # # id patient
        # patient_id = patient_role.find('{urn:hl7-org:v3}id')
        # patient_id.set('extension', 'patient_id')

        # # patient cell number
        # contact_msisdn = patient_role.find('{urn:hl7-org:v3}telecom')
        # contact_msisdn.set('value', 'contact_msisdn')

        # # birth time
        # patient = patient_role.find('{urn:hl7-org:v3}patient')
        # birth_time = patient.find('{urn:hl7-org:v3}birthTime')
        # birth_time.set('value', 'birth_time')

        # # language code
        # lang_com = patient.find('{urn:hl7-org:v3}languageCommunication')
        # lang_code = lang_com.find('{urn:hl7-org:v3}languageCode')
        # lang_code.set('code', 'lang_code')

        # # hcw cell number
        # hcw_author = root.find('{urn:hl7-org:v3}author')
        # assign_author = hcw_author.find('{urn:hl7-org:v3}assignedAuthor')
        # hcw_msisdn = assign_author.find('{urn:hl7-org:v3}telecom')
        # hcw_msisdn.set('value', 'hcw_cell_number')

        # # id clinic
        # rep_org = assign_author.find('{urn:hl7-org:v3}representedOrganization')
        # clinic_code = rep_org.find('{urn:hl7-org:v3}id')
        # clinic_code.set('extension', 'clinic_code')

        # # author time
        # for time in root.iter('{urn:hl7-org:v3}time'):
        #     time.set('value', 'author timestamp')

        # # effective time
        # for effective_time in root.iter('{urn:hl7-org:v3}effectiveTime'):
        #     effective_time.set('value', 'timestamp')

        # # application code & software name
        # for authdevice in root.iter('{urn:hl7-org:v3}assignedAuthoringDevice'):
        #     application_code = authdevice.find('{urn:hl7-org:v3}code')
        #     application_code.set('code', 'PF')
        #     software_name = authdevice.find('{urn:hl7-org:v3}softwareName')
        #     software_name.text = 'Vumi'

        # # pregnancy status code, pregnancy display name, due date
        # for entry in root.iter('{urn:hl7-org:v3}entry'):
        #     observation = entry.find('{urn:hl7-org:v3}observation')
        #     value = observation.find('{urn:hl7-org:v3}value')
        #     value.set('code', 'preg_status_code')
        #     value.set('displayName', 'preg_display_name')

        #     entry_rel = observation.find('{urn:hl7-org:v3}entryRelationship')
        #     for value in entry_rel.iter('{urn:hl7-org:v3}value'):
        #         value.set('value', 'due_date')
        tree.write('./registration/CDA_updated.xml',
                   xml_declaration=True)
        pass

    def run(self, registration_id, **kwargs):
        """ Load registration, construct Jembi XML doc and send it off. """
        l = self.get_logger(**kwargs)

        l.info("Compiling Jembi XML data")
        try:
            registration = Registration.objects.get(pk=registration_id)
            json_doc = self.build_jembi_xml(registration)

            result = requests.post(
                "%s/json/subscription" % settings.JEMBI_BASE_URL,  # url
                headers={'Content-Type': 'application/json'},
                data=json.dumps(json_doc),
                auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
                verify=False
            )
            return result.text

        except ObjectDoesNotExist:
            logger.error('Missing Registration object', exc_info=True)

        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceeded processing Jembi send via Celery.',
                exc_info=True)

jembi_post_xml = Jembi_Post_Xml()
