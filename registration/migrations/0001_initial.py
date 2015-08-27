# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Source'
        db.create_table(u'registration_source', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'registration', ['Source'])

        # Adding model 'Registration'
        db.create_table(u'registration_registration', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('hcw_msisdn', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('mom_msisdn', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('mom_id_type', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('mom_lang', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('mom_edd', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('mom_id_no', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('mom_dob', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('clinic_code', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('authority', self.gf('django.db.models.fields.CharField')(max_length=6)),
            ('source', self.gf('django.db.models.fields.related.ForeignKey')(related_name='registrations', to=orm['registration.Source'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'registration', ['Registration'])


    def backwards(self, orm):
        # Deleting model 'Source'
        db.delete_table(u'registration_source')

        # Deleting model 'Registration'
        db.delete_table(u'registration_registration')


    models = {
        u'registration.registration': {
            'Meta': {'object_name': 'Registration'},
            'authority': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'clinic_code': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'hcw_msisdn': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mom_dob': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'mom_edd': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'mom_id_no': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'mom_id_type': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'mom_lang': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'mom_msisdn': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'registrations'", 'to': u"orm['registration.Source']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'registration.source': {
            'Meta': {'object_name': 'Source'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['registration']