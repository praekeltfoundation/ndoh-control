from django.test import TestCase
from StringIO import StringIO

from subscription.management.commands import set_seq


class FakeClient(object):

    def __init__(self, stubs):
        self.stubs = stubs

    def get_contact(self, contact_id):
        for s in self.stubs:
            if s['uuid'] == contact_id:
                return s


class TestSetSeqCommand(TestCase):

    def setUp(self):
        self.command = self.mk_command()

    def mk_command(self, contacts=None):
        fake_client = FakeClient(contacts or [])
        command = set_seq.Command()
        command.stdout = StringIO()
        command.client_class = lambda *a: fake_client
        return command

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
