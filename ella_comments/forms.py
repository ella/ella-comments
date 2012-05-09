import datetime

from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_unicode
from django.conf import settings

from threadedcomments.forms import ThreadedCommentForm


class AuthorizedCommentForm(ThreadedCommentForm):
    user = None

    def __init__(self, *args, **kwargs):
        "there is no such thing as user_name, user_email, user_url"
        super(AuthorizedCommentForm, self).__init__(*args, **kwargs)
        self.fields.pop('name')
        self.fields.pop('email')
        self.fields.pop('url')

    def check_for_duplicate_comment(self, new):
        """
        copy paste of check_for_duplicate_comment from ``django.contrib.comments.forms``
        so we can let the decision of which db to use on router
        """
        possible_duplicates = self.get_comment_model()._default_manager.filter(
            content_type = new.content_type,
            object_pk = new.object_pk,
            user_name = new.user_name,
            user_email = new.user_email,
            user_url = new.user_url,
        )
        for old in possible_duplicates:
            if old.submit_date.date() == new.submit_date.date() and old.comment == new.comment:
                return old

        return new

    def get_comment_create_data(self):
        "so remove it from comment create date"
        return dict(
            parent_id    = self.cleaned_data['parent'],
            title        = self.cleaned_data['title'],
            content_type = ContentType.objects.get_for_model(self.target_object),
            object_pk    = force_unicode(self.target_object._get_pk_val()),
            user_name    = self.user.get_full_name() or self.user.username,
            user_email   = self.user.email,
            comment      = self.cleaned_data["comment"],
            submit_date  = datetime.datetime.now(),
            site_id      = settings.SITE_ID,
            is_public    = True,
            is_removed   = False,
        )

