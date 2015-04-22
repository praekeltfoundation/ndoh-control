from django.core.management.base import BaseCommand
from optparse import make_option

from subscription.models import Subscription


class Command(BaseCommand):
    help = "Sets MSISDN of all subscriptions to have a plus if missing"
    option_list = BaseCommand.option_list + (
        make_option('--dry_run', action='store_true', default=False),
    )

    def clean_msisdn(self, msisdn):
        if msisdn.strip()[0] == "+":
            return msisdn.strip()
        else:
            return "+%s" % (msisdn.strip())

    def handle(self, *args, **options):

        subscribers = Subscription.objects.exclude(
            to_addr__startswith="+")
        self.stdout.write("Affected records: %s\n" % (subscribers.count()))

        if not options["dry_run"]:
            for subscriber in subscribers:
                # make current subscription completed

                subscriber.to_addr = self.clean_msisdn(subscriber.to_addr)
                subscriber.save()

            self.stdout.write("Records updated\n")
