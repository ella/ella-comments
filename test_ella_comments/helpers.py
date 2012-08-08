from django.contrib.sites.models import Site
from django.contrib.comments.signals import comment_was_posted

from threadedcomments.models import ThreadedComment


def create_comment(obj, ct, **kwargs):
    defaults = {
        'comment': '',
        'content_type': ct,
        'object_pk': obj.pk,
        'site': Site.objects.get_current(),
    }
    defaults.update(kwargs)
    c = ThreadedComment.objects.create(**defaults)
    comment_was_posted.send(c.__class__, comment=c, request=None)
    return c
