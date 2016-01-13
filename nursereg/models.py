from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User


class NurseSource(models.Model):
    """ The source from which a nurse registation originates.
        The user foreignkey is used to identify the source based on the
        user's api token.
    """
    name = models.CharField(max_length=100, null=False, blank=False)
    user = models.ForeignKey(User, related_name='nursesources', null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"%s" % self.name


class NurseReg(models.Model):
    """ A nurse registation submitted via Vumi or external sources.
        Upon saving a registration, 3 things should happen:
        1. Send nurse registration information to Jembi
        2. Create or update the nurse's contact on Vumi
        3. Create a subscription for the nurse
    """
    ID_TYPE_CHOICES = (
        ('sa_id', 'SA ID'),
        ('passport', 'Passport'),
    )
    COUNTRY_CHOICES = (
        ('na', 'Namibia'),
        ('bw', 'Botswana'),
        ('mz', 'Mozambique'),
        ('sz', 'Swaziland'),
        ('ls', 'Lesotho'),
        ('cu', 'Cuba'),
        ('other', 'Other'),
    )
    OPTOUT_REASON_CHOICES = (
        ('job_change', 'Job changed'),
        ('number_owner_change', 'Number owner change'),
        ('not_useful', 'Messages not useful'),
        ('other', 'Other'),
    )
    cmsisdn = models.CharField(max_length=255)
    dmsisdn = models.CharField(max_length=255, null=True, blank=True)
    rmsisdn = models.CharField(max_length=255, null=True, blank=True)
    faccode = models.CharField(max_length=100)
    id_type = models.CharField(max_length=8, choices=ID_TYPE_CHOICES)
    id_no = models.CharField(max_length=100, null=True, blank=True)
    passport_origin = models.CharField(max_length=100, null=True,
                                       blank=True, choices=COUNTRY_CHOICES)
    dob = models.DateField()
    nurse_source = models.ForeignKey(NurseSource, related_name='nurseregs',
                                     null=False)
    persal_no = models.IntegerField(null=True, blank=True)
    opted_out = models.BooleanField(default=False)
    optout_reason = models.CharField(max_length=100, null=True, blank=True,
                                     choices=OPTOUT_REASON_CHOICES)
    optout_count = models.IntegerField(default=0)
    sanc_reg_no = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"Nurse Registration for %s" % self.cmsisdn

    def clean(self):
        if self.id_type == 'sa_id' and self.id_no is None:
            raise ValidationError(
                _("Provide an id number in the id_no field."))
        if self.id_type == 'sa_id' and self.dob is None:
            # TODO #97 Optimise by extracting dob from ID number
            raise ValidationError(
                _("Provide a date of birth in the dob field."))
        if self.id_type == 'passport' and self.id_no is None:
            raise ValidationError(
                _("Provide a passport number in the id_no field."))
        if self.id_type == 'passport' and self.passport_origin is None:
            raise ValidationError(
                _("Provide a passport country of origin in the \
                   passport_origin field."))
        if self.opted_out and self.optout_reason is None:
            raise ValidationError(
                _("Provide an optout reason in the optout_reason field."))
        if self.opted_out and self.optout_count == 0:
            raise ValidationError(
                _("Provide a valid integer in the optout_count field."))

    def save(self, *args, **kwargs):
        self.clean()
        if self.dmsisdn is None:
            self.dmsisdn = self.cmsisdn
        super(NurseReg, self).save(*args, **kwargs)


from django.db.models.signals import post_save
from django.dispatch import receiver
from .tasks import update_create_vumi_contact, jembi_post_json


@receiver(post_save, sender=NurseReg)
def nursereg_postsave(sender, instance, created, **kwargs):
    """ Send the registration info to Jembi, then create or
        update the Vumi contact. Contact editing contains
        the code for creating a new subscription.
    """
    if created:
        # Fire Jembi send tasks
        jembi_post_json.apply_async(
            kwargs={"nursereg_id": instance.id})

        # Fire Contact update create tasks
        update_create_vumi_contact.apply_async(
            kwargs={"nursereg_id": instance.id})
