# -*- coding: utf-8 -*-
from django.test import TestCase

from nose import tools

from django.contrib import comments
from django.utils.translation import ugettext as _
from django.template.defaultfilters import slugify
from django.contrib.auth.models import User
from django.conf import settings

from ella.utils.test_helpers import create_basic_categories, create_and_place_a_publishable

# register must be imported for custom urls
from ella_comments import register
from ella_comments.models import CommentOptionsObject
from ella_comments import views, models

from test_ella_comments.helpers import create_comment
from test_ella_comments import template_loader

class CommentViewTestCase(TestCase):
    def setUp(self):
        super(CommentViewTestCase, self).setUp()
        create_basic_categories(self)
        create_and_place_a_publishable(self)

    def get_url(self, *bits):
        url = [self.publishable.get_absolute_url(), slugify(_('comments')), '/']
        if bits:
            url.append('/'.join(map(lambda x: slugify(_(str(x))), bits)))
            url.append('/')

        return ''.join(url)

    def get_form_data(self, form, **kwargs):
        out = {
            'name': 'Honza',
            'email': 'honza.kral@gmail.com',
            'url': '',
            'comment': 'I like this App',
        }
        out.update(kwargs)
        out['parent'] = form.parent and form.parent or ''
        out.update(form.generate_security_data())
        return out

    def tearDown(self):
        super(CommentViewTestCase, self).tearDown()
        template_loader.templates = {}

class TestCommentViewHelpers(TestCase):
    def test_group_threads(self):
        data = [
                u'a', u'a/i', u'a/i/j', u'a/k',
                u'b',
                u'c', u'c/d', u'c/d/f', u'c/d/g', u'c/e',
                u'h',
            ]
        expected = [
                [u'a', u'a/i', u'a/i/j', u'a/k'],
                [u'b'],
                [u'c', u'c/d', u'c/d/f', u'c/d/g', u'c/e'],
                [u'h'],
            ]
        tools.assert_equals(expected, models.group_threads(data, lambda x: x[:1]))

class TestCommentViewPagination(CommentViewTestCase):
    def setUp(self):
        super(TestCommentViewPagination, self).setUp()
        settings.COMMENTS_PAGINATE_BY = 3

    def tearDown(self):
        super(TestCommentViewPagination, self).tearDown()
        del settings._wrapped.COMMENTS_PAGINATE_BY

    def test_get_list_raises_404_on_incorrect_page_param(self):
        template_loader.templates['404.html'] = ''
        response = self.client.get(self.get_url(), {'p': 2})
        tools.assert_equals(404, response.status_code)

    def test_get_list_returns_second_page_if_asked_to(self):
        template_loader.templates['page/comment_list.html'] = ''
        a = create_comment(self.publishable, self.publishable.content_type)
        d = create_comment(self.publishable, self.publishable.content_type)
        ab = create_comment(self.publishable, self.publishable.content_type, parent_id=a.pk)
        de = create_comment(self.publishable, self.publishable.content_type, parent_id=d.pk)
        def_ = create_comment(self.publishable, self.publishable.content_type, parent_id=de.pk)
        ac = create_comment(self.publishable, self.publishable.content_type, parent_id=a.pk)
        response = self.client.get(self.get_url(), {'p': 2})
        tools.assert_equals(200, response.status_code)
        tools.assert_equals([d, de, def_], list(response.context['comment_list']))

    def test_get_list_returns_first_page_with_no_params(self):
        template_loader.templates['page/comment_list.html'] = ''
        a = create_comment(self.publishable, self.publishable.content_type)
        d = create_comment(self.publishable, self.publishable.content_type)
        ab = create_comment(self.publishable, self.publishable.content_type, parent_id=a.pk)
        de = create_comment(self.publishable, self.publishable.content_type, parent_id=d.pk)
        def_ = create_comment(self.publishable, self.publishable.content_type, parent_id=de.pk)
        ac = create_comment(self.publishable, self.publishable.content_type, parent_id=a.pk)
        response = self.client.get(self.get_url())
        tools.assert_equals(200, response.status_code)
        tools.assert_equals([a, ab, ac], list(response.context['comment_list']))

class TestCommentModeration(CommentViewTestCase):
    def setUp(self):
        super(TestCommentModeration, self).setUp()
        CommentOptionsObject.objects.set_for_object(self.publishable, premoderated=True)
        self.form = comments.get_form()(target_object=self.publishable)

    def test_premoderated_comments_are_not_public(self):
        response = self.client.post(self.get_url('new'), self.get_form_data(self.form))
        tools.assert_equals(302, response.status_code)
        tools.assert_equals(1, comments.get_model().objects.count())
        comment = comments.get_model().objects.all()[0]
        tools.assert_equals(False, comment.is_public)

    def test_premoderated_comments_are_not_visible_in_listing(self):
        template_loader.templates['page/comment_list.html'] = ''
        response = self.client.post(self.get_url('new'), self.get_form_data(self.form))
        tools.assert_equals(302, response.status_code)
        response = self.client.get(self.get_url())
        tools.assert_true('comment_list' in response.context)
        tools.assert_equals(0, len(response.context['comment_list']))

class TestCommentViews(CommentViewTestCase):

    def test_comments_urls_is_blocked(self):
        template_loader.templates['404.html'] = ''
        CommentOptionsObject.objects.set_for_object(self.publishable, blocked=True)
        response = self.client.post(self.get_url('new'))
        tools.assert_equals(404, response.status_code)

    def test_post_works_for_correct_data(self):
        form = comments.get_form()(target_object=self.publishable)
        response = self.client.post(self.get_url('new'), self.get_form_data(form))
        tools.assert_equals(302, response.status_code)
        tools.assert_equals(1, comments.get_model().objects.count())

    def test_post_works_for_correct_data_with_parent(self):
        c = create_comment(self.publishable, self.publishable.content_type)
        form = comments.get_form()(target_object=self.publishable, parent=c.pk)
        response = self.client.post(self.get_url('new'), self.get_form_data(form))
        tools.assert_equals(302, response.status_code)
        tools.assert_equals(2, comments.get_model().objects.count())
        child = comments.get_model().objects.exclude(pk=c.pk)[0]
        tools.assert_equals(c, child.parent)

    def post_comment_as_logged_in_user(self):
        c = create_comment(self.publishable, self.publishable.content_type)
        boy = User.objects.create(username='boy', email='boy@whiskey.com')
        boy.set_password('boy')
        boy.save()
        self.client.login(username='boy', password='boy')
        form = comments.get_form()(target_object=self.publishable, parent=c.pk)
        data = { 'name': '', 'email': '', }
        response = self.client.post(self.get_url('new'), self.get_form_data(form, **data))
        tools.assert_equals(302, response.status_code)
        tools.assert_equals(2, comments.get_model().objects.count())
        child = comments.get_model().objects.exclude(pk=c.pk)[0]
        tools.assert_equals(u'boy', child.user_name)
        tools.assert_equals(u'boy@whiskey.com', child.user_email)

    def test_post_works_for_logged_in_user(self):
        self.post_comment_as_logged_in_user()

    def test_post_works_for_logged_in_user_with_logged_only_form(self):
        settings.COMMENTS_AUTHORIZED_ONLY = True
        self.post_comment_as_logged_in_user()
        settings.COMMENTS_AUTHORIZED_ONLY = False

    def test_post_renders_comment_form_on_get(self):
        template_loader.templates['page/comment_form.html'] = ''
        response = self.client.get(self.get_url('new'))
        tools.assert_equals(200, response.status_code)
        tools.assert_true('form' in response.context)
        form = response.context['form']
        tools.assert_equals(self.publishable, form.target_object)

    def test_post_passes_parent_on_get_to_template_if_specified(self):
        template_loader.templates['page/comment_form.html'] = ''
        c = create_comment(self.publishable, self.publishable.content_type)
        response = self.client.get(self.get_url('new', c.pk))
        tools.assert_equals(200, response.status_code)
        tools.assert_true('parent' in response.context)
        tools.assert_equals(c, response.context['parent'])
        form = response.context['form']
        tools.assert_equals(str(c.pk), form.parent)

    def test_post_raises_404_for_non_existent_parent(self):
        template_loader.templates['404.html'] = ''
        response = self.client.get(self.get_url('new', 12345))
        tools.assert_equals(404, response.status_code)

    def test_post_returns_bad_request_with_POST_and_no_data(self):
        template_loader.templates['comments/400-debug.html'] = ''
        template_loader.templates['page/comment_form.html'] = ''
        response = self.client.post(self.get_url('new'))
        tools.assert_equals(400, response.status_code)

    def test_get_list_renders_correct_comments(self):
        template_loader.templates['page/comment_list.html'] = ''
        c = create_comment(self.publishable, self.publishable.content_type)
        c2 = create_comment(self.publishable, self.publishable.content_type)
        response = self.client.get(self.get_url())
        tools.assert_equals(200, response.status_code)
        tools.assert_equals([c, c2], list(response.context['comment_list']))

    def test_get_list_renders_correct_comments_including_tree_order(self):
        template_loader.templates['page/comment_list.html'] = ''
        a = create_comment(self.publishable, self.publishable.content_type)
        d = create_comment(self.publishable, self.publishable.content_type)
        ab = create_comment(self.publishable, self.publishable.content_type, parent_id=a.pk)
        de = create_comment(self.publishable, self.publishable.content_type, parent_id=d.pk)
        def_ = create_comment(self.publishable, self.publishable.content_type, parent_id=de.pk)
        ac = create_comment(self.publishable, self.publishable.content_type, parent_id=a.pk)
        response = self.client.get(self.get_url())
        tools.assert_equals(200, response.status_code)
        tools.assert_equals([a, ab, ac, d, de, def_], list(response.context['comment_list']))

    def test_get_list_renders_only_given_branch_if_asked_to(self):
        template_loader.templates['page/comment_list.html'] = ''
        a = create_comment(self.publishable, self.publishable.content_type)
        d = create_comment(self.publishable, self.publishable.content_type)
        ab = create_comment(self.publishable, self.publishable.content_type, parent_id=a.pk)
        de = create_comment(self.publishable, self.publishable.content_type, parent_id=d.pk)
        def_ = create_comment(self.publishable, self.publishable.content_type, parent_id=de.pk)
        ac = create_comment(self.publishable, self.publishable.content_type, parent_id=a.pk)
        response = self.client.get(self.get_url(), {'ids': a.pk})
        tools.assert_equals(200, response.status_code)
        tools.assert_equals([a, ab, ac], list(response.context['comment_list']))

    def test_get_list_renders_only_given_branches_if_asked_to(self):
        template_loader.templates['page/comment_list.html'] = ''
        a = create_comment(self.publishable, self.publishable.content_type)
        d = create_comment(self.publishable, self.publishable.content_type)
        ab = create_comment(self.publishable, self.publishable.content_type, parent_id=a.pk)
        de = create_comment(self.publishable, self.publishable.content_type, parent_id=d.pk)
        def_ = create_comment(self.publishable, self.publishable.content_type, parent_id=de.pk)
        ac = create_comment(self.publishable, self.publishable.content_type, parent_id=a.pk)
        response = self.client.get(self.get_url() + '?ids=%s&ids=%s' % (a.pk, d.pk))
        tools.assert_equals(200, response.status_code)
        tools.assert_equals([a, ab, ac, d, de, def_], list(response.context['comment_list']))

class TestUpdateComment(CommentViewTestCase):
    def test_get_comment_for_user(self):
        boy = User.objects.create(username='boy')
        girl = User.objects.create(username='girl')
        first = create_comment(self.publishable, self.publishable.content_type, comment='first', user=boy)
        second = create_comment(self.publishable, self.publishable.content_type, comment='second', user=girl)
        tools.assert_equals(first, views.update_comment.get_comment_for_user(self.publishable, boy, first.pk))
        tools.assert_raises(comments.get_model().DoesNotExist, lambda: views.update_comment.get_comment_for_user(self.publishable, boy, 1024))
        tools.assert_raises(comments.get_model().DoesNotExist, lambda: views.update_comment.get_comment_for_user(self.publishable, boy, second.pk))

    def test_get_update_comment_form(self):
        comment = create_comment(self.publishable, self.publishable.content_type, comment='some comment')
        form = views.update_comment.get_update_comment_form(self.publishable, comment, None, None)
        tools.assert_equals('some comment', form.initial['comment'])

