from rest_framework import serializers
from django.contrib.auth.models import User, Group
from .models import Source, Registration


class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Group
        fields = ('url', 'name')


class SourceSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Source
        fields = ('url', 'id', 'name', 'user')


class RegistrationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Registration
        fields = ('id', 'hcw_msisdn', 'mom_msisdn', 'mom_id_type',
                  'mom_passport_origin', 'mom_lang', 'mom_edd', 'mom_id_no',
                  'mom_dob', 'clinic_code', 'authority', 'source', )
