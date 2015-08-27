from django.db import models


class Source(models.Model):
    """ The source from which a registation originates.
    """
    name = models.CharField(max_length=100, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Registration(models.Model):
    """ A registation submitted via Vumi or external sources.
        Upon saving a registration, 3 things should happen:
        1. Send registration information to Jembi
        2. Create or update the contact on Vumi
        3. Create a subscription for the mom
    """
    hcw_msisdn = models.CharField(max_length=255, null=True, blank=True)
    mom_msisdn = models.CharField(max_length=255, null=False, blank=False)
    mom_id_type = models.CharField(max_length=8, null=False, blank=False)
    mom_lang = models.CharField(max_length=3, null=False, blank=False)
    mom_edd = models.DateField(null=True, blank=True)
    mom_id_no = models.CharField(max_length=100, null=True, blank=True)
    mom_dob = models.DateField(null=True, blank=True)
    clinic_code = models.CharField(max_length=100, null=True, blank=True)
    authority = models.CharField(max_length=6, null=False, blank=False)
    source = models.ForeignKey(Source, related_name='registrations',
                               null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"Registration for %s" % self.mom_msisdn
