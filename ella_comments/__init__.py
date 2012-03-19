"""
Change the attributes you want to customize
"""

from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured

from threadedcomments.models import ThreadedComment
from threadedcomments.forms import ThreadedCommentForm

from ella_comments.forms import AuthorizedCommentForm

def get_model():
    return ThreadedComment

def get_form():
    custom_comment_form = getattr(settings, 'COMMENTS_CUSTOM_FORM', None)
    if custom_comment_form:
        try:
            module_name, klass_name = custom_comment_form.rsplit('.', 1)
            module = import_module(module_name)
        except ImportError, e:
            raise ImproperlyConfigured('Error importing custom comment form %s: "%s"' % (klass_name, e))
        try:
            CustomCommentForm = getattr(module, klass_name)
        except AttributeError:
            raise ImproperlyConfigured('Module "%s" does not define a comment form name "%s"' % (module, klass_name))
        else:
            return CustomCommentForm
    if getattr(settings, 'COMMENTS_AUTHORIZED_ONLY', False):
        return AuthorizedCommentForm
    return ThreadedCommentForm

# register signals if appropriate
from ella_comments import listing_handlers
