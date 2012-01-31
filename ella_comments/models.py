from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from ella.core.cache import CachedGenericForeignKey, get_cached_object

class DefaultCommentOptions(object):
    blocked = False
    premoderated = False
    check_profanities = True


class CommentOptionsManager(models.Manager):
    def get_for_object(self, obj):
        ct = ContentType.objects.get_for_model(obj)
        try:
            return get_cached_object(CommentOptionsObject, target_ct=ct,
                target_id=obj.pk)
        except CommentOptionsObject.DoesNotExist:
            return DefaultCommentOptions()


class CommentOptionsObject(models.Model):
    """contains comment options string for object"""
    objects = CommentOptionsManager()

    target_ct = models.ForeignKey(ContentType, verbose_name=_('Target content type'))
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

class BannedIP(models.Model):
    """
    """
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    ip_address = models.IPAddressField(_('IP Address'), unique=True)
    reason = models.CharField(_('Reason'), max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _('Banned IP')
        verbose_name_plural = _('Banned IPs')

    def __unicode__(self):
        return self.ip_address
