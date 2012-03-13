import logging

from django.conf import settings
from django.db.models.loading import get_model

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

COMCOUNT_KEY = 'comcount:%d:%s'

class MostCommentedListingHandler(RedisListingHandler):
    CAT_LISTING = 'comcount:cat:%d'
    CT_LISTING = 'comcount:ct:%d'

    def _get_listing(self, publishable, score, data):
        Listing = get_model('core', 'listing')
        return Listing(publishable=publishable, publish_from=publishable.publish_from)

    def _get_score_limits(self):
        max_score = None
        min_score = None

        if self.date_range:
            # TODO: maybe zinterstore with RedisListingHandler's zset using MIN aggregation
            raise NotSupported()
        return min_score, max_score

def get_redis_values(publishable):
    return (
        MostCommentedListingHandler.CAT_LISTING % publishable.category_id,
        MostCommentedListingHandler.CT_LISTING % publishable.content_type_id,
    ), '%d:%d' % (publishable.content_type_id, publishable.pk)

def publishable_published(publishable, **kwargs):
    keys, val = get_redis_values(publishable)

    for k in keys:
        client.zrem(k, val)

def publishable_unpublished(publishable, **kwargs):
    keys, val = get_redis_values(publishable)

    cnt = client.get(COMCOUNT_KEY % (publishable.content_type_id, publishable.pk))
    for k in keys:
        client.zadd(k, val, cnt)

def comment_posted(comment, **kwargs):
    key = COMCOUNT_KEY % (comment.content_type_id, comment.object_pk)
    client.zinc(key, 1)

    if isinstance(comment.content_object, Publishable):
        publishable_published(comment.content_object)
