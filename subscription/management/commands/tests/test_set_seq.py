from unittest import skip

from django.test import TestCase
from django.test.utils import override_settings

from djcelery.models import PeriodicTask, IntervalSchedule

from StringIO import StringIO

from subscription.management.commands import set_seq
from subscription.models import Subscription, MessageSet, Message


class FakeClient(object):

    def __init__(self, stubs):
        self.stubs = stubs

    def get_contact(self, contact_id):
        for s in self.stubs:
            if s['uuid'] == contact_id:
                return s


class TestSetSeqCommand(TestCase):

    # fixtures = ["test.json"]

    def setUp(self):
        self.command = self.mk_command()

    def mk_command(self, contacts=None):
        fake_client = FakeClient(contacts or [])
        command = set_seq.Command()
        command.stdout = StringIO()
        command.client_class = lambda *a: fake_client
        return command

    def mk_message_set(self, set_size=10, language='english'):
        msg_set = MessageSet.objects.create(short_name='message set')
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
                         message_set, lang='english', schedule=None):
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

    @skip('no fixtures')
    def test_data_loaded(self):
        subscriptions = Subscription.objects.all()
        self.assertEqual(len(subscriptions), 3)

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_stubbed_contacts(self):
        command = self.mk_command(contacts=[
            {
                'uuid': 'contact-key',
                'extra': {
                    'due_date_day': 'foo',
                    'due_date_month': 'bar',
                }
            }
        ])
        command.handle()
        self.assertEqual('Completed', command.stdout.getvalue().strip())

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_subscription_updated(self):

        msg_set = self.mk_message_set()
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
                        u'due_date_month': u'11'},
             u'key': u'82309423098',
             u'msisdn': u'+271234'}
        ])
        command.handle()
        updated = Subscription.objects.get(pk=1)
        self.assertEqual(1, updated.next_sequence_number)
        self.assertEqual('Completed', command.stdout.getvalue().strip())
