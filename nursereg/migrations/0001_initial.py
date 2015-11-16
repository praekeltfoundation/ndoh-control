# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'NurseSource'
        db.create_table(u'nursereg_nursesource', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='nursesources', to=orm['auth.User'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'nursereg', ['NurseSource'])

        # Adding model 'NurseReg'
        db.create_table(u'nursereg_nursereg', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('cmsisdn', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('dmsisdn', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('rmsisdn', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('faccode', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('id_type', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('id_no', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('passport_origin', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('dob', self.gf('django.db.models.fields.DateField')()),
            ('nurse_source', self.gf('django.db.models.fields.related.ForeignKey')(related_name='nurseregs', to=orm['nursereg.NurseSource'])),
            ('persal_no', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('opted_out', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('optout_reason', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('optout_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('sanc_reg_no', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'nursereg', ['NurseReg'])


    def backwards(self, orm):
        # Deleting model 'NurseSource'
        db.delete_table(u'nursereg_nursesource')

        # Deleting model 'NurseReg'
        db.delete_table(u'nursereg_nursereg')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'nursereg.nursereg': {
            'Meta': {'object_name': 'NurseReg'},
            'cmsisdn': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dmsisdn': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'dob': ('django.db.models.fields.DateField', [], {}),
            'faccode': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'id_no': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id_type': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'nurse_source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nurseregs'", 'to': u"orm['nursereg.NurseSource']"}),
            'opted_out': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'optout_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'optout_reason': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'passport_origin': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'persal_no': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'rmsisdn': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'sanc_reg_no': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'nursereg.nursesource': {
            'Meta': {'object_name': 'NurseSource'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nursesources'", 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['nursereg']