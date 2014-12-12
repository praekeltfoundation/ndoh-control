from django.test import TestCase
from django.test.utils import override_settings

from djcelery.models import PeriodicTask, IntervalSchedule

from StringIO import StringIO

from subscription.management.commands.reset_status import (
    SUBSCRIPTION_ACCELERATED)
from subscription.management.commands import reset_status
from subscription.models import Subscription, MessageSet, Message


class TestResetStatusCommand(TestCase):

    def setUp(self):
        self.command = self.mk_command()

    def mk_command(self):
        command = reset_status.Command()
        command.stdout = StringIO()
        return command

    def mk_message_set(self, set_size=10, short_name='standard',
                       language='en'):
        msg_set, created = MessageSet.objects.get_or_create(
            short_name=short_name)
        if created:
            for i in range(set_size):
                Message.objects.create(
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
    def test_accelerated_subscription_updated(self):

        msg_set = self.mk_message_set(short_name='accelerated')
        self.assertEqual(msg_set.pk, SUBSCRIPTION_ACCELERATED)

        sub = self.mk_subscription(
            user_account='82309423098',
            contact_key='82309423098',
            to_addr='+271234',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 16
        sub.process_status = -1
        sub.save()

        sub = self.mk_subscription(
            user_account='82309423099',
            contact_key='82309423099',
            to_addr='+271235',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 12
        sub.process_status = 0
        sub.save()

        set_process_status = 0
        set_active = False
        set_completed = True
        command = self.mk_command()
        # options needed to be named after the dest from optparse
        options = {"message_set_id": SUBSCRIPTION_ACCELERATED,
                   "process_status": -1,
                   "next_sequence_number": 16,
                   "is_active": True,
                   "language": 'en',
                   "set_process_status": set_process_status,
                   "set_active": str(set_active),
                   "set_completed": str(set_completed),
                   "dry_run": None}
        command.handle(None, **options)

        updated = Subscription.objects.get(contact_key='82309423098')
        self.assertEqual(set_process_status, updated.process_status)
        self.assertEqual(set_active, updated.active)
        self.assertEqual(set_completed, updated.completed)
        self.assertEqual('\n'.join([
            'Affected records: 2',  # one subscription from fixtures
            'Records updated'
        ]), command.stdout.getvalue().strip())

        not_updated = Subscription.objects.get(contact_key='82309423099')
        self.assertEqual(0, not_updated.process_status)
        self.assertEqual(True, not_updated.active)
        self.assertEqual(False, not_updated.completed)


    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_inactive_subscriptions_updated(self):

        msg_set = self.mk_message_set(short_name='accelerated')
        self.assertEqual(msg_set.pk, SUBSCRIPTION_ACCELERATED)

        sub = self.mk_subscription(
            user_account='82309423097',
            contact_key='82309423097',
            to_addr='+271233',
            message_set=msg_set)
        sub.active = False
        sub.completed = False
        sub.next_sequence_number = 10
        sub.process_status = -1
        sub.save()

        sub = self.mk_subscription(
            user_account='82309423098',
            contact_key='82309423098',
            to_addr='+271234',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 10
        sub.process_status = -1
        sub.save()

        sub = self.mk_subscription(
            user_account='82309423099',
            contact_key='82309423099',
            to_addr='+271235',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 12
        sub.process_status = 0
        sub.save()

        command = self.mk_command()
        # options needed to be named after the dest from optparse
        options = {"message_set_id": None,
                   "process_status": -1,
                   "next_sequence_number": None,
                   "is_active": False,
                   "language": None,
                   "set_active": None,
                   "set_completed": None,
                   "set_process_status": 0,
                   "dry_run": None}
        command.handle(None, **options)

        updated = Subscription.objects.get(contact_key='82309423097')
        self.assertEqual(0, updated.process_status)
        self.assertEqual(False, updated.active)
        self.assertEqual('\n'.join([
            'Affected records: 1',
            'Records updated'
        ]), command.stdout.getvalue().strip())

        not_updated = Subscription.objects.get(contact_key='82309423098')
        self.assertEqual(-1, not_updated.process_status)
        self.assertEqual(True, not_updated.active)
        self.assertEqual(False, not_updated.completed)

        not_updated = Subscription.objects.get(contact_key='82309423099')
        self.assertEqual(0, not_updated.process_status)
        self.assertEqual(True, not_updated.active)
        self.assertEqual(False, not_updated.completed)


    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_empty_lang_update(self):

        msg_set = self.mk_message_set(short_name='accelerated')
        self.assertEqual(msg_set.pk, SUBSCRIPTION_ACCELERATED)

        sub = self.mk_subscription(
            user_account='82309423097',
            contact_key='82309423097',
            to_addr='+271233',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 1
        sub.process_status = -1
        sub.lang = 'st'
        sub.save()

        sub = self.mk_subscription(
            user_account='82309423098',
            contact_key='82309423098',
            to_addr='+271234',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 1
        sub.process_status = -1
        sub.save()

        sub = self.mk_subscription(
            user_account='82309423099',
            contact_key='82309423099',
            to_addr='+271235',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 12
        sub.process_status = 0
        sub.save()

        command = self.mk_command()
        # options needed to be named after the dest from optparse
        options = {"message_set_id": SUBSCRIPTION_ACCELERATED,
                   "process_status": -1,
                   "next_sequence_number": 1,
                   "is_active": True,
                   "language": 'st',
                   "set_active": False,
                   "set_completed": False,
                   "set_process_status": -2,
                   "dry_run": None}
        command.handle(None, **options)

        updated = Subscription.objects.get(contact_key='82309423097')
        self.assertEqual(-2, updated.process_status)
        self.assertEqual(False, updated.active)
        self.assertEqual('\n'.join([
            'Affected records: 1',
            'Records updated'
        ]), command.stdout.getvalue().strip())

        not_updated = Subscription.objects.get(contact_key='82309423098')
        self.assertEqual(-1, not_updated.process_status)
        self.assertEqual(True, not_updated.active)
        self.assertEqual(False, not_updated.completed)

        not_updated = Subscription.objects.get(contact_key='82309423099')
        self.assertEqual(0, not_updated.process_status)
        self.assertEqual(True, not_updated.active)
        self.assertEqual(False, not_updated.completed)

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_dry_run(self):

        msg_set = self.mk_message_set(short_name='accelerated')
        self.assertEqual(msg_set.pk, SUBSCRIPTION_ACCELERATED)

        sub = self.mk_subscription(
            user_account='82309423097',
            contact_key='82309423097',
            to_addr='+271233',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 1
        sub.process_status = -1
        sub.lang = 'st'
        sub.save()

        sub = self.mk_subscription(
            user_account='82309423098',
            contact_key='82309423098',
            to_addr='+271234',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 1
        sub.process_status = -1
        sub.save()

        sub = self.mk_subscription(
            user_account='82309423099',
            contact_key='82309423099',
            to_addr='+271235',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 12
        sub.process_status = 0
        sub.save()

        command = self.mk_command()
        # options needed to be named after the dest from optparse
        options = {"message_set_id": SUBSCRIPTION_ACCELERATED,
                   "process_status": -1,
                   "next_sequence_number": 1,
                   "is_active": True,
                   "language": 'st',
                   "set_active": False,
                   "set_completed": False,
                   "set_process_status": -2,
                   "dry_run": True}
        command.handle(None, **options)

        self.assertEqual('Affected records: 1',
                         command.stdout.getvalue().strip())

        not_updated = Subscription.objects.get(contact_key='82309423097')
        self.assertEqual(-1, not_updated.process_status)
        self.assertEqual(True, not_updated.active)
        self.assertEqual(False, not_updated.completed)

        not_updated = Subscription.objects.get(contact_key='82309423098')
        self.assertEqual(-1, not_updated.process_status)
        self.assertEqual(True, not_updated.active)
        self.assertEqual(False, not_updated.completed)

        not_updated = Subscription.objects.get(contact_key='82309423099')
        self.assertEqual(0, not_updated.process_status)
        self.assertEqual(True, not_updated.active)
        self.assertEqual(False, not_updated.completed)
