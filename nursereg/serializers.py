from rest_framework import serializers
from django.contrib.auth.models import User, Group
from .models import NurseSource, NurseReg


class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Group
        fields = ('url', 'name')


class NurseSourceSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = NurseSource
        fields = ('url', 'id', 'name', 'user')


class NurseRegSerializer(serializers.ModelSerializer):

    class Meta:
        model = NurseReg
        fields = ('id', 'msisdn', 'faccode', 'id_type', 'id_no',
                  'passport_origin', 'dob', 'nurse_source', 'persal_no',
                  'opted_out', 'optout_reason', 'optout_count', 'sanc_reg_no',)
