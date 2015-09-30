from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
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
        ('zu', 'isiZulu'),
        ('xh', 'isiXhosa'),
        ('af', 'Afrikaans'),
        ('en', 'English'),
        ('nso', 'Sesotho sa Leboa'),
        ('tn', 'Setswana'),
        ('st', 'Sesotho'),
        ('ts', 'Xitsonga'),
        ('ss', 'siSwati'),
        ('ve', 'Tshivenda'),
        ('nr', 'isiNdebele'),
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

    def clean(self):
        if self.mom_id_type == 'sa_id' and self.mom_id_no is None:
            raise ValidationError(
                _("Provide an id number in the mom_id_no field."))
        if self.mom_id_type == 'sa_id' and self.mom_dob is None:
            # TODO #97 Optimise by extracting dob from ID number
            raise ValidationError(
                _("Provide a date of birth in the mom_dob field."))
        if self.mom_id_type == 'passport' and self.mom_id_no is None:
            raise ValidationError(
                _("Provide a passport number in the mom_id_no field."))
        if self.mom_id_type == 'passport' and self.mom_passport_origin is None:
            raise ValidationError(
                _("Provide a passport country of origin in the \
                   mom_passport_origin field."))
        if self.authority == 'clinic' and self.mom_id_type == 'none' and \
           self.mom_dob is None:
            raise ValidationError(
                _("Provide the mother's date of birth in the mom_dob field."))
        if self.authority == 'clinic' and self.mom_edd is None:
            raise ValidationError(
                _("Provide an estimated due date in the mom_edd field."))
        if self.authority == 'clinic' and self.clinic_code is None:
            raise ValidationError(
                _("Provide a clinic code in the clinic_code field."))

    def save(self, *args, **kwargs):
        self.clean()
        super(Registration, self).save(*args, **kwargs)


from django.db.models.signals import post_save
from django.dispatch import receiver
from .tasks import jembi_post_json, jembi_post_xml, update_create_vumi_contact


@receiver(post_save, sender=Registration)
def fire_jembi_post(sender, instance, created, **kwargs):
    """ Send the registration info to Jembi.
        For the clinic and chw registrations, fires an additional task that
        uploads an XML document.
    """
    if created:
        # Fire Jembi send tasks
        jembi_post_json.apply_async(
            kwargs={"registration_id": instance.id})

        if (instance.authority == 'clinic' or instance.authority == 'chw'):
            jembi_post_xml.apply_async(
                kwargs={"registration_id": instance.id})

        # Fire Contact update create tasks
        update_create_vumi_contact.apply_async(
            kwargs={"registration_id": instance.id})
