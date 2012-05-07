# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'CommentOptionsObject.target_id'
        db.alter_column('ella_comments_commentoptionsobject', 'target_id', self.gf('django.db.models.fields.TextField')())


    def backwards(self, orm):
        
        # Changing field 'CommentOptionsObject.target_id'
        db.alter_column('ella_comments_commentoptionsobject', 'target_id', self.gf('django.db.models.fields.PositiveIntegerField')())


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ella_comments.commentoptionsobject': {
            'Meta': {'unique_together': "(('target_ct', 'target_id'),)", 'object_name': 'CommentOptionsObject'},
            'blocked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'check_profanities': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'premoderated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target_ct': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'target_id': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['ella_comments', 'ella_comments']
