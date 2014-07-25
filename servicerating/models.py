from django.db import models
from django.utils import timezone
from django.db.models import DateTimeField


# Modelled on https://github.com/jamesmarlowe/django-AutoDateTimeFields 
# But with timezone support
class AutoDateTimeField(DateTimeField):
    def pre_save(self, model_instance, add):
        now = timezone.now()
        setattr(model_instance, self.attname, now)
        return now


class AutoNewDateTimeField(DateTimeField):
    def pre_save(self, model_instance, add):
        if not add:
            return getattr(model_instance, self.attname)
        now = timezone.now()
        setattr(model_instance, self.attname, now)
        return now


class UserAccount(models.Model):
    """ Vumi User Accounts that can send data
    """
    key = models.CharField(max_length=43)
    name = models.CharField(max_length=200)
    notes = models.TextField(verbose_name=u'Notes', null=True, blank=True)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    def __unicode__(self):
        return "%s" % self.name


class Conversation(models.Model):
    """ A conversation that can deliver messages into system
    """
    user_account = models.ForeignKey(UserAccount,
                                         related_name='conversations',
                                         null=False)
    key = models.CharField(max_length=43)
    name = models.CharField(max_length=200)
    notes = models.TextField(verbose_name=u'Notes', null=True, blank=True)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    def __unicode__(self):
        return "%s" % self.name

class Contact(models.Model):
    """ A contact that can deliver messages into system
        Because contacts will change over time, there will
        be intentional duplicates
    """
    conversation = models.ForeignKey(Conversation,
                                         related_name='contacts',
                                         null=False)
    key = models.CharField(max_length=43)
    value = models.TextField(null=True, blank=True)
    msisdn = models.CharField(max_length=100)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    def __unicode__(self):
        return "%s" % self.key


class Response(models.Model):
    """ Contacts replies to request for input
    """
    contact = models.ForeignKey(Contact,
                                    related_name='contact_responses',
                                    null=False)
    key = models.CharField(max_length=200, null=False, blank=False)
    value = models.TextField(verbose_name=u'Value', blank=True)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    def __unicode__(self):
        return "Response from %s to %s in %s" % (self.contact.msisdn, self.key, self.contact.conversation.name)


class Extra(models.Model):
    """ Contacts extras
    """
    contact = models.ForeignKey(Contact,
                                    related_name='extras',
                                    null=False)
    key = models.CharField(max_length=200, null=False, blank=False)
    value = models.TextField(verbose_name=u'Value', blank=True)
    created_at = AutoNewDateTimeField(blank=True)
    updated_at = AutoDateTimeField(blank=True)

    def __unicode__(self):
        return "Extra of %s for %s in %s" % (self.key, self.contact.msisdn, self.contact.conversation.name)

from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^servicerating\.models\.AutoNewDateTimeField", "^servicerating\.models\.AutoDateTimeField"])
