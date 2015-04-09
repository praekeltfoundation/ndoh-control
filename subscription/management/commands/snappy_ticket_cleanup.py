from django.core.management.base import BaseCommand
from optparse import make_option
from snappybouncer.models import Ticket


class Command(BaseCommand):
    help = "Remove all Snappy tickets from backend that lacks a nonce"
    option_list = BaseCommand.option_list + (
        make_option('--dry_run', action='store_true', default=False),
    )

    def handle(self, *args, **options):
        tickets = Ticket.objects.filter(support_nonce=None)
        counter = 0

        self.stdout.write('Deleting tickets without support nonces...\n')
        self.stdout.write('Nonceless tickets found: %s\n' % tickets.count())

        for ticket in tickets:
            if not options["dry_run"]:
                ticket.delete()
                counter += 1

        self.stdout.write('Deleted %s tickets' % counter)
