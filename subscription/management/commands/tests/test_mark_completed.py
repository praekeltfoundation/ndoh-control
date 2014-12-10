from django.test import TestCase
from django.test.utils import override_settings

from djcelery.models import PeriodicTask, IntervalSchedule

from StringIO import StringIO

from subscription.management.commands.mark_completed import (
    SUBSCRIPTION_ACCELERATED, SUBSCRIPTION_BABY1, SUBSCRIPTION_BABY2)
from subscription.management.commands import mark_completed
from subscription.models import Subscription, MessageSet, Message


class TestResetStatusCommand(TestCase):

    def setUp(self):
        self.command = self.mk_command()

    def mk_command(self):
        command = mark_completed.Command()
        command.stdout = StringIO()
        return command

    def mk_message_set(self, next_set, set_size=10, short_name='standard',
                       language='en'):
        msg_set, created = MessageSet.objects.get_or_create(
            short_name=short_name, next_set=next_set)
        for i in range(set_size):
            Message.objects.get_or_create(
                message_set=msg_set,
                sequence_number=i,
                lang=language,
                content='message %s' % (i,)
            )
        return msg_set

    def mk_default_schedule(self):
        interval, _ = IntervalSchedule.objects.get_or_create(
            every=2, period='days')
        scheduled, _ = PeriodicTask.objects.get_or_create(
            name='default', interval=interval)
        return scheduled

    def mk_subscription(self, user_account, contact_key, to_addr,
                        message_set, lang='en', schedule=None):
        schedule = schedule or self.mk_default_schedule()
        return Subscription.objects.create(
            user_account=user_account,
            contact_key=contact_key,
            to_addr=to_addr,
            message_set=message_set,
            lang=lang,
            schedule=schedule)

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_accelerated_subscription_completed(self):

        msg_set_baby2 = self.mk_message_set(next_set=None, short_name='baby2')
        self.assertEqual(msg_set_baby2.pk, SUBSCRIPTION_BABY2)
        msg_set_baby1 = self.mk_message_set(next_set=msg_set_baby2, short_name='baby1')
        self.assertEqual(msg_set_baby1.pk, SUBSCRIPTION_BABY1)
        msg_set_accel = self.mk_message_set(next_set=msg_set_baby1, short_name='accelerated')
        self.assertEqual(msg_set_accel.pk, SUBSCRIPTION_ACCELERATED)

        sub = self.mk_subscription(
            user_account='82309423100',
            contact_key='82309423100',
            to_addr='+271234',
            message_set=msg_set_accel)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 16
        sub.process_status = -1
        sub.save()

        sub = self.mk_subscription(
            user_account='82309423101',
            contact_key='82309423101',
            to_addr='+271235',
            message_set=msg_set_accel)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 12
        sub.process_status = 0
        sub.save()

        command = self.mk_command()
        # options needed to be named after the dest from optparse
        options = {"message_set_id": SUBSCRIPTION_ACCELERATED,
                   "process_status": -1,
                   "next_sequence_number": 16}
        command.handle(None, **options)

        subs = Subscription.objects.all()
        print subs
        updated = Subscription.objects.get(contact_key='82309423100',
            message_set_id=SUBSCRIPTION_BABY1)
        self.assertEqual(2, updated.process_status)
        self.assertEqual(False, updated.active)
        self.assertEqual(True, updated.completed)
        self.assertEqual('\n'.join([
            'Affected records: 1',
            'Records updated'
        ]), command.stdout.getvalue().strip())

        not_updated = Subscription.objects.get(contact_key='82309423101')
        self.assertEqual(0, not_updated.process_status)
        self.assertEqual(True, not_updated.active)
        self.assertEqual(False, not_updated.completed)
