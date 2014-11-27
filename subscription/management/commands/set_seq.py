from datetime import date, datetime
from math import floor

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q

from requests import HTTPError
from go_http.contacts import ContactsApiClient

from subscription.models import Subscription


SUBSCRIPTION_STANDARD = 1  # less than week 32 when reg
SUBSCRIPTION_LATER = 2  # 32-35 when reg


class Command(BaseCommand):
    help = "Ensure a mom's subscription is inline with protocol schedule"

    client_class = ContactsApiClient

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
            today = self.get_now().date()
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
        if schedule == SUBSCRIPTION_STANDARD:
            if weeks < 5:
                # Start from beginning
                seq_start = 1
            elif weeks < 41:
                # Message starts at week 5, sequence starts at 1
                START_OFFSET = 4
                PER_WEEK = 2
                seq_start = (
                    (weeks - START_OFFSET) * PER_WEEK) - (PER_WEEK - 1)
            else:
                self.stdout.write("Fast forwarding to end\n")
                # Start of last week on schedule
                seq_start = 73
        elif schedule == SUBSCRIPTION_LATER:
            if weeks < 40:
                # Message starts at week 31, sequence starts at 1
                START_OFFSET = 30
                PER_WEEK = 3
                seq_start = (
                    (weeks - START_OFFSET) * PER_WEEK) - (PER_WEEK - 1)
            else:
                self.stdout.write("Fast forwarding to end\n")
                # Start of last week on schedule
                seq_start = 28
        else:
            self.stdout.write("Unexpected schedule\n")
            seq_start = 0
        return seq_start

    def get_now(self):
        return datetime.now()

    def handle(self, *args, **options):
        subscribers = Subscription.objects.filter(
            Q(active=True), Q(completed=False),
            Q(message_set__short_name='standard') | Q(message_set__short_name='later'))

        # Make a reuseable contact api connection
        contacts = self.client_class(settings.VUMI_GO_API_TOKEN)
        counter = 0.0
        started = self.get_now()
        for subscriber in subscribers:
            self.stdout.write("Getting: %s\n" % (subscriber.contact_key,))
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
                    self.stdout.write("Mother due %s\n" % due_date.isoformat())
                    self.stdout.write("Week of preg %s\n" % weeks)
                elif "extra" in contact \
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
                if sub_type is not int(subscriber.message_set_id):
                    self.stdout.write("Sub type %s does not match contact sub type %s\n" % (
                        sub_type, int(subscriber.message_set_id)))
                else:
                    self.stdout.write("Sub type is %s\n" % sub_type)
                    new_seq_num = self.calc_sequence_start(weeks, sub_type)
                    self.stdout.write("Setting to seq %s from %s\n" % (
                        new_seq_num, str(subscriber.next_sequence_number)))
                    subscriber.next_sequence_number = new_seq_num
                    subscriber.save()
                    counter += 1.0
                    delta = self.get_now() - started
                    # Make sure we're not dividing by zero
                    if delta.seconds > 0:
                        per_second = (
                            counter / float((self.get_now() - started).seconds))
                    else:
                        per_second = 'unknown'
                    self.stdout.write(
                        "Updated %s subscribers at %s per second\n" % (counter, per_second))

            except ValueError as err:
                self.stdout.write(
                    "Contact %s threw %s\n" % (subscriber.contact_key, err))

            except KeyError as err:
                self.stdout.write(
                    "Contact %s threw KeyError on %s\n" % (subscriber.contact_key, err))

            except HTTPError as err:
                self.stdout.write(
                    "Contact %s threw %s\n" % (subscriber.contact_key,
                                               err.response.status_code))
        self.stdout.write("Completed\n")
