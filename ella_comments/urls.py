from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _
from django.conf.urls.defaults import patterns, url

from ella.core.custom_urls import resolver
from ella_comments.views import list_comments, post_comment, update_comment, comment_detail

urlpatterns = patterns('',
    url(r'^$', list_comments, name='comments-list'),
    url(r'^(?P<comment_id>\d+)/$', comment_detail, name='comment-detail'),
    url(r'^%s/(?P<comment_id>\d+)/$' % slugify(_('update')), update_comment, name='comments-update'),
    url(r'^%s/$' % slugify(_('new')), post_comment, name='comments-new'),
    url(r'^%s/(?P<parent_id>\d+)/$' % slugify(_('new')), post_comment, name='comments-reply'),
)

resolver.register(urlpatterns, prefix=slugify(_('comments')))

