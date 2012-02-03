"""
Change the attributes you want to customize
"""

from django.conf import settings

from threadedcomments.models import ThreadedComment
from threadedcomments.forms import ThreadedCommentForm

from ella_comments.forms import AuthorizedCommentForm

def get_model():
    return ThreadedComment

def get_form():
    if getattr(settings, 'COMMENTS_AUTHORIZED_ONLY', False):
        return AuthorizedCommentForm
    return ThreadedCommentForm

