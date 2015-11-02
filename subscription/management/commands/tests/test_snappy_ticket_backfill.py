from django.test import TestCase
from django.test.utils import override_settings
from django.core import management
from django.db.models.signals import post_save
from StringIO import StringIO
from snappybouncer.models import (UserAccount, Conversation, Ticket,
                                  fire_snappy_if_new)
from subscription.management.commands import snappy_ticket_backfill


class TestSnappyTicketBackfillCommand(TestCase):

    def _replace_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(Ticket)
        assert has_listeners(), (
            "Ticket model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(fire_snappy_if_new,
                             sender=Ticket)
        assert not has_listeners(), (
            "Ticket model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(Ticket)
        assert not has_listeners(), (
            "Ticket model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests.")
        post_save.connect(
            fire_snappy_if_new,
            sender=Ticket)

    def setUp(self):
        super(TestSnappyTicketBackfillCommand, self).setUp()
        self._replace_post_save_hooks()
        management.call_command(
            'loaddata', 'test_snappybouncer.json', verbosity=0)
        self.command = self.mk_command()

    def tearDown(self):
        self._restore_post_save_hooks()

    def mk_command(self):
        command = snappy_ticket_backfill.Command()
        command.stdout = StringIO()
        return command

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_data_loaded(self):
        useraccounts = UserAccount.objects.all()
        self.assertEqual(useraccounts.count(), 1)

        conversations = Conversation.objects.all()
        self.assertEqual(conversations.count(), 1)

        tickets = Ticket.objects.all()
        self.assertEqual(tickets.count(), 5)

        tickets_with_support_id = Ticket.objects.exclude(support_id=None)
        self.assertEqual(tickets_with_support_id.count(), 3)

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_support_id_less_tickets_deleted(self):
        command = self.mk_command()
        options = {"dry_run": None}
        command.handle(None, **options)

        self.assertEqual('\n'.join([
            'Finding tickets with support ids...',
            'Tickets with support ids found: 3'
        ]), command.stdout.getvalue().strip())

        tickets = Ticket.objects.all()
        self.assertEqual(tickets.count(), 5)
