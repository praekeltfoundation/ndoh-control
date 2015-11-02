from django.core.management.base import BaseCommand
from optparse import make_option
from snappybouncer.models import Ticket


class Command(BaseCommand):
    help = "For every Snappy Ticket that has a support_id but "\
           "does not have an Operator, this will populate the "\
           "Operator, Tag and Faccode fields for that Ticket"
    option_list = BaseCommand.option_list + (
        make_option('--dry_run', action='store_true', default=False),
    )

    def handle(self, *args, **options):

        self.stdout.write('Finding tickets with support ids...\n')
        tickets_with_support_id = Ticket.objects.exclude(support_id=None)
        counter1 = tickets_with_support_id.count()
        self.stdout.write('Tickets with support ids found: %s\n' % counter1)

        self.stdout.write('Finding subset tickets without operators...\n')
        tickets = tickets_with_support_id.exclude(operator=None)
        counter2 = tickets.count()
        self.stdout.write('Subset tickets found: %s\n' % counter2)

        if not options["dry_run"]:
            # tickets_with_support_id.delete()
            # self.stdout.write('Deleted %s tickets' % counter)
            pass
        else:
            # self.stdout.write('%s tickets would be deleted' % counter)
            pass
