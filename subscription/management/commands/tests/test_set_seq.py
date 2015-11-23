from datetime import date, datetime

from django.test import TestCase
from django.test.utils import override_settings

from djcelery.models import PeriodicTask, IntervalSchedule

from StringIO import StringIO

from subscription.management.commands import set_seq
from subscription.management.commands.set_seq import (
    SUBSCRIPTION_STANDARD, SUBSCRIPTION_LATER)
from subscription.models import Subscription, MessageSet, Message


class FakeClient(object):

    def __init__(self, stubs):
        self.stubs = stubs

    def get_contact(self, contact_id):
        for s in self.stubs:
            if s['key'] == contact_id:
                return s


class TestSetSeqCommand(TestCase):

    fixtures = ["test_initialdata.json"]

    def setUp(self):
        self.command = self.mk_command()

    def mk_command(self, contacts=None):
        fake_client = FakeClient(contacts or [])
        command = set_seq.Command()
        command.stdout = StringIO()
        command.client_class = lambda *a: fake_client
        # set the date so tests continue to work in the future
        command.get_now = lambda *a: datetime(2014, 11, 5)
        return command

    def mk_message_set(self, set_size=10, short_name='standard',
                       language='eng'):
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
                        message_set, lang='eng', schedule=None):
        schedule = schedule or self.mk_default_schedule()
        return Subscription.objects.create(
            user_account=user_account,
            contact_key=contact_key,
            to_addr=to_addr,
            message_set=message_set,
            lang=lang,
            schedule=schedule)

    def test_calc_sequence_start(self):
        self.assertEqual(self.command.calc_sequence_start(3, 1), 1)
        self.assertEqual(self.command.calc_sequence_start(5, 1), 1)
        self.assertEqual(self.command.calc_sequence_start(31, 1), 53)
        self.assertEqual(self.command.calc_sequence_start(31, 2), 1)
        self.assertEqual(self.command.calc_sequence_start(32, 2), 4)
        self.assertEqual(self.command.calc_sequence_start(35, 2), 13)

    def test_calc_sequence_start_with_ff_to_end_type_1(self):
        self.assertEqual(self.command.calc_sequence_start(44, 2), 28)
        self.assertEqual(self.command.stdout.getvalue().strip(),
                         'Fast forwarding to end')

    def test_calc_sequence_start_with_ff_to_end_type_2(self):
        self.assertEqual(self.command.calc_sequence_start(44, 1), 73)
        self.assertEqual(self.command.stdout.getvalue().strip(),
                         'Fast forwarding to end')

    def test_year_from_month(self):
        self.assertEqual(
            set([2015]),
            set([self.command.year_from_month(month)
                 for month in range(9)]))
        self.assertEqual(
            set([2014]),
            set([self.command.year_from_month(month)
                 for month in range(9, 12)]))

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_stubbed_contacts(self):
        command = self.mk_command(contacts=[
            {
                'key': 'contact-key',
                'extra': {
                    'due_date_day': 'foo',
                    'due_date_month': 'bar',
                }
            }
        ])
        command.handle()
        self.assertEqual('Completed', command.stdout.getvalue().strip())

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_standard_subscription_updated(self):

        msg_set = self.mk_message_set(short_name='standard')
        self.assertEqual(msg_set.pk, SUBSCRIPTION_STANDARD)

        sub = self.mk_subscription(
            user_account='82309423098',
            contact_key='82309423098',
            to_addr='+271234',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.save()

        command = self.mk_command(contacts=[
            {u'$VERSION': 2,
             u'created_at': u'2014-10-13 07:39:05.503410',
             u'extra': {u'due_date_day': u'21',
                        u'due_date_month': u'11',
                        u'subscription_type': SUBSCRIPTION_STANDARD},
             u'key': u'82309423098',
             u'msisdn': u'+271234'}
        ])
        command.handle()

        weeks = command.calc_weeks(date(2014, 11, 21))
        # two weeks to due date based on `get_now()`
        self.assertEqual(weeks, 38)
        sequence_number = command.calc_sequence_start(
            weeks, SUBSCRIPTION_STANDARD)
        # start at week 4
        # 38 - 4 -> 34
        # At two per week -> 68
        # Fix because sequence starts at 1 and we have two per week -> 67
        self.assertEqual(sequence_number, 67)

        updated = Subscription.objects.get(contact_key='82309423098')
        self.assertEqual(sequence_number, updated.next_sequence_number)
        self.assertEqual('\n'.join([
            'Getting: 82309423098',
            'Mother due 2014-11-21',
            'Week of preg 38',
            'Sub type is 1',
            'Setting to seq 67 from 1',
            'Updated 1.0 subscribers at unknown per second',
            'Completed'
        ]), command.stdout.getvalue().strip())

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_later_subscription_updated(self):

        msg_set = self.mk_message_set(short_name='later')
        self.assertEqual(msg_set.pk, SUBSCRIPTION_LATER)

        sub = self.mk_subscription(
            user_account='82309423098',
            contact_key='82309423098',
            to_addr='+271234',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.save()

        command = self.mk_command(contacts=[
            {u'$VERSION': 2,
             u'created_at': u'2014-10-13 07:39:05.503410',
             u'extra': {u'due_date_day': u'21',
                        u'due_date_month': u'11',
                        u'subscription_type': SUBSCRIPTION_LATER},
             u'key': u'82309423098',
             u'msisdn': u'+271234'}
        ])
        command.handle()

        weeks = command.calc_weeks(date(2014, 11, 21))
        # two weeks to due date based on `get_now()`
        self.assertEqual(weeks, 38)
        sequence_number = command.calc_sequence_start(
            weeks, SUBSCRIPTION_LATER)
        # start at week 30
        # 38 - 30 -> 8
        # At three per week -> 24
        # Fix because sequence starts at 1 and we have 3 per week -> 22
        self.assertEqual(sequence_number, 22)

        updated = Subscription.objects.get(contact_key='82309423098')
        self.assertEqual(sequence_number, updated.next_sequence_number)
        self.assertEqual('\n'.join([
            'Getting: 82309423098',
            'Mother due 2014-11-21',
            'Week of preg 38',
            'Sub type is 2',
            'Setting to seq 22 from 1',
            'Updated 1.0 subscribers at unknown per second',
            'Completed'
        ]), command.stdout.getvalue().strip())

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_leap_year_due_date(self):

        msg_set = self.mk_message_set(short_name='standard')
        self.assertEqual(msg_set.pk, SUBSCRIPTION_STANDARD)

        sub = self.mk_subscription(
            user_account='82309423098',
            contact_key='82309423098',
            to_addr='+271234',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.save()

        command = self.mk_command(contacts=[
            {u'$VERSION': 2,
             u'created_at': u'2014-10-13 07:39:05.503410',
             u'extra': {u'due_date_day': u'29',
                        u'due_date_month': u'02',
                        u'subscription_type': SUBSCRIPTION_STANDARD},
             u'key': u'82309423098',
             u'msisdn': u'+271234'}
        ])
        command.handle()

        self.assertEqual('\n'.join([
            'Getting: 82309423098',
            'Contact 82309423098 threw day is out of range for month',
            'Completed'
        ]), command.stdout.getvalue().strip())

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_contact_missing_fields(self):

        msg_set = self.mk_message_set(short_name='standard')
        self.assertEqual(msg_set.pk, SUBSCRIPTION_STANDARD)

        sub = self.mk_subscription(
            user_account='82309423098',
            contact_key='82309423098',
            to_addr='+271234',
            message_set=msg_set)
        sub.active = True
        sub.completed = False
        sub.save()

        command = self.mk_command(contacts=[
            {u'$VERSION': 2,
             u'bbm_pin': None,
             u'created_at': u'2014-09-11 12:42:00.470711',
             u'dob': None,
             u'email_address': None,
             u'extra': {u'birth_day': u'30',
                        u'birth_month': u'12',
                        u'birth_year': u'1996',
                        u'clinic_code': u'123456',
                        u'dob': u'1996-12-30',
                        u'due_date_day': u'23',
                        u'due_date_month': u'01',
                        u'id_type': u'sa_id',
                        u'is_registered': u'true',
                        u'is_registered_by': u'clinic',
                        u'language_choice': u'zu',
                        u'last_stage': u'states_faq_end',
                        u'metric_sessions_to_register': u'0',
                        u'metric_sum_sessions': u'55',
                        u'sa_id': u'xxxx',
                        u'service_rating_reminder': u'0',
                        u'ussd_sessions': u'54'},
             u'facebook_id': None,
             u'groups': [u'4baf3a89aa0243feb328ca664d1a5e8c'],
             u'gtalk_id': None,
             u'key': u'82309423098',
             u'msisdn': u'+27715323385',
             u'mxit_id': None,
             u'name': None,
             u'subscription': {},
             u'surname': None,
             u'twitter_handle': None,
             u'user_account': u'useraccountkey',
             u'wechat_id': None}
        ])
        command.handle()

        self.assertEqual('\n'.join([
            "Getting: 82309423098",
            "Mother due 2015-01-23",
            "Week of preg 29",
            "Contact 82309423098 threw KeyError on 'subscription_type'",
            "Completed"
        ]), command.stdout.getvalue().strip())
