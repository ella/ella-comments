from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from ella.core.cache import CachedGenericForeignKey, get_cached_object, ContentTypeForeignKey

DEFAULT_COMMENT_OPTIONS = {
    'blocked': False,
    'premoderated': False,
    'check_profanities': True
}


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
            coo= get_cached_object(CommentOptionsObject, target_ct=ct,
                target_id=obj.pk)
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
    target_id = models.PositiveIntegerField(_('Target id'))
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

