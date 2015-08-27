from rest_framework import serializers

from .models import Source, Registration


class SourceSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Source
        fields = ('url', 'id', 'name')


class RegistrationSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Registration
        fields = ('url', 'id', 'hcw_msisdn', 'mom_msisdn', 'mom_id_type',
                  'mom_lang', 'mom_edd', 'mom_id_no', 'mom_dob', 'clinic_code',
                  'authority', 'source', )
