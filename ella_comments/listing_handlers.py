import logging
import time

from django.db.models.loading import get_model

from ella.core.cache.redis import RedisListingHandler, client
from ella.core.models import Publishable

log = logging.getLogger('ella_comments')

COMCOUNT_KEY = 'comcount:pub:%d:%s'
LASTCOM_KEY = 'lastcom:pub:%d:%s'

class MostCommentedListingHandler(RedisListingHandler):
    PREFIX = 'comcount'
    def _get_score_limits(self):
        max_score = None
        min_score = None

        if self.date_range:
            # TODO: maybe zinterstore with RedisListingHandler's zset using MIN aggregation
            raise NotSupported()
        return min_score, max_score

    def _get_listing(self, publishable, score):
        Listing = get_model('core', 'listing')
        return Listing(publishable=publishable, publish_from=publishable.publish_from)

class LastCommentedListingHandler(RedisListingHandler):
    PREFIX = 'lastcom'

def publishable_unpublished(publishable, **kwargs):
    pipe = client.pipeline()
    MostCommentedListingHandler.remove_publishable(publishable.category, publishable, pipe=pipe, commit=False)
    LastCommentedListingHandler.remove_publishable(publishable.category, publishable, pipe=pipe, commit=False)
    pipe.execute()

def publishable_published(publishable, **kwargs):
    cnt = client.get(COMCOUNT_KEY % (publishable.content_type_id, publishable.pk))
    lastcom = client.hgetall(LASTCOM_KEY % (publishable.content_type_id, publishable.pk))

    pipe = client.pipeline()

    MostCommentedListingHandler.add_publishable(publishable.category, publishable, cnt, pipe=pipe, commit=False)
    if lastcom:
        LastCommentedListingHandler.add_publishable(publishable.category, publishable, lastcom['submit_date'], pipe=pipe, commit=False)

    pipe.execute()

def comment_posted(comment, **kwargs):
    count_key = COMCOUNT_KEY % (comment.content_type_id, comment.object_pk)
    last_keu = LASTCOM_KEY % (comment.content_type_id, comment.object_pk)

    pipe = client.pipeline()
    pipe.incr(count_key)
    pipe.hmset(last_keu, {
        'submit_date': repr(time.mktime(comment.submit_date.timetuple())),
        'user_id': comment.user_id or '',
        'username': comment.user_name,
    })
    pipe.execute()

    obj = comment.content_object
    if isinstance(obj, Publishable):
        publishable_published(obj, last_comment=comment)

def connect_signals():
    from django.contrib.comments.signals import comment_was_posted
    from ella.core.signals import content_published, content_unpublished
    content_published.connect(publishable_published)
    content_unpublished.connect(publishable_unpublished)

    comment_was_posted.connect(comment_posted)

if client:
    connect_signals()

