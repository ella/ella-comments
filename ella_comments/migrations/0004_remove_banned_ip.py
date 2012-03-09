import datetime
from south.db import db
from django.db import models
from ella_comments.models import *

class Migration:

    def forwards(self, orm):
        # Deleting model 'BannedIP'
        db.delete_table('ellacomments_bannedip')


    def backwards(self, orm):
        # Adding model 'BannedIP'
        db.create_table('ellacomments_bannedip', (
            ('id', models.AutoField(primary_key=True)),
            ('created', models.DateTimeField(_('Created'), auto_now_add=True)),
            ('ip_address', models.IPAddressField(_('IP Address'), unique=True)),
            ('reason', models.CharField(_('Reason'), max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal('ella_comments', ['BannedIP'])





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
            'target_id': ('django.db.models.fields.PositiveIntegerField', [], {})
        }
    }

    complete_apps = ['ella_comments']
