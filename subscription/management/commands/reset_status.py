from django.core.management.base import BaseCommand
from optparse import make_option


from subscription.models import Subscription

SUBSCRIPTION_STANDARD = 1  # less than week 32 when reg
SUBSCRIPTION_LATER = 2  # 32-35 when reg
SUBSCRIPTION_ACCELERATED = 3  # over 35 weeks when reg


class Command(BaseCommand):
    help = "Set status on subscriptions matching criteria"
    option_list = BaseCommand.option_list + (
        make_option('--filter_messageset', dest='message_set_id',
                    default=None, type='int',
                    help='What message set do you want to look at'),
        make_option('--filter_status', dest='process_status',
                    default=None, type='int',
                    help='What status should the processing be at'),
        make_option('--filter_seq', dest='next_sequence_number',
                    default=None, type='int',
                    help='What sequence number should the processing be at'),
        make_option('--filter_active', dest='is_active',
                    default=None, type='str',
                    help='Should the subscription be active'),
        make_option('--filter_lang', dest='language',
                    default=None, type='str',
                    help='What language should the subscription be'),

        make_option('--set_active', dest='set_active',
                    default=None, type='str',
                    help='What should active be set to'),
        make_option('--set_completed', dest='set_completed',
                    default=None, type='str',
                    help='What should completed be set to'),
        make_option('--set_process_status', dest='set_process_status',
                    default=None, type='int',
                    help='What should process_status be set to'),

        make_option('--dry_run', action='store_true', default=False),
    )

    def handle(self, *args, **options):

        subscribers = Subscription.objects.filter(
            process_status=options["process_status"]
        )

        if options["message_set_id"] is not None:
            subscribers = subscribers.filter(
                message_set_id=options["message_set_id"]
            )

        if options["next_sequence_number"] is not None:
            subscribers = subscribers.filter(
                next_sequence_number=options["next_sequence_number"]
            )

        if options["is_active"] is not None:
            if options["is_active"] == "True":
                subscribers = subscribers.filter(
                    active=True
                )
            elif options["is_active"] == "False":
                subscribers = subscribers.filter(
                    active=False
                )

        if options["language"] is not None:
            subscribers = subscribers.filter(
                lang=options["language"]
            )

        self.stdout.write("Affected records: %s\n" % (subscribers.count()))

        if not options["dry_run"]:
            for subscriber in subscribers:
                if options["set_active"] is not None:
                    if options["set_active"] is "True":
                        subscriber.active = True
                    else:
                        subscriber.active = False
                if options["set_completed"] is not None:
                    if options["set_completed"] is "True":
                        subscriber.completed = True
                    else:
                        subscriber.completed = False
                if options["set_process_status"] is not None:
                    subscriber.process_status = options["set_process_status"]
                subscriber.save()
            self.stdout.write("Records updated\n")
