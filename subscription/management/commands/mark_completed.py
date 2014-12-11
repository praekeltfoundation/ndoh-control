from django.core.management.base import BaseCommand
from optparse import make_option
from django.db.models import Q
from djcelery.models import PeriodicTask
from django.db.models import Max
from datetime import datetime
from math import floor

from subscription.models import Subscription, MessageSet, Message

SUBSCRIPTION_STANDARD = 1  # less than week 32 when reg
SUBSCRIPTION_LATER = 2  # 32-35 when reg
SUBSCRIPTION_ACCELERATED = 3  # over 35 weeks when reg
SUBSCRIPTION_BABY1 = 4
SUBSCRIPTION_BABY2 = 5
SUBSCRIPTION_MISCARRIAGE = 6
SUBSCRIPTION_STILLBIRTH = 7
SUBSCRIPTION_BABYLOSS = 8
SUBSCRIPTION_SUBSCRIPTION = 9 # personal aka public line reg
SUBSCRIPTION_CHW = 10 # chw line reg


class Command(BaseCommand):
    help = "Set status on subscriptions matching criteria and creates new \
            sub if follow-on messageset exists"
    option_list = BaseCommand.option_list + (
        make_option('--filter_messageset', dest='message_set_id', default=None, type='int',
                        help='What message set do you want to look at'),
        make_option('--filter_status', dest='process_status', default=None, type='int',
                        help='What status should the processing be at'),
        make_option('--filter_seq', dest='next_sequence_number', default=None, type='int',
                        help='What status should the processing be at'),
    )

    def get_now(self):
        return datetime.now()

    def calc_days(self, updated_at, today=None):
        if today is None:
            today = self.get_now().date()
        # calc diff betwen now and updated_at
        days = (today - updated_at).days
        return days

    def calc_baby1_start(self, days):
        schedule_interval = 7 / 2.0  # twice a week for baby1
        seq_start = int(floor(days/schedule_interval)) + 1
        return seq_start

    def handle(self, *args, **options):

        subscribers = Subscription.objects.filter(
            Q(message_set_id=options["message_set_id"]),
            Q(process_status=options["process_status"]),
            Q(next_sequence_number=options["next_sequence_number"]))
        self.stdout.write("Affected records: " + str(len(subscribers)) + "\n")
        set_max = Message.objects.filter(
            Q(message_set_id=options["message_set_id"])
                ).aggregate(Max('sequence_number'))["sequence_number__max"]
        message_set = MessageSet.objects.get(
            Q(id=options["message_set_id"]))


        for subscriber in subscribers:
            # make current subscription completed
            subscriber.next_sequence_number = set_max
            subscriber.active = False
            subscriber.completed = True
            subscriber.process_status = 2
            last_update = subscriber.updated_at.date()

            subscriber.save()

            # if there is a next set, make a new subscription
            if message_set.next_set:
                # clone existing minus PK as recommended in
                # https://docs.djangoproject.com/en/1.6/topics/db/queries/#copying-model-instances
                subscriber.pk = None
                new_subscription = subscriber
                new_subscription.process_status = 0 # Ready
                new_subscription.active = True
                new_subscription.completed = False
                new_subscription.message_set = message_set.next_set
                if message_set.next_set.short_name == 'baby2':
                    new_subscription.schedule = PeriodicTask.objects.get(pk=2)
                    # PeriodicTask(pk=2) is once a week
                else:
                    new_subscription.schedule = PeriodicTask.objects.get(pk=3)
                    # PeriodicTask(pk=3) is twice a week

                if (message_set.short_name == 'accelerated' or
                        message_set.short_name == 'later'):
                    days_missed = self.calc_days(last_update)
                    new_subscription.next_sequence_number = self.calc_baby1_start(days_missed)
                else:
                    new_subscription.next_sequence_number = 1

                new_subscription.save()

        self.stdout.write("Records updated\n")
