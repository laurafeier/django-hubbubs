# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Subscription'
        db.create_table('hubbubs_subscription', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('topic', self.gf('django.db.models.fields.URLField')(max_length=255)),
            ('hub', self.gf('django.db.models.fields.URLField')(max_length=255)),
            ('verify_token', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('secret', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('lease_expiration', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'], null=True, blank=True)),
        ))
        db.send_create_signal('hubbubs', ['Subscription'])

        # Adding unique constraint on 'Subscription', fields ['topic', 'site']
        db.create_unique('hubbubs_subscription', ['topic', 'site_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Subscription', fields ['topic', 'site']
        db.delete_unique('hubbubs_subscription', ['topic', 'site_id'])

        # Deleting model 'Subscription'
        db.delete_table('hubbubs_subscription')


    models = {
        'hubbubs.subscription': {
            'Meta': {'unique_together': "(('topic', 'site'),)", 'object_name': 'Subscription'},
            'hub': ('django.db.models.fields.URLField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lease_expiration': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']", 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'topic': ('django.db.models.fields.URLField', [], {'max_length': '255'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'verify_token': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['hubbubs']
