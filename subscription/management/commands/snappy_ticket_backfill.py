from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
from besnappy import SnappyApiSender
from snappybouncer.models import Ticket
from snappybouncer.tasks import backfill_ticket


class Command(BaseCommand):
    help = "For every Snappy Ticket that has a support_id but "\
           "does not have an Operator, this will populate the "\
           "Operator, Tag and Faccode fields for that Ticket"
    option_list = BaseCommand.option_list + (
        make_option('--dry_run', action='store_true', default=False),
    )

    def handle(self, *args, **options):
        self.stdout.write('Looking up Snappy operators (staff)...\n')
        # Make a session to Snappy
        snappy_api = SnappyApiSender(
            api_key=settings.SNAPPY_API_KEY,
            api_url=settings.SNAPPY_BASE_URL
        )
        # Get the snappy account id
        accounts = snappy_api.get_accounts()
        staff = snappy_api.get_staff(accounts[0]["id"])
        operators = dict()
        for staff_member in staff:
            operators[staff_member["username"]] = staff_member["id"]
        self.stdout.write('Staff members compiled.\n')

        self.stdout.write('Finding tickets with support ids...\n')
        tickets_with_support_id = Ticket.objects.exclude(support_id=None)
        counter1 = tickets_with_support_id.count()
        self.stdout.write('Tickets with support ids found: %s\n' % counter1)

        self.stdout.write('Finding subset tickets without operators...\n')
        tickets = tickets_with_support_id.filter(operator=None)
        counter2 = tickets.count()
        self.stdout.write('Subset tickets found: %s\n' % counter2)

        if not options["dry_run"]:
            # tickets_with_support_id.delete()
            self.stdout.write(
                'Queueing %s tickets for backfilling\n' % counter2)
            for ticket in tickets:
                # Fire task that backfills tickets
                backfill_ticket.delay(ticket.id, operators)
            self.stdout.write('Queued %s tickets for backfilling' % counter2)
        else:
            self.stdout.write('%s tickets would be backfilled' % counter2)
