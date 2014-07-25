# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserAccount'
        db.create_table(u'servicerating_useraccount', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=43)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_at', self.gf('servicerating.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('servicerating.models.AutoDateTimeField')(blank=True)),
        ))
        db.send_create_signal(u'servicerating', ['UserAccount'])

        # Adding model 'Conversation'
        db.create_table(u'servicerating_conversation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user_account', self.gf('django.db.models.fields.related.ForeignKey')(related_name='conversations', to=orm['servicerating.UserAccount'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=43)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_at', self.gf('servicerating.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('servicerating.models.AutoDateTimeField')(blank=True)),
        ))
        db.send_create_signal(u'servicerating', ['Conversation'])

        # Adding model 'Contact'
        db.create_table(u'servicerating_contact', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('conversation', self.gf('django.db.models.fields.related.ForeignKey')(related_name='contacts', to=orm['servicerating.Conversation'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=43)),
            ('value', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('msisdn', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('created_at', self.gf('servicerating.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('servicerating.models.AutoDateTimeField')(blank=True)),
        ))
        db.send_create_signal(u'servicerating', ['Contact'])

        # Adding model 'Response'
        db.create_table(u'servicerating_response', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contact', self.gf('django.db.models.fields.related.ForeignKey')(related_name='contact_responses', to=orm['servicerating.Contact'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('value', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('created_at', self.gf('servicerating.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('servicerating.models.AutoDateTimeField')(blank=True)),
        ))
        db.send_create_signal(u'servicerating', ['Response'])

        # Adding model 'Extra'
        db.create_table(u'servicerating_extra', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contact', self.gf('django.db.models.fields.related.ForeignKey')(related_name='extras', to=orm['servicerating.Contact'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('value', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('created_at', self.gf('servicerating.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('servicerating.models.AutoDateTimeField')(blank=True)),
        ))
        db.send_create_signal(u'servicerating', ['Extra'])


    def backwards(self, orm):
        # Deleting model 'UserAccount'
        db.delete_table(u'servicerating_useraccount')

        # Deleting model 'Conversation'
        db.delete_table(u'servicerating_conversation')

        # Deleting model 'Contact'
        db.delete_table(u'servicerating_contact')

        # Deleting model 'Response'
        db.delete_table(u'servicerating_response')

        # Deleting model 'Extra'
        db.delete_table(u'servicerating_extra')


    models = {
        u'servicerating.contact': {
            'Meta': {'object_name': 'Contact'},
            'conversation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contacts'", 'to': u"orm['servicerating.Conversation']"}),
            'created_at': ('servicerating.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '43'}),
            'msisdn': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated_at': ('servicerating.models.AutoDateTimeField', [], {'blank': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'servicerating.conversation': {
            'Meta': {'object_name': 'Conversation'},
            'created_at': ('servicerating.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '43'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated_at': ('servicerating.models.AutoDateTimeField', [], {'blank': 'True'}),
            'user_account': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'conversations'", 'to': u"orm['servicerating.UserAccount']"})
        },
        u'servicerating.extra': {
            'Meta': {'object_name': 'Extra'},
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'extras'", 'to': u"orm['servicerating.Contact']"}),
            'created_at': ('servicerating.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'updated_at': ('servicerating.models.AutoDateTimeField', [], {'blank': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'servicerating.response': {
            'Meta': {'object_name': 'Response'},
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contact_responses'", 'to': u"orm['servicerating.Contact']"}),
            'created_at': ('servicerating.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'updated_at': ('servicerating.models.AutoDateTimeField', [], {'blank': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'servicerating.useraccount': {
            'Meta': {'object_name': 'UserAccount'},
            'created_at': ('servicerating.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '43'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated_at': ('servicerating.models.AutoDateTimeField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['servicerating']