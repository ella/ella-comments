import logging
import time

from django.contrib import comments

from ella.core.cache.redis import RedisListingHandler, client, SlidingListingHandler
from ella.core.models import Publishable, Listing

log = logging.getLogger('ella_comments')

MOST_COMMENTED_LH = 'most_commented'
RECENTLY_COMMENTED_LH = 'recently_commented'
LAST_COMMENTED_LH = 'last_commented'


COMCOUNT_KEY = 'comcount:pub:%d:%s'
LASTCOM_KEY = 'lastcom:pub:%d:%s'

class CommentListingHandler(object):
    def _get_score_limits(self):
        max_score = None
        min_score = None

        if self.date_range:
            # TODO: maybe zinterstore with RedisListingHandler's zset using MIN aggregation
            raise NotSupported()
        return min_score, max_score

    def _get_listing(self, publishable, score):
        return Listing(publishable=publishable, publish_from=publishable.publish_from)

class RecentMostCommentedListingHandler(CommentListingHandler, SlidingListingHandler):
    PREFIX = 'slidingccount'

class MostCommentedListingHandler(CommentListingHandler, RedisListingHandler):
    PREFIX = 'comcount'

class LastCommentedListingHandler(CommentListingHandler, RedisListingHandler):
    PREFIX = 'lastcom'

def comment_pre_save(instance, **kwargs):
    if instance.pk:
        try:
            old_instance = instance.__class__._default_manager.get(pk=instance.pk)
        except instance.__class__.DoesNotExist:
            return
        instance.__pub_info = {
            'is_public': old_instance.is_public,
            'is_removed': old_instance.is_removed,
        }

def comment_post_save(instance, **kwargs):
    if hasattr(instance, '__pub_info'):
        is_public = instance.is_public and not instance.is_removed
        was_public = instance.__pub_info['is_public'] and not instance.__pub_info['is_removed']

        # comment being moderated
        if was_public and not is_public:
            count_key = COMCOUNT_KEY % (instance.content_type_id, instance.object_pk)
            client.decr(count_key)

        # commet back up
        elif not was_public and is_public:
            count_key = COMCOUNT_KEY % (instance.content_type_id, instance.object_pk)
            client.incr(count_key)
        else:
            # no change
            return

        last_keu = LASTCOM_KEY % (instance.content_type_id, instance.object_pk)
        try:
            # update the last comment info
            last_com = comments.get_model()._default_manager.filter(content_type_id=instance.content_type_id, object_pk=instance.object_pk, is_public=True, is_removed=False).latest('submit_date')
            client.hmset(last_keu, {
                'submit_date': repr(time.mktime(last_com.submit_date.timetuple())),
                'user_id': last_com.user_id or '',
                'username': last_com.user.username if last_com.user_id else last_com.user_name,
            })
        except comments.get_model().DoesNotExist:
            client.delete(last_keu)

        # update the listing handlers
        obj = instance.content_object
        if isinstance(obj, Publishable) and obj.is_published():
            publishable_published(obj)


def publishable_unpublished(publishable, **kwargs):
    pipe = client.pipeline()
    for k in (MOST_COMMENTED_LH, LAST_COMMENTED_LH, RECENTLY_COMMENTED_LH):
        ListingHandler = Listing.objects.get_listing_handler(k, fallback=False)
        if ListingHandler is None:
            continue
        ListingHandler.remove_publishable(publishable.category, publishable, pipe=pipe, commit=False)
    pipe.execute()

def publishable_published(publishable, **kwargs):
    cnt = client.get(COMCOUNT_KEY % (publishable.content_type_id, publishable.pk))
    lastcom = client.hgetall(LASTCOM_KEY % (publishable.content_type_id, publishable.pk))

    pipe = client.pipeline()

    if cnt is None:
        cnt = 0

    if Listing.objects.get_listing_handler(MOST_COMMENTED_LH, fallback=False):
        Listing.objects.get_listing_handler(MOST_COMMENTED_LH).add_publishable(publishable.category, publishable, cnt, pipe=pipe, commit=False)

    if lastcom and Listing.objects.get_listing_handler(LAST_COMMENTED_LH, fallback=False):
        Listing.objects.get_listing_handler(LAST_COMMENTED_LH).add_publishable(publishable.category, publishable, lastcom['submit_date'], pipe=pipe, commit=False)

    pipe.execute()

def comment_posted(comment, **kwargs):
    count_key = COMCOUNT_KEY % (comment.content_type_id, comment.object_pk)
    last_keu = LASTCOM_KEY % (comment.content_type_id, comment.object_pk)

    pipe = client.pipeline()
    pipe.incr(count_key)
    pipe.hmset(last_keu, {
        'submit_date': repr(time.mktime(comment.submit_date.timetuple())),
        'user_id': comment.user_id or '',
        'username': comment.user.username if comment.user_id else comment.user_name,
    })

    obj = comment.content_object
    if not isinstance(obj, Publishable) or not obj.is_published():
        pipe.execute()
    elif Listing.objects.get_listing_handler(RECENTLY_COMMENTED_LH, fallback=False):
        Listing.objects.get_listing_handler(RECENTLY_COMMENTED_LH).incr_score(obj.category, obj, pipe=pipe, commit=False)
        pipe.execute()
        publishable_published(obj)

def connect_signals():
    from django.contrib.comments.signals import comment_was_posted
    from ella.core.signals import content_published, content_unpublished
    from django.db.models.signals import pre_save, post_save
    content_published.connect(publishable_published)
    content_unpublished.connect(publishable_unpublished)

    comment_was_posted.connect(comment_posted)

    pre_save.connect(comment_pre_save, sender=comments.get_model())
    post_save.connect(comment_post_save, sender=comments.get_model())

if client:
    connect_signals()

