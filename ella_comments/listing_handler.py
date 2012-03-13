import logging
import time

from django.conf import settings
from django.db.models.loading import get_model
from django.contrib import comments

from ella.core.cache.redis import RedisListingHandler
from ella.core.models import Publishable

log = logging.getLogger('ella_comments')

client = None
if hasattr(settings, 'COMMENTS_REDIS'):
    try:
        from redis import Redis
    except:
        log.error('Redis support requested but Redis client not installed.')
        client = None
    else:
        client = Redis(**getattr(settings, 'COMMENTS_REDIS'))

class CommentListingHandler(RedisListingHandler):
    @classmethod
    def get_redis_values(cls, publishable):
        return (
            cls.CAT_LISTING % publishable.category_id,
            cls.CT_LISTING % publishable.content_type_id,
        ), '%d:%d' % (publishable.content_type_id, publishable.pk)

    def _get_listing(self, publishable, score, data):
        Listing = get_model('core', 'listing')
        return Listing(publishable=publishable, publish_from=publishable.publish_from)

COMCOUNT_KEY = 'comcount:%d:%s'
class MostCommentedListingHandler(CommentListingHandler):
    CAT_LISTING = 'comcount:cat:%d'
    CT_LISTING = 'comcount:ct:%d'

    def _get_score_limits(self):
        max_score = None
        min_score = None

        if self.date_range:
            # TODO: maybe zinterstore with RedisListingHandler's zset using MIN aggregation
            raise NotSupported()
        return min_score, max_score

class LastCommentedListingHandler(CommentListingHandler):
    CAT_LISTING = 'lastcom:cat:%d'
    CT_LISTING = 'lastcom:ct:%d'

def publishable_unpublished(publishable, **kwargs):
    pipe = client.pipeline()

    keys, val = LastCommentedListingHandler.get_redis_values(publishable)
    for k in keys:
        pipe.zrem(k, val)

    keys, val = MostCommentedListingHandler.get_redis_values(publishable)
    for k in keys:
        pipe.zrem(k, val)

    pipe.execute()

def publishable_published(publishable, **kwargs):
    cnt = client.get(COMCOUNT_KEY % (publishable.content_type_id, publishable.pk))
    pipe = client.pipeline()
    keys, val = MostCommentedListingHandler.get_redis_values(publishable)
    for k in keys:
        pipe.zadd(k, val, cnt)

    keys, val = LastCommentedListingHandler.get_redis_values(publishable)
    if 'last_comment' in kwargs:
        last_comment = kwargs['last_comment']
    else:
        last_comment = comments.get_model()._default_manager.get_for_object(publishable).latest('submit_date')

    score = repr(time.mktime(last_comment.publish_date.timetuple()))
    for k in keys:
        pipe.zadd(k, val, score)

    pipe.execute()

def comment_posted(comment, **kwargs):
    key = COMCOUNT_KEY % (comment.content_type_id, comment.object_pk)
    client.zinc(key, 1)

    if isinstance(comment.content_object, Publishable):
        publishable_published(comment.content_object, last_comment=comment)
