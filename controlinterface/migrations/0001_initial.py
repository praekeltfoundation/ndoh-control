# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'WidgetData'
        db.create_table(u'controlinterface_widgetdata', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('data_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('created_at', self.gf('controlinterface.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('controlinterface.models.AutoDateTimeField')(blank=True)),
        ))
        db.send_create_signal(u'controlinterface', ['WidgetData'])

        # Adding model 'Widget'
        db.create_table(u'controlinterface_widget', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('type_of', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('data_from', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('interval', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('nulls', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('created_at', self.gf('controlinterface.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('controlinterface.models.AutoDateTimeField')(blank=True)),
        ))
        db.send_create_signal(u'controlinterface', ['Widget'])

        # Adding M2M table for field data on 'Widget'
        m2m_table_name = db.shorten_name(u'controlinterface_widget_data')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('widget', models.ForeignKey(orm[u'controlinterface.widget'], null=False)),
            ('widgetdata', models.ForeignKey(orm[u'controlinterface.widgetdata'], null=False))
        ))
        db.create_unique(m2m_table_name, ['widget_id', 'widgetdata_id'])

        # Adding model 'Dashboard'
        db.create_table(u'controlinterface_dashboard', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('dashboard_type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('created_at', self.gf('controlinterface.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('controlinterface.models.AutoDateTimeField')(blank=True)),
        ))
        db.send_create_signal(u'controlinterface', ['Dashboard'])

        # Adding M2M table for field widgets on 'Dashboard'
        m2m_table_name = db.shorten_name(u'controlinterface_dashboard_widgets')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('dashboard', models.ForeignKey(orm[u'controlinterface.dashboard'], null=False)),
            ('widget', models.ForeignKey(orm[u'controlinterface.widget'], null=False))
        ))
        db.create_unique(m2m_table_name, ['dashboard_id', 'widget_id'])

        # Adding model 'UserDashboard'
        db.create_table(u'controlinterface_userdashboard', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('default_dashboard', self.gf('django.db.models.fields.related.ForeignKey')(related_name='default', to=orm['controlinterface.Dashboard'])),
            ('created_at', self.gf('controlinterface.models.AutoNewDateTimeField')(blank=True)),
            ('updated_at', self.gf('controlinterface.models.AutoDateTimeField')(blank=True)),
        ))
        db.send_create_signal(u'controlinterface', ['UserDashboard'])

        # Adding M2M table for field dashboards on 'UserDashboard'
        m2m_table_name = db.shorten_name(u'controlinterface_userdashboard_dashboards')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('userdashboard', models.ForeignKey(orm[u'controlinterface.userdashboard'], null=False)),
            ('dashboard', models.ForeignKey(orm[u'controlinterface.dashboard'], null=False))
        ))
        db.create_unique(m2m_table_name, ['userdashboard_id', 'dashboard_id'])


    def backwards(self, orm):
        # Deleting model 'WidgetData'
        db.delete_table(u'controlinterface_widgetdata')

        # Deleting model 'Widget'
        db.delete_table(u'controlinterface_widget')

        # Removing M2M table for field data on 'Widget'
        db.delete_table(db.shorten_name(u'controlinterface_widget_data'))

        # Deleting model 'Dashboard'
        db.delete_table(u'controlinterface_dashboard')

        # Removing M2M table for field widgets on 'Dashboard'
        db.delete_table(db.shorten_name(u'controlinterface_dashboard_widgets'))

        # Deleting model 'UserDashboard'
        db.delete_table(u'controlinterface_userdashboard')

        # Removing M2M table for field dashboards on 'UserDashboard'
        db.delete_table(db.shorten_name(u'controlinterface_userdashboard_dashboards'))


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
        u'controlinterface.dashboard': {
            'Meta': {'object_name': 'Dashboard'},
            'created_at': ('controlinterface.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            'dashboard_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'updated_at': ('controlinterface.models.AutoDateTimeField', [], {'blank': 'True'}),
            'widgets': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['controlinterface.Widget']", 'null': 'True', 'blank': 'True'})
        },
        u'controlinterface.userdashboard': {
            'Meta': {'object_name': 'UserDashboard'},
            'created_at': ('controlinterface.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            'dashboards': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'dashboards'", 'symmetrical': 'False', 'to': u"orm['controlinterface.Dashboard']"}),
            'default_dashboard': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'default'", 'to': u"orm['controlinterface.Dashboard']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'updated_at': ('controlinterface.models.AutoDateTimeField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'controlinterface.widget': {
            'Meta': {'object_name': 'Widget'},
            'created_at': ('controlinterface.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            'data': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['controlinterface.WidgetData']", 'null': 'True', 'blank': 'True'}),
            'data_from': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'nulls': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'type_of': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'updated_at': ('controlinterface.models.AutoDateTimeField', [], {'blank': 'True'})
        },
        u'controlinterface.widgetdata': {
            'Meta': {'object_name': 'WidgetData'},
            'created_at': ('controlinterface.models.AutoNewDateTimeField', [], {'blank': 'True'}),
            'data_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'updated_at': ('controlinterface.models.AutoDateTimeField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['controlinterface']