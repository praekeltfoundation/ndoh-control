from datetime import date, datetime

from django.test import TestCase
from django.test.utils import override_settings

from djcelery.models import PeriodicTask, IntervalSchedule

from StringIO import StringIO

from subscription.management.commands import add_to_group
from subscription.management.commands.mark_completed import (
    SUBSCRIPTION_ACCELERATED, SUBSCRIPTION_BABY1, SUBSCRIPTION_BABY2)
from subscription.models import Subscription, MessageSet, Message


class FakeClient(object):

    def __init__(self, stubs):
        self.stubs = stubs

    def get_contact(self, contact_id):
        for s in self.stubs:
            if s['key'] == contact_id:
                return s

    def update_contact(self, contact_id, contact_data):
        contact_data["key"] = contact_id
        contact_data["VERSION"] = 2
        return contact_data
        # i = 0
        # print self.stubs
        # for s in self.stubs:
        #     print "key" in s
        #     print s
        #     if s['key'] == contact_id:
        #         contact_data["key"] = contact_id
        #         contact_data["VERSION"] = 2
        #         self.stubs[i] = contact_data
        #         return contact_data
        #     i += 1


class TestAddToGroupCommand(TestCase):

    def setUp(self):
        self.command = self.mk_command()

    def mk_command(self, contacts=None):
        fake_client = FakeClient(contacts or [])
        command = add_to_group.Command()
        command.stdout = StringIO()
        command.client_class = lambda *a: fake_client
        # set the date so tests continue to work in the future
        command.get_now = lambda *a: datetime(2014, 11, 5)
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
                        message_set, lang='eng', schedule=None):
        schedule = schedule or self.mk_default_schedule()
        return Subscription.objects.create(
            user_account=user_account,
            contact_key=contact_key,
            to_addr=to_addr,
            message_set=message_set,
            lang=lang,
            schedule=schedule)


    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_contact_updated(self):

        msg_set_baby2 = self.mk_message_set(next_set=None, short_name='baby2')
        self.assertEqual(msg_set_baby2.pk, SUBSCRIPTION_BABY2)
        msg_set_baby1 = self.mk_message_set(next_set=msg_set_baby2, short_name='baby1')
        self.assertEqual(msg_set_baby1.pk, SUBSCRIPTION_BABY1)
        msg_set_accel = self.mk_message_set(next_set=msg_set_baby1, short_name='accelerated')
        self.assertEqual(msg_set_accel.pk, SUBSCRIPTION_ACCELERATED)

        # not broken user
        sub = self.mk_subscription(
            user_account='82309423101',
            contact_key='82309423101',
            to_addr='+271235',
            message_set=msg_set_accel)
        sub.active = True
        sub.completed = False
        sub.next_sequence_number = 10
        sub.process_status = 0
        sub.save()

        options = {"message_set_id": SUBSCRIPTION_ACCELERATED,
                   "process_status": -1,
                   "next_sequence_number": 16,
                   "set_group": "group-key",
                   "dry_run": None}

        command = self.mk_command(contacts=[
            {u'$VERSION': 2,
             u'created_at': u'2014-10-13 07:39:05.503410',
             u'extra': {u'due_date_day': u'21',
                        u'due_date_month': u'11',
                        u'subscription_type': SUBSCRIPTION_ACCELERATED},
             u'key': u'82309423100',
             u'groups': [],
             u'msisdn': u'+271234'}
        ])
        command.handle(None, **options)

        self.assertEqual('\n'.join([
            'Affected records: 1',
            'Updating: 82309423100',
            'Groups now: [\'group-key\']',
            'Updated 1.0 subscribers at unknown per second',
            'Contacts updated'
        ]), command.stdout.getvalue().strip())


