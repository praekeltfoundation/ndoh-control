from django.db import models
# from django.utils import timezone
# import datetime
from djcelery.models import PeriodicTask
from autodatetimefields.models import AutoNewDateTimeField, AutoDateTimeField


class MessageSet(models.Model):
    """ Core details about a set of messages that a user
        can be sent
    """
    short_name = models.CharField(max_length=20)
    notes = models.CharField(max_length=200, verbose_name=u'Notes', null=True, blank=True)
    next_set = models.ForeignKey('self',
                                         # related_name='next_set',
                                         null=True,
                                         blank=True)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    def __unicode__(self):
        return "%s" % self.short_name


class Message(models.Model):
    """ A message that a user can be sent
    """
    message_set = models.ForeignKey(MessageSet,
                                         related_name='messages',
                                         null=False)
    sequence_number = models.IntegerField(null=False, blank=False)
    lang = models.CharField(max_length=3, null=False, blank=False)
    content = models.TextField(null=False, blank=False)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    def __unicode__(self):
        return "Message %s from %s" % (self.sequence_number, self.message_set.short_name)


class Subscription(models.Model):
    """ Users subscriptions and their status
    """
    user_account = models.CharField(max_length=36, null=False, blank=False)
    contact_key = models.CharField(max_length=36, null=False, blank=False)
    to_addr = models.CharField(max_length=255, null=False, blank=False)
    message_set = models.ForeignKey(MessageSet,
                                         related_name='subscribers',
                                         null=False)
    next_sequence_number = models.IntegerField(default=1, null=False, blank=False)
    lang = models.CharField(max_length=3, null=False, blank=False)
    active = models.BooleanField(default=True)
    completed = models.BooleanField(default=False)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)
    schedule =  models.ForeignKey(PeriodicTask,
                                        related_name='subscriptions',
                                        null=False)

    def __unicode__(self):
        return "%s to %s" % (self.contact_key, self.message_set.short_name)

from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^autodatetimefields\.models\.AutoNewDateTimeField", "^autodatetimefields\.models\.AutoDateTimeField"])
