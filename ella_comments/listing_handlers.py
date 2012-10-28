import logging

from django.contrib import comments

from ella.core.cache.redis import RedisListingHandler, client, SlidingListingHandler, TimeBasedListingHandler
from ella.core.models import Publishable, Listing
from ella.utils.timezone import to_timestamp

log = logging.getLogger('ella_comments')

MOST_COMMENTED_LH = 'most_commented'
RECENTLY_COMMENTED_LH = 'recently_commented'
LAST_COMMENTED_LH = 'last_commented'


COMCOUNT_KEY = 'comcount:pub:%s:%s'
LASTCOM_KEY = 'lastcom:pub:%s:%s'

class RecentMostCommentedListingHandler(SlidingListingHandler):
    PREFIX = 'slidingccount'

class MostCommentedListingHandler(RedisListingHandler):
    PREFIX = 'comcount'

class LastCommentedListingHandler(TimeBasedListingHandler):
    PREFIX = 'lastcom'

def comment_post_save(instance, **kwargs):
    if hasattr(instance, '__pub_info'):
        is_public = instance.is_public and not instance.is_removed
        was_public = instance.__pub_info['is_public'] and not instance.__pub_info['is_removed']

        # Base queryset for public comments
        public_comments = comments.get_model()._default_manager.filter(
            content_type=instance.content_type_id,
            object_pk=instance.object_pk,
            is_public=True,
            is_removed=False
        )

        # If the comment's "publicity" was modified in any way, update the count key
        if (was_public and not is_public) or (not was_public and is_public):
            client.set(
                COMCOUNT_KEY % (instance.content_type_id, instance.object_pk),
                public_comments.count()
            )
        # If no change to the "publicity" of the comment was made, return
        else:
            return

        # Update the last comment info
        last_keu = LASTCOM_KEY % (instance.content_type_id, instance.object_pk)
        try:
            last_com = public_comments.latest('submit_date')
            client.hmset(last_keu, {
                'submit_date': repr(to_timestamp(last_com.submit_date)),
                'user_id': last_com.user_id or '',
                'username': last_com.user_name,
                'comment': last_com.comment,
                'url': last_com.url,
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
        'submit_date': repr(to_timestamp(comment.submit_date)),
        'user_id': comment.user_id or '',
        'username': comment.user_name,
        'comment': comment.comment,
        'url': comment.url,
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
    from django.db.models.signals import post_save
    content_published.connect(publishable_published)
    content_unpublished.connect(publishable_unpublished)

    comment_was_posted.connect(comment_posted)

    post_save.connect(comment_post_save, sender=comments.get_model())

if client:
    connect_signals()

