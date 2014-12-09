from django.core.management.base import BaseCommand
from optparse import make_option
from django.db.models import Q


from subscription.models import Subscription

SUBSCRIPTION_STANDARD = 1  # less than week 32 when reg
SUBSCRIPTION_LATER = 2  # 32-35 when reg
SUBSCRIPTION_ACCELERATED = 3  # over 35 weeks when reg


class Command(BaseCommand):
    help = "Set status on subscriptions matching criteria"
    option_list = BaseCommand.option_list + (
        make_option('--filter_messageset', dest='message_set_id', type='int', default=None,
                        help='What message set do you want to look at'),
        make_option('--filter_status', dest='process_status', default=None, type='int',
                        help='What status should the processing be at'),
        make_option('--filter_seq', dest='next_sequence_number', default=None, type='int',
                        help='What status should the processing be at'),
        make_option('--set_active', dest='active', default=None, type='str',
                        help='What should active be set to'),
        make_option('--set_completed', dest='completed', default=None, type='str',
                        help='What should completed be set to'),
        make_option('--set_process_status', dest='new_process_status', default=None, type='int',
                        help='What should process_status be set to'),
    )

    def handle(self, *args, **options):
       
        subscribers = Subscription.objects.filter(
            Q(message_set_id=options["message_set_id"]), Q(process_status=options["process_status"]),
            Q(next_sequence_number=options["next_sequence_number"]))
        self.stdout.write("Affected records: " + str(len(subscribers)) + "\n")

        for subscriber in subscribers:
            if options["active"] is not None:
                if options["active"] is "True":
                    subscriber.active = True
                else:
                    subscriber.active = False
            if options["completed"] is not None:
                if options["completed"] is "True":
                    subscriber.completed = True
                else:
                    subscriber.completed = False
            if options["new_process_status"] is not None:
                subscriber.process_status = options["new_process_status"]
            subscriber.save()
        self.stdout.write("Records updated\n")
