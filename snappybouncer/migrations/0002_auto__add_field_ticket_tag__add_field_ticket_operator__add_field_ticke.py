# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Ticket.tag'
        db.add_column(u'snappybouncer_ticket', 'tag',
                      self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Ticket.operator'
        db.add_column(u'snappybouncer_ticket', 'operator',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Ticket.faccode'
        db.add_column(u'snappybouncer_ticket', 'faccode',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Ticket.tag'
        db.delete_column(u'snappybouncer_ticket', 'tag')

        # Deleting field 'Ticket.operator'
        db.delete_column(u'snappybouncer_ticket', 'operator')

        # Deleting field 'Ticket.faccode'
        db.delete_column(u'snappybouncer_ticket', 'faccode')


    models = {
        u'snappybouncer.conversation': {
            'Meta': {'object_name': 'Conversation'},
            'created_at': ('snappybouncer.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '43'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated_at': ('snappybouncer.models.AutoDateTimeField', [], {'blank': 'True'}),
            'user_account': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'conversations'", 'to': u"orm['snappybouncer.UserAccount']"})
        },
        u'snappybouncer.ticket': {
            'Meta': {'object_name': 'Ticket'},
            'contact_key': ('django.db.models.fields.CharField', [], {'max_length': '43'}),
            'conversation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tickets'", 'to': u"orm['snappybouncer.Conversation']"}),
            'created_at': ('snappybouncer.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            'faccode': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'msisdn': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'operator': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'support_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'support_nonce': ('django.db.models.fields.CharField', [], {'max_length': '43', 'null': 'True', 'blank': 'True'}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'updated_at': ('snappybouncer.models.AutoDateTimeField', [], {'blank': 'True'})
        },
        u'snappybouncer.useraccount': {
            'Meta': {'object_name': 'UserAccount'},
            'created_at': ('snappybouncer.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '43'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'updated_at': ('snappybouncer.models.AutoDateTimeField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['snappybouncer']