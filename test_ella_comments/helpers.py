from django.contrib.sites.models import Site
from django.contrib.comments.signals import comment_was_posted
from django.core.handlers.base import BaseHandler
from django.test import client

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

class RequestFactory(client.Client):
    " Helper class to create an empty request obj. "
    def request(self, **request):
        if 'wsgi.input' not in request:
            request['wsgi.input'] = client.FakePayload('')
        request = client.RequestFactory.request(self, **request)

        # run request middleware to setup a session, user, etc.
        handler = BaseHandler()
        handler.load_middleware()
        for middleware_method in handler._request_middleware:
            if middleware_method(request):
                raise Exception("Couldn't create request mock object - "
                                "request middleware returned a response")
        return request
