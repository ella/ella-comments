# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        db.rename_table('ellacomments_commentoptionsobject', 'ella_comments_commentoptionsobject')
        db.rename_table('ellacomments_bannedip', 'ella_comments_bannedip')


    def backwards(self, orm):
        db.rename_table('ella_comments_commentoptionsobject', 'ellacomments_commentoptionsobject')
        db.rename_table('ella_comments_bannedip', 'ellacomments_bannedip')

    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ella_comments.bannedip': {
            'Meta': {'object_name': 'BannedIP'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'unique': 'True', 'max_length': '15'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'ella_comments.commentoptionsobject': {
            'Meta': {'unique_together': "(('target_ct', 'target_id'),)", 'object_name': 'CommentOptionsObject'},
            'blocked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'check_profanities': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'premoderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target_ct': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'target_id': ('django.db.models.fields.PositiveIntegerField', [], {})
        }
    }

    complete_apps = ['ella_comments']
