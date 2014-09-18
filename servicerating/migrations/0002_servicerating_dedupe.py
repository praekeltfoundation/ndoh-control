# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    depends_on = (
        ("subscription", "0002_addcleanuptask"),
    )

    def forwards(self, orm):
        crontab = orm['djcelery.CrontabSchedule'](
            month_of_year="*",
            day_of_week="*",
            hour="5",
            minute="0",
            day_of_month="*"
        )
        crontab.save()
        task = orm['djcelery.PeriodicTask'](
            task="servicerating.tasks.ensure_one_servicerating", 
            name="Ensure Clean Servicerating", 
            args="[]", 
            enabled=True, 
            crontab=crontab, 
            kwargs="{}",
            description=""
        )
        task.save()
        
    def backwards(self, orm):
        pass

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
    symmetrical = True
