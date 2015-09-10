from django.db import models
from django.contrib.auth.models import User


class Source(models.Model):
    """ The source from which a registation originates.
        The user foreignkey is used to identify the source based on the
        user's api token.
    """
    name = models.CharField(max_length=100, null=False, blank=False)
    user = models.ForeignKey(User, related_name='sources', null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"%s" % self.name


class Registration(models.Model):
    """ A registation submitted via Vumi or external sources.
        Upon saving a registration, 3 things should happen:
        1. Send registration information to Jembi
        2. Create or update the contact on Vumi
        3. Create a subscription for the mom

        Authority determines which subscriptions a registration can
        subscribe to:
        'personal' - subscription
        'chw' - chw
        'clinic' - standard, later, accelerated
    """
    ID_TYPE_CHOICES = (
        ('sa_id', 'SA ID'),
        ('passport', 'Passport'),
        ('none', 'None'),
    )
    LANG_CHOICES = (
        ('en', 'English'),
        ('af', 'Afrikaans'),
        ('zu', 'Zulu'),
        ('xh', 'Xhosa'),
        ('st', 'Sotho'),
        ('tn', 'Setswana'),
    )
    AUTHORITY_CHOICES = (
        ('personal', 'Personal / Public'),
        ('chw', 'CHW'),
        ('clinic', 'Clinic'),
    )
    hcw_msisdn = models.CharField(max_length=255, null=True, blank=True)
    mom_msisdn = models.CharField(max_length=255, null=False, blank=False)
    mom_id_type = models.CharField(max_length=8, null=False, blank=False,
                                   choices=ID_TYPE_CHOICES)
    mom_passport_origin = models.CharField(max_length=100, null=True,
                                           blank=True)
    mom_lang = models.CharField(max_length=3, null=False, blank=False,
                                choices=LANG_CHOICES)
    mom_edd = models.DateField(null=True, blank=True)
    mom_id_no = models.CharField(max_length=100, null=True, blank=True)
    mom_dob = models.DateField(null=True, blank=True)
    clinic_code = models.CharField(max_length=100, null=True, blank=True)
    authority = models.CharField(max_length=8, null=False, blank=False,
                                 choices=AUTHORITY_CHOICES)
    source = models.ForeignKey(Source, related_name='registrations',
                               null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"Registration for %s" % self.mom_msisdn
