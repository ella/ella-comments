import operator

from django.db import models
from django.db.models.signals import pre_save, post_save, post_delete
from django.contrib import comments
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.cache import cache

from ella.core.cache import CachedGenericForeignKey, get_cached_object, ContentTypeForeignKey
from ella.core.cache.redis import client

from threadedcomments.models import PATH_DIGITS

from ella_comments.listing_handlers import COMCOUNT_KEY
from ella_comments.signals import comment_removed

DEFAULT_COMMENT_OPTIONS = {
    'blocked': False,
    'premoderated': False,
    'check_profanities': True
}

COMMENT_LIST_KEY = 'comments:list:%s:%s:%d'

class CachedCommentList(object):
    CACHE_TIMEOUT = 30
    def __init__(self, ctype, object_pk, reverse=None, group_threads=None, flat=None, ids=()):
        self.ctype = ctype
        self.object_pk = object_pk
        self.reverse = reverse if reverse is not None else getattr(settings, 'COMMENTS_REVERSED', False)
        self.group_threads = group_threads if group_threads is not None else getattr(settings, 'COMMENTS_GROUP_THREADS', False)
        self.flat = flat if flat is not None else getattr(settings, 'COMMENTS_FLAT', False)
        self.ids = ids

    def _count_cache_key(self):
        return 'comments:count:%s:%s:%s' % (self.ctype.pk, self.object_pk, ','.join(map(str, sorted(self.ids))))

    def _cache_key(self, start=None, stop=None):
        return 'comments:list:%s:%s:%d:%d:%d:%s:%s:%s' % (
            self.ctype.pk, self.object_pk,
            1 if self.reverse else 0,
            1 if self.group_threads else 0,
            1 if self.flat else 0,
            ','.join(map(str, sorted(self.ids))),
            start or '', stop or ''
        )

    def get_query_set(self):
        # basic queryset
        qs = comments.get_model().objects.filter(content_type=self.ctype, object_pk=self.object_pk, site__pk=settings.SITE_ID, is_public=True)
        if getattr(settings, 'COMMENTS_HIDE_REMOVED', False):
            qs = qs.filter(is_removed=False)

        # only individual branches requested
        if self.ids:
            # branch is everything whose tree_path begins with the same prefix
            qs = qs.filter(reduce(
                        operator.or_,
                        map(lambda x: models.Q(tree_path__startswith=x.zfill(PATH_DIGITS)), self.ids)
                ))

        if self.flat:
            order = '-submit_date' if not self.reverse else 'submit_date'
        else:
            order = 'tree_path' if not self.reverse else '-tree_path'
        qs = qs.order_by(order)

        return qs

    def __len__(self):
        if client and not self.ids:
            return int(client.get(COMCOUNT_KEY % (self.ctype.pk, self.object_pk)) or 0)
        cnt = cache.get(self._count_cache_key())
        if cnt is None:
            cnt = self.get_query_set().count()
            cache.set(self._count_cache_key(), cnt, self.CACHE_TIMEOUT)
        return int(cnt)
    count = __len__

    def get_list(self, start=None, stop=None):
        cache_key = self._cache_key(start, stop)
        items = cache.get(cache_key)
        if items is None:
            qs = self.get_query_set()
            if start is not None:
                qs = qs[start:stop]
            items = list(qs)
            cache.set(cache_key, items, self.CACHE_TIMEOUT)
        return items

    def __getitem__(self, key):
        assert isinstance(key, slice), 'CachedCommentList only supports slicing'
        assert not key.step, 'CachedCommentList doesn\'t support step'
        start, stop = key.start or 0, key.stop or 0
        assert stop >= start, 'CachedCommentList only supports positive slices'

        return self.get_list(start, stop)


def group_threads(items, prop=lambda x: x.tree_path[:PATH_DIGITS]):
    groups = []
    prev = None
    for i in items:
        if prop(i) != prev:
            prev = prop(i)
            groups.append([])
        groups[-1].append(i)
    return groups


class CommentOptionsManager(models.Manager):
    def set_for_object(self, obj, **kwargs):
        if not kwargs:
            return

        if hasattr(obj, 'app_data'):
            obj.app_data.setdefault('comments', {}).update(kwargs)
            obj.save(force_update=True)

        else:
            coo, created = self.get_or_create(target_ct=ContentType.objects.get_for_model(obj), target_id=obj.pk, defaults=kwargs)
            if not created:
                for k, v in kwargs:
                    setattr(coo, k, v)
                coo.save(force_update=True)


    def get_for_object(self, obj):
        if hasattr(obj, 'app_data'):
            return obj.app_data.get('comments', DEFAULT_COMMENT_OPTIONS)

        ct = ContentType.objects.get_for_model(obj)
        try:
            coo = get_cached_object(CommentOptionsObject, target_ct=ct, target_id=obj.pk)
            return {
                'blocked': coo.blocked,
                'premoderated': coo.premoderated,
                'check_profanities': coo.check_profanities,
            }
        except CommentOptionsObject.DoesNotExist:
            return DEFAULT_COMMENT_OPTIONS


class CommentOptionsObject(models.Model):
    """contains comment options string for object"""
    objects = CommentOptionsManager()

    target_ct = ContentTypeForeignKey(verbose_name=_('Target content type'))
    target_id = models.TextField(_('Target id'))
    target = CachedGenericForeignKey(ct_field="target_ct", fk_field="target_id")

    blocked = models.BooleanField(_('Disable comments'), default=False)
    premoderated = models.BooleanField(_('Show comments only after approval'),
        default=False)
    check_profanities = models.BooleanField(_('Check profanities in comments'),
        default=False, editable=False)

    class Meta:
        unique_together = (('target_ct', 'target_id',),)
        verbose_name = _('Comment Options')
        verbose_name_plural = _('Comment Options')

    def __unicode__(self):
        return u"%s: %s" % (_("Comment Options"), self.target)

# signal handlers for sending comment_removed signals
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
        # if this is a newly removed comment, send the comment_removed signal
        if not instance.__pub_info['is_removed'] and instance.is_removed:
            comment_removed.send(sender=instance.__class__, comment=instance)

def comment_post_delete(instance, **kwargs):
    comment_removed.send(sender=instance.__class__, comment=instance)

pre_save.connect(comment_pre_save, sender=comments.get_model())
post_save.connect(comment_post_save, sender=comments.get_model())
post_delete.connect(comment_post_delete, sender=comments.get_model())
