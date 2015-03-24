from django.core.management.base import BaseCommand
from optparse import make_option
from django.conf import settings
from datetime import datetime

from requests import HTTPError
from go_http.contacts import ContactsApiClient

from subscription.models import Subscription

SUBSCRIPTION_STANDARD = 1  # less than week 32 when reg
SUBSCRIPTION_LATER = 2  # 32-35 when reg
SUBSCRIPTION_ACCELERATED = 3  # over 35 weeks when reg
SUBSCRIPTION_BABY1 = 4
SUBSCRIPTION_BABY2 = 5
SUBSCRIPTION_MISCARRIAGE = 6
SUBSCRIPTION_STILLBIRTH = 7
SUBSCRIPTION_BABYLOSS = 8
SUBSCRIPTION_SUBSCRIPTION = 9  # personal aka public line reg
SUBSCRIPTION_CHW = 10  # chw line reg


class Command(BaseCommand):
    help = "Puts a contact in a group in vumi"
    client_class = ContactsApiClient
    option_list = BaseCommand.option_list + (
        make_option('--filter_messageset',
                    dest='message_set_id', default=None, type='int',
                    help='What message set do you want to look at'),
        make_option('--filter_status',
                    dest='process_status', default=None, type='int',
                    help='What status should the processing be at'),
        make_option('--filter_seq', dest='next_sequence_number',
                    default=None, type='int',
                    help='What status should the processing be at'),

        make_option('--set_group', dest='set_group', default=None, type='str',
                    help='What group should they be added to'),

        make_option('--dry_run', action='store_true', default=False),
    )

    def get_now(self):
        return datetime.now()

    def handle(self, *args, **options):

        subscribers = Subscription.objects.filter(
            message_set_id=options["message_set_id"],
            process_status=options["process_status"],
            next_sequence_number=options["next_sequence_number"])
        self.stdout.write("Affected records: %s\n" % (subscribers.count()))

        if not options["dry_run"]:
            contacts = self.client_class(settings.VUMI_GO_API_TOKEN)
            counter = 0.0
            started = self.get_now()

            for subscriber in subscribers:
                self.stdout.write("Updating: %s\n" % (subscriber.contact_key,))
                try:
                    contact = contacts.get_contact(subscriber.contact_key)
                    contact.pop("key", None)
                    contact.pop("$VERSION", None)
                    contact.pop("created_at", None)
                    contact["groups"].append(options["set_group"])
                    updatedcontact = contacts.update_contact(
                        subscriber.contact_key, contact)
                    self.stdout.write(
                        "Groups now: %s\n" % (str(updatedcontact["groups"])))
                    # Tracker updates
                    counter += 1.0
                    delta = self.get_now() - started
                    # Make sure we're not dividing by zero
                    if delta.seconds > 0:
                        per_second = (
                            counter / float(
                                (self.get_now() - started).seconds))
                    else:
                        per_second = 'unknown'
                    self.stdout.write(
                        "Updated %s subscribers at %s per second\n" % (
                            counter, per_second))

                except ValueError as err:
                    self.stdout.write(
                        "Contact %s threw %s\n" % (
                            subscriber.contact_key, err))

                except KeyError as err:
                    self.stdout.write(
                        "Contact %s threw KeyError on %s\n" % (
                            subscriber.contact_key, err))

                except HTTPError as err:
                    self.stdout.write(
                        "Contact %s threw %s\n" % (subscriber.contact_key,
                                                   err.response.status_code))

            self.stdout.write("Contacts updated\n")
