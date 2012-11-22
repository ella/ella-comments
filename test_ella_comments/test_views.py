# -*- coding: utf-8 -*-
import time
import mock

from urlparse import urlparse

from django.conf import settings
from django.contrib import comments
from django.contrib.auth.models import User
from django.core.cache import cache
from django.template.defaultfilters import slugify
from django.test import TestCase
from django.utils.translation import ugettext as _

from nose import tools

from ella.core.cache.redis import client
from ella.core.cache import utils
from ella.utils.test_helpers import create_basic_categories, create_and_place_a_publishable

# register must be imported for custom urls
from ella_comments import register
from ella_comments.models import CommentOptionsObject
from ella_comments import views, models

from test_ella_comments.helpers import create_comment
from test_ella_comments import template_loader
from test_ella_comments.models import ReverseCommentOrderingPublishable, ResultsPerPagePublishable, \
    OVERRIDDEN_RESULTS_PER_PAGE


class CommentViewTestCase(TestCase):
    def setUp(self):
        super(CommentViewTestCase, self).setUp()
        create_basic_categories(self)
        create_and_place_a_publishable(self)
        utils.PUBLISHABLE_CT = None

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
        " Flush cache and redis for each unit test. "
        super(CommentViewTestCase, self).tearDown()
        template_loader.templates = {}
        cache.clear()
        client.flushdb()

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
    def setUp(self):
        super(TestUpdateComment, self).setUp()
        template_loader.templates['404.html'] = ''
        template_loader.templates['page/comment_update.html'] = ''

        # Create a few users for the tests
        self.user_foo = User.objects.create_user('foo', 'foo@example.com', 'test')
        self.user_bar = User.objects.create_user('bar', 'bar@example.com', 'test')

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

    def test_non_moderator_allowed_edits(self):
        """
        Assert that 404 is raised if the `COMMENTS_ALLOW_MODERATOR_UPDATE` setting is
        False or does not exist and the user editing the comment is NOT the comment owner.
        """
        # Assert that moderator update flags are set as expected
        tools.assert_true(hasattr(settings, 'COMMENTS_ALLOW_UPDATE'))

        # Patch the COMMENTS_ALLOW_MODERATOR_UPDATE for the test
        settings.COMMENTS_ALLOW_MODERATOR_UPDATE = False

        # Create a new comment with user_foo
        comment = create_comment(self.publishable, self.publishable.content_type, comment='first', user=self.user_foo)

        # Try to edit this comment with user_bar and assert it raises 404 b/c COMMENTS_ALLOW_MODERATOR_UPDATE is set to False
        self.client.login(username='bar', password='test')
        response = self.client.get(self.get_url('update', comment.id))
        tools.assert_equals(404, response.status_code)

        # Reset the COMMENTS_ALLOW_MODERATOR_UPDATE value
        settings.COMMENTS_ALLOW_MODERATOR_UPDATE = True

    def test_user_doesnt_pass_test(self):
        """
        Assert that 404 is raised if the `COMMENTS_ALLOW_MODERATOR_UPDATE` setting is
        True but the user editing the comment is NOT the comment owner and does NOT pass
        the `user_can_access_comment` method.
        """
        # Assert that moderator update flags are set as expected
        tools.assert_true(hasattr(settings, 'COMMENTS_ALLOW_UPDATE'))
        tools.assert_true(hasattr(settings, 'COMMENTS_ALLOW_MODERATOR_UPDATE'))

        # Create a new comment with user_foo
        comment = create_comment(self.publishable, self.publishable.content_type, comment='first', user=self.user_foo)

        # Try to edit this comment with user_bar and assert it raises 404 b/c COMMENTS_ALLOW_MODERATOR_UPDATE is set to False
        self.client.login(username='bar', password='test')
        response = self.client.get(self.get_url('update', comment.id))
        tools.assert_equals(404, response.status_code)

    def test_user_passes_test(self):
        """
        Assert that the user CAN edit the comment if they are not the owner but
        they do have the appropriate permissions (and if the apporpriate settings are configured).
        """
        # Assert that moderator update flags are set as expected
        tools.assert_true(hasattr(settings, 'COMMENTS_ALLOW_UPDATE'))
        tools.assert_true(hasattr(settings, 'COMMENTS_ALLOW_MODERATOR_UPDATE'))

        # Create a new comment with user_foo
        comment = create_comment(self.publishable, self.publishable.content_type, comment='first', user=self.user_foo)

        # Create a new staff user and assert that they pass the default test
        user_staff = User.objects.create_superuser(username='staff', email='bar@bar.com', password='test')
        tools.assert_true(views.update_comment.user_can_access_comment(user_staff))

        # Try to edit this comment with user_bar (whos IS staff)
        self.client.login(username='staff', password='test')
        response = self.client.get(self.get_url('update', comment.id))

        # Assert that the response is 200 and that the appropriate tpl is being called
        tools.assert_equals(200, response.status_code)
        tools.assert_equals('page/comment_update.html', response.template.name)

    def test_comment_update_with_post(self):
        " Assert that a POST request with valid data successfully updates the comment. "
        # Create a new comment with user_foo
        comment = create_comment(self.publishable, self.publishable.content_type, comment='first', user=self.user_foo)

        # Create a new staff user and assert that they pass the default test
        user_staff = User.objects.create_superuser(username='staff', email='bar@bar.com', password='test')
        tools.assert_true(views.update_comment.user_can_access_comment(user_staff))

        # Instantiate the edit form with
        form = comments.get_form()(target_object=self.publishable)
        form_data = self.get_form_data(form)
        UPDATED_COMMENT_TEXT = 'update me!'
        form_data.update({'comment': UPDATED_COMMENT_TEXT})

        # Try to edit this comment with user_bar (whos IS staff)
        self.client.login(username='staff', password='test')
        self.client.post(self.get_url('update', comment.id), form_data)

        # Refetch the comment from the orm and assert that it has indeed been updated
        comment = comments.get_model().objects.get(id=comment.id)
        tools.assert_equals(UPDATED_COMMENT_TEXT, comment.comment)
        tools.assert_equals(self.user_foo, comment.user)

    @mock.patch.object(views, 'comment_updated')
    def test_comment_updated_signal(self, mock_signal):
        " Assert that the `comment_updated` signal is sent as expected after a comment is edited. "
        # Create a new comment with user_foo
        comment = create_comment(self.publishable, self.publishable.content_type, comment='first', user=self.user_foo)

        # Create a new staff user and assert that they pass the default test
        user_staff = User.objects.create_superuser(username='staff', email='bar@bar.com', password='test')
        tools.assert_true(views.update_comment.user_can_access_comment(user_staff))

        # Instantiate the edit form with
        form = comments.get_form()(target_object=self.publishable)
        form_data = self.get_form_data(form)
        UPDATED_COMMENT_TEXT = 'update me!'
        form_data.update({'comment': UPDATED_COMMENT_TEXT})

        # Try to edit this comment with user_bar (whos IS staff)
        self.client.login(username='staff', password='test')
        self.client.post(self.get_url('update', comment.id), form_data)

        # Assert that the `comment_updated` signal was called
        mock_signal.send.assert_called()
        # mock_signal.send.assert_called_once_with(
        #     sender=comment.__class__,
        #     comment=comment,
        #     updating_user=user_staff,
        #     # date_updated=mock_now
        # )

class TestCommentDetailView(CommentViewTestCase):
    " Unit tests for `ella-comments.views.comment_detail()`. "

    def setUp(self):
        " Run a quick comment count check and factory a request object. "
        super(TestCommentDetailView, self).setUp()
        tools.assert_equals(comments.get_model().objects.count(), 0)
        template_loader.templates['page/comment_list.html'] = ''
        template_loader.templates['404.html'] = ''

    def test_404_raised_if_comment_matching_id_does_not_exist(self):
        " Assert that the view raises a 404 if the comment matching the `comment_id` doesn't exist. "
        INVALID_COMMENT_ID = 4
        response = self.client.get(self.get_url(INVALID_COMMENT_ID))
        tools.assert_equals(404, response.status_code)

    @mock.patch.object(views, '_get_comment_order')
    def test_reverse_ordering_kwarg_is_passed_correctly(self, mock__get_comment_order):
        " Assert that `views._get_comment_order()` is called with the expected args. "
        comment_1 = create_comment(self.publishable, self.publishable.content_type)

        # 1. Call the `comment_detail()` passing no kwargs
        response = self.client.get(self.get_url(comment_1.id))
        tools.assert_equals(response.status_code, 302)

        # Assert that `_get_comment_order()` was called with the publishable and the default `reverse_ordering` value (which is False)
        mock__get_comment_order.assert_called_once_with(self.publishable, None)
        mock__get_comment_order.reset_mock()


        # 2. Call the `comment_detail()` passing passing `reverse_ordering` kwarg
        response = self.client.get(self.get_url(comment_1.id), {'reverse_ordering': '1'})
        tools.assert_equals(response.status_code, 302)

        # Assert that `_get_comment_order()` was called with the publishable and the passed `reverse_ordering` kwarg (which is True)
        mock__get_comment_order.assert_called_once_with(self.publishable, True)

    def test__get_comment_order_util_method(self):
        " Assert that `views._get_comment_order()` returns the expected value.  "
        # 1. Assert True is returned when passing `reverse_ordering` = True
        tools.assert_true(views._get_comment_order(self.publishable, reverse_ordering=True))

        # 2. Assert False is returned when passing `reverse_ordering` = False
        tools.assert_false(views._get_comment_order(self.publishable, reverse_ordering=False))

        # 3. Assert True is returned when passing `reverse_ordering` = None
        tools.assert_true(views._get_comment_order(self.publishable, reverse_ordering=None))

        # 4. Assert False is returned when passing a `content_object` who has the `reverse_comment_ordering` property specified (to False)
        obj = ReverseCommentOrderingPublishable()
        tools.assert_false(obj.reverse_comment_ordering)
        tools.assert_false(views._get_comment_order(obj, reverse_ordering=None))

    @mock.patch.object(views, '_get_results_per_page')
    def test_results_per_page_kwarg_is_passed_correctly(self, mock__get_results_per_page):
        " Assert that `views._get_results_per_page()` is called with the expected args from `views.comment_detail()`. "
        comment_1 = create_comment(self.publishable, self.publishable.content_type)

        # 1. Call the `comment_detail()` passing no kwargs
        response = self.client.get(self.get_url(comment_1.id))
        tools.assert_equals(response.status_code, 302)

        # Assert that `_get_results_per_page()` was called with the publishable and the default `results_per_page` value (which is 10)
        mock__get_results_per_page.assert_called_once_with(self.publishable, 10)
        mock__get_results_per_page.reset_mock()


        # 2. Call the `comment_detail()` passing passing `results_per_page` kwarg
        response = self.client.get(self.get_url(comment_1.id), {'results_per_page': 25})
        tools.assert_equals(response.status_code, 302)

        # Assert that `_get_results_per_page()` was called with the publishable and the passed `results_per_page` kwarg which is 25
        mock__get_results_per_page.assert_called_once_with(self.publishable, 25)

    def test__get_results_per_page_util_method(self):
        " Assert that `views._get_results_per_page()` returns the expected value.  "
        # 1. Assert 10 is returned when passing the 10 as the `results_per_page` arg
        RESULTS_PER_PAGE = 10
        tools.assert_equals(views._get_results_per_page(self.publishable, results_per_page=RESULTS_PER_PAGE), RESULTS_PER_PAGE)

        # 2. Assert that an object can override the return value if it has specified the `comment_results_per_page` property
        obj = ResultsPerPagePublishable()
        tools.assert_equals(obj.comment_results_per_page, OVERRIDDEN_RESULTS_PER_PAGE)
        tools.assert_true(OVERRIDDEN_RESULTS_PER_PAGE != RESULTS_PER_PAGE)
        tools.assert_equals(views._get_results_per_page(obj, results_per_page=RESULTS_PER_PAGE), OVERRIDDEN_RESULTS_PER_PAGE)

    def test_correct_page_in_redirect(self):
        " Assert that `views.comment_detail()` returns an HttpResponseRedirect to the expected location. "
        # Create a handful of comments
        for i in range(0, 22):
            create_comment(self.publishable, self.publishable.content_type)
        tools.assert_false(hasattr(self.publishable, 'results_per_page'))
        tools.assert_false(hasattr(self.publishable, 'reverse_comment_ordering'))

        # Call the `comment_detail()` view to get the absolute url for comment.id == 4 passing no kwargs
        #   `results_per_page` should be 10
        #   `reverse_ordering` should be True
        comment_4 = comments.get_model().objects.get(pk=4)
        response = self.client.get(self.get_url(comment_4.id))
        tools.assert_equals(response.status_code, 302)
        url = urlparse(response['location'])
        tools.assert_equals(url.path, comment_4.content_object.get_absolute_url())
        tools.assert_equals(url.query, 'p=%d&comment_id=%s' % (2, comment_4.id))
        tools.assert_equals(url.fragment, str(comment_4.id))

        # Call the `comment_detail()` view to get the absolute url for comment.id == 4 passing `reverse_ordering` = False
        #   `results_per_page` should be 10
        #   `reverse_ordering` should be False
        comment_4 = comments.get_model().objects.get(pk=4)
        response = self.client.get(self.get_url(comment_4.id), {'reverse_ordering': ''})
        tools.assert_equals(response.status_code, 302)
        url = urlparse(response['location'])
        tools.assert_equals(url.path, comment_4.content_object.get_absolute_url())
        tools.assert_equals(url.query, 'p=%d&comment_id=%s' % (1, comment_4.id))
        tools.assert_equals(url.fragment, str(comment_4.id))

        # Call the `comment_detail()` view to get the absolute url for comment.id == 4 passing `results_per_page` = 1
        #   `results_per_page` should be 1
        #   `reverse_ordering` should be True
        comment_4 = comments.get_model().objects.get(pk=4)
        response = self.client.get(self.get_url(comment_4.id), {'results_per_page': '1'})
        tools.assert_equals(response.status_code, 302)
        url = urlparse(response['location'])
        tools.assert_equals(url.path, comment_4.content_object.get_absolute_url())
        tools.assert_equals(url.query, 'p=%d&comment_id=%s' % (19, comment_4.id))
        tools.assert_equals(url.fragment, str(comment_4.id))
