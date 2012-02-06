import datetime

from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_unicode
from django.conf import settings

from threadedcomments.forms import ThreadedCommentForm


class AuthorizedCommentForm(ThreadedCommentForm):
    def __init__(self, *args, **kwargs):
        "there is no such thing as user_name, user_email, user_url"
        super(AuthorizedCommentForm, self).__init__(*args, **kwargs)
        self.fields.pop('name')
        self.fields.pop('email')
        self.fields.pop('url')

    def get_comment_create_data(self):
        "so remove it from comment create date"
        return dict(
            parent_id    = self.cleaned_data['parent'],
            title        = self.cleaned_data['title'],
            content_type = ContentType.objects.get_for_model(self.target_object),
            object_pk    = force_unicode(self.target_object._get_pk_val()),
            comment      = self.cleaned_data["comment"],
            submit_date  = datetime.datetime.now(),
            site_id      = settings.SITE_ID,
            is_public    = True,
            is_removed   = False,
        )

