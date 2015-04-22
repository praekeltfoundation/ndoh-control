from django.test import TestCase

from djcelery.models import PeriodicTask, IntervalSchedule

from StringIO import StringIO

from subscription.management.commands import normalise_msisdn
from subscription.models import Subscription, MessageSet, Message


class TestNormaliseMsisdnCommand(TestCase):

    def setUp(self):
        self.command = self.mk_command()

    def mk_command(self):
        command = normalise_msisdn.Command()
        command.stdout = StringIO()
        return command

    def mk_default_schedule(self):
        interval, _ = IntervalSchedule.objects.get_or_create(
            every=2, period='days')
        scheduled, _ = PeriodicTask.objects.get_or_create(
            name='default', interval=interval)
        return scheduled

    def mk_message_set(self, next_set, set_size=10, short_name='standard',
                       language='en', default_schedule=None):
        default_schedule = default_schedule or self.mk_default_schedule()
        msg_set, created = MessageSet.objects.get_or_create(
            short_name=short_name, next_set=next_set,
            default_schedule=default_schedule)
        for i in range(set_size):
            Message.objects.get_or_create(
                message_set=msg_set,
                sequence_number=i,
                lang=language,
                content='message %s' % (i,)
            )
        return msg_set

    def mk_subscription(self, user_account, contact_key, to_addr,
                        message_set, lang='en', schedule=None,
                        updated_at=None):
        schedule = schedule or self.mk_default_schedule()
        return Subscription.objects.create(
            user_account=user_account,
            contact_key=contact_key,
            to_addr=to_addr,
            message_set=message_set,
            lang=lang,
            schedule=schedule,
            updated_at=updated_at)

    def test_normalise_msisdn(self):

        msg_set_accel = self.mk_message_set(next_set=None,
                                            short_name='accelerated')

        sub = self.mk_subscription(
            user_account='82309423101',
            contact_key='82309423101',
            to_addr='271235',
            message_set=msg_set_accel)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 1
        sub.process_status = 0
        sub.save()

        sub2 = self.mk_subscription(
            user_account='82309423101',
            contact_key='82309423102',
            to_addr='271236',
            message_set=msg_set_accel)
        sub2.active = True
        sub2.completed = False
        sub2.next_sequence_number = 1
        sub2.process_status = 0
        sub2.save()

        sub3 = self.mk_subscription(
            user_account='82309423101',
            contact_key='82309423103',
            to_addr='+271236',
            message_set=msg_set_accel)
        sub3.active = True
        sub3.completed = False
        sub3.next_sequence_number = 1
        sub3.process_status = 0
        sub3.save()

        command = self.mk_command()
        # options needed to be named after the dest from optparse
        options = {"dry_run": None}
        command.handle(None, **options)

        updated = Subscription.objects.get(
            contact_key='82309423101')
        self.assertEqual("+271235", updated.to_addr)
        updated2 = Subscription.objects.get(
            contact_key='82309423102')
        self.assertEqual("+271236", updated2.to_addr)
        notupdated = Subscription.objects.get(
            contact_key='82309423103')
        self.assertEqual("+271236", notupdated.to_addr)
        self.assertEqual('\n'.join([
            'Affected records: 2',
            'Records updated'
        ]), command.stdout.getvalue().strip())

    def test_normalise_msisdn_dry_run(self):

        msg_set_accel = self.mk_message_set(next_set=None,
                                            short_name='accelerated')

        sub = self.mk_subscription(
            user_account='82309423101',
            contact_key='82309423101',
            to_addr='271235',
            message_set=msg_set_accel)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 1
        sub.process_status = 0
        sub.save()

        sub2 = self.mk_subscription(
            user_account='82309423101',
            contact_key='82309423102',
            to_addr='271236',
            message_set=msg_set_accel)
        sub2.active = True
        sub2.completed = False
        sub2.next_sequence_number = 1
        sub2.process_status = 0
        sub2.save()

        sub3 = self.mk_subscription(
            user_account='82309423101',
            contact_key='82309423103',
            to_addr='+271236',
            message_set=msg_set_accel)
        sub3.active = True
        sub3.completed = False
        sub3.next_sequence_number = 1
        sub3.process_status = 0
        sub3.save()

        command = self.mk_command()
        # options needed to be named after the dest from optparse
        options = {"dry_run": True}
        command.handle(None, **options)

        notupdated = Subscription.objects.get(
            contact_key='82309423101')
        self.assertEqual("271235", notupdated.to_addr)
        notupdated2 = Subscription.objects.get(
            contact_key='82309423102')
        self.assertEqual("271236", notupdated2.to_addr)
        notupdated3 = Subscription.objects.get(
            contact_key='82309423103')
        self.assertEqual("+271236", notupdated3.to_addr)
        self.assertEqual('\n'.join([
            'Affected records: 2'
        ]), command.stdout.getvalue().strip())
