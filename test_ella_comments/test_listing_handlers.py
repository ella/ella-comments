import mock

from datetime import datetime

from django.contrib import comments
from django.test import TestCase

from ella.core.cache.redis import client
from ella.utils.test_helpers import create_basic_categories, create_and_place_a_publishable
from ella.utils.timezone import utc_localize, use_tz

from ella_comments import listing_handlers

from nose import tools, SkipTest

from test_ella_comments.helpers import create_comment


class TestListingHandlers(TestCase):
    def setUp(self):
        if not client:
            raise SkipTest()

        super(TestListingHandlers, self).setUp()
        create_basic_categories(self)
        create_and_place_a_publishable(self)
        client.flushdb()

    def test_aa(self):
        day = datetime.now().strftime('%Y%m%d')
        create_comment(self.publishable, self.publishable.content_type, user_name='kvbik', submit_date=utc_localize(datetime(2010, 10, 10, 10, 10, 10)))
        ct_id = self.publishable.content_type_id
        tools.assert_equals(set([
            'slidingccount:WINDOWS',
            'slidingccount:KEYS',

            'comcount:2',
            'lastcom:2',
            'slidingccount:2',

            'comcount:c:1',
            'comcount:c:2',
            'lastcom:c:1',
            'lastcom:c:2',
            'slidingccount:c:1',
            'slidingccount:c:2',

            'lastcom:d:1',
            'lastcom:d:2',
            'comcount:d:1',
            'comcount:d:2',
            'slidingccount:d:1',
            'slidingccount:d:2',

            'lastcom:ct:%d' % ct_id,
            'comcount:ct:%d' % ct_id,
            'slidingccount:ct:%d' % ct_id,


            'lastcom:pub:%d:1' % ct_id,
            'comcount:pub:%d:1' % ct_id,


            'slidingccount:2:%s' % day,
            'slidingccount:c:1:%s' % day,
            'slidingccount:c:2:%s' % day,
            'slidingccount:d:1:%s' % day,
            'slidingccount:d:2:%s' % day,
            'slidingccount:ct:%d:%s' % (ct_id, day),

        ]), set(client.keys('*')))

        if use_tz:
            # timestamps are stored in utc time
            tstamp = '1286705410.0'
        else:
            tstamp = '1286698210.0'
        tools.assert_equals({'submit_date': tstamp, 'user_id': '', 'username': 'kvbik', 'comment': '', 'url': ''}, client.hgetall('lastcom:pub:%d:1' % ct_id))
        tools.assert_equals('1', client.get('comcount:pub:%d:1' % ct_id))

class TestCommentPostSaveSignalHandler(TestListingHandlers):
    " Unit tests for `ella_comments.listing_handlers.comment_post_save()`. "
    def setUp(self):
        super(TestCommentPostSaveSignalHandler, self).setUp()

        # Assert that no comments are in the system
        tools.assert_equals(comments.get_model()._default_manager.count(), 0)

        # Assert that the `publishable`'s comment count does not exist yet
        tools.assert_false(client.exists(listing_handlers.COMCOUNT_KEY % (self.publishable.content_type_id, self.publishable.pk)))

    def _build_publishable_comment_count_key(self, publishable):
        " Util method to consistently build the comment count key for a publishable. "
        return listing_handlers.COMCOUNT_KEY % (publishable.content_type_id, publishable.pk)

    def _create_comment(self):
        " Util method to create and return a new commnt. "
        return create_comment(
            self.publishable,
            self.publishable.content_type,
            user_name='kvbik',
            submit_date=utc_localize(datetime(2010, 10, 10, 10, 10, 10))
        )

    def test_no_change_to_comment_publicity(self):
        """
        Assert that no change made to the `is_public` or `is_removed` properties of a
        comment result in no changes to the comment count or last comment keys of the content object.
        """
        # Create a new public comment on the publishable
        comment = self._create_comment()
        tools.assert_equals(comments.get_model()._default_manager.count(), 1)
        tools.assert_equals(comments.get_model()._default_manager.filter(is_public=True, is_removed=False).count(), 1)

        # Assert that the comment count key on the publishable was set correctly to 1
        tools.assert_equals(
            int(client.get(self._build_publishable_comment_count_key(self.publishable))),
            1
        )

        # Update this comment (but do not change "publicity") and assert that
        # nothing has changed regarding the comment count on the publishable
        comment.comment = 'New comment text'
        tools.assert_true(comment.is_public)
        tools.assert_false(comment.is_removed)
        comment.save()

        # Assert that the comment count key on the publishable is still set correctly to 1
        tools.assert_equals(
            int(client.get(self._build_publishable_comment_count_key(self.publishable))),
            1
        )

    def test_modify_comment_publicity(self):
        """
        Assert that a modification made to the `is_public` or `is_removed` properties of a
        comment result in changes to the comment count of the content object.
        """
        # Create a new public comment on the publishable
        comment = self._create_comment()
        tools.assert_equals(comments.get_model()._default_manager.count(), 1)
        tools.assert_equals(comments.get_model()._default_manager.filter(is_public=True, is_removed=False).count(), 1)

        # Assert that the comment count key on the publishable was set correctly to 1
        tools.assert_equals(
            int(client.get(self._build_publishable_comment_count_key(self.publishable))),
            1
        )

        # Update this comment (and change "publicity" of it)
        comment.is_public = False
        comment.save()

        # Assert that the comment count key on the publishable has been updated to reflect
        # the fact that there are 0 public comments associated to it.
        tools.assert_equals(
            int(client.get(self._build_publishable_comment_count_key(self.publishable))),
            0
        )

    @mock.patch.object(listing_handlers, 'client')
    def test_client_invoked(self, mock_client):
        """
        Call `comment_post_save()` with a comment that has been modified,
        and assert that the client was not invoked.
        """
        # Create a new public comment
        comment = self._create_comment()

        # Programatically set the `__pub_info` data on the comment
        setattr(comment, '__pub_info', {
            'is_public': False,
            'is_removed': True,
        })

        # Pass this comment to the `comment_post_save()` signal handler
        listing_handlers.comment_post_save(comment)

        # Assert that that client.set() was called w/ the appropriate args
        mock_client.set.assert_called_with(
            self._build_publishable_comment_count_key(self.publishable),
            1
        )

    @mock.patch.object(listing_handlers, 'client')
    def test_client_not_invoked(self, mock_client):
        """
        Call `comment_post_save()` with a comment that has not been modified,
        and assert that `client.set()` was not invoked.
        """
        # Create a new public comment
        comment = self._create_comment()

        # Programatically set the `__pub_info` data on the comment (but DON'T CHANGE ANYTHING)
        setattr(comment, '__pub_info', {
            'is_public': True,
            'is_removed': False,
        })

        # Pass this comment to the `comment_post_save()` signal handler
        listing_handlers.comment_post_save(comment)

        # Assert that the `set` method was NOT called
        tools.assert_false(mock_client.set.called)
