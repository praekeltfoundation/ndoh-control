from django.test import TestCase
from django.test.utils import override_settings
from django.core import management
from django.db.models.signals import post_save
from StringIO import StringIO
from snappybouncer.models import (UserAccount, Conversation, Ticket,
                                  relay_to_helpdesk)
from subscription.management.commands import snappy_ticket_cleanup


class TestSnappyTicketCleanupCommand(TestCase):

    def _replace_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(Ticket)
        assert has_listeners(), (
            "Ticket model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(relay_to_helpdesk,
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
            relay_to_helpdesk,
            sender=Ticket)

    def setUp(self):
        super(TestSnappyTicketCleanupCommand, self).setUp()
        self._replace_post_save_hooks()
        management.call_command(
            'loaddata', 'test_snappybouncer.json', verbosity=0)
        self.command = self.mk_command()

    def tearDown(self):
        self._restore_post_save_hooks()

    def mk_command(self):
        command = snappy_ticket_cleanup.Command()
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

        nonceless = Ticket.objects.filter(support_nonce=None)
        self.assertEqual(nonceless.count(), 2)

    @override_settings(VUMI_GO_API_TOKEN='token')
    def test_nonceless_tickets_deleted(self):
        command = self.mk_command()
        options = {"dry_run": None}
        command.handle(None, **options)

        self.assertEqual('\n'.join([
            'Finding tickets without support nonces...',
            'Nonceless tickets found: 2',
            'Deleted 2 tickets'
        ]), command.stdout.getvalue().strip())

        tickets = Ticket.objects.all()
        self.assertEqual(tickets.count(), 3)

        nonceless = Ticket.objects.filter(support_nonce=None)
        self.assertEqual(nonceless.count(), 0)
