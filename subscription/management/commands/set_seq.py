from datetime import date
from math import floor

from django.core.management.base import BaseCommand
from django.conf import settings

from requests import HTTPError
from go_http.contacts import ContactsApiClient

from subscription.models import Subscription


class Command(BaseCommand):
    help = "Ensure a mom's subscription is inline with protocol schedule"

    def year_from_month(self, month):
        if int(month) > 8:
            return 2014  # due in 2014
        else:
            return 2015

    def clean_day(self, day):
        if int(day) < 31:
            return int(day)
        else:
            self.stdout.write(
                "Contact has malformed due day data \
                    of %s so making it 14" % day)
            return 14

    def clean_month(self, month):
        return int(month)

    def calc_weeks(self, due_date, today=None):
        if today is None:
            today = date.today()
        # calc diff betwen now and due day
        diff = (due_date - today).days
        # get it in weeks
        diff_weeks = int(floor((diff / 7)))
        # get preg week
        preg_week = 40 - diff_weeks
        # You can't be less than two week preg
        if preg_week <= 1:
            return False
        elif preg_week > 41:
            return 41
        else:
            return preg_week

    def calc_sequence_start(self, weeks, schedule):
        # calculates which sms in the sequence to start with
        if schedule == 1:
            if weeks < 5:
                seq_start = 1
            elif weeks < 41:
                seq_start = ((weeks - 4) * 2) - 1
            else:
                self.stdout.write("Fast forwarding to end")
                seq_start = 73
        else:
            if weeks < 40:
                seq_start = ((weeks - 30) * 3) - 2
            else:
                self.stdout.write("Fast forwarding to end")
                seq_start = 28
        return seq_start

    def handle(self, *args, **options):
        # Get all subscribers
        subscribers = Subscription.objects.filter(
            active=True, completed=False, message_set__lte=2).all()

        # Make a reuseable contact api connection
        contacts = ContactsApiClient(settings.VUMI_GO_API_TOKEN)
        for subscriber in subscribers:
            self.stdout.write("Getting: " + subscriber.contact_key)
            try:
                contact = contacts.get_contact(subscriber.contact_key)
                if "extra" in contact \
                        and "due_date_day" in contact["extra"] \
                        and "due_date_month" in contact["extra"]:
                    year = self.year_from_month(
                        contact["extra"]["due_date_month"])
                    month = self.clean_month(
                        contact["extra"]["due_date_month"])
                    day = self.clean_day(contact["extra"]["due_date_day"])
                    due_date = date(year, month, day)
                    weeks = self.calc_weeks(due_date)
                    self.stdout.write("Mother due %s" % due_date.isoformat())
                    self.stdout.write("Week of preg %s" % weeks)
                else:
                    if "extra" in contact \
                            and "due_date_month" in contact["extra"]:
                        year = self.year_from_month(
                            contact["extra"]["due_date_month"])
                        month = self.clean_month(
                            contact["extra"]["due_date_month"])
                        day = 14
                        self.stdout.write(
                            "Contact %s has no due day data so making it 14" %
                            subscriber.contact_key)
                        weeks = self.calc_weeks(due_date)
                        self.stdout.write(
                            "Mother due %s" % due_date.isoformat())
                        self.stdout.write("Week of preg %s" % weeks)
                sub_type = int(contact["extra"]["subscription_type"])
                self.stdout.write("Sub type is %s" % sub_type)
                new_seq_num = self.calc_sequence_start(weeks, sub_type)
                self.stdout.write("Setting to seq %s" % new_seq_num)
                subscriber.next_sequence_number = new_seq_num
                subscriber.save()

            except HTTPError as err:
                self.stdout.write(
                    "Contact %s threw %s" % (subscriber.contact_key,
                                             err.response.status_code))
