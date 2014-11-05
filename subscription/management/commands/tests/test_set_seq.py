from django.test import TestCase
from StringIO import StringIO

from subscription.management.commands import set_seq


class TestSetSeqCommand(TestCase):

    def setUp(self):
        self.command = set_seq.Command()
        self.command.stdout = StringIO()

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
