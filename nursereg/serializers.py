from rest_framework import serializers
from .models import NurseSource, NurseReg


class NurseSourceSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = NurseSource
        fields = ('url', 'id', 'name', 'user')


class NurseRegSerializer(serializers.ModelSerializer):

    class Meta:
        model = NurseReg
        fields = ('id', 'cmsisdn', 'dmsisdn', 'rmsisdn', 'faccode', 'id_type',
                  'id_no', 'passport_origin', 'dob', 'nurse_source',
                  'persal_no', 'opted_out', 'optout_reason', 'optout_count',
                  'sanc_reg_no',)
