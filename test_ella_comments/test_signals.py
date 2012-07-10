from django.test import TestCase

from ella.utils.test_helpers import create_basic_categories, create_and_place_a_publishable

from test_ella_comments.helpers import create_comment
from ella_comments.signals import comment_removed

from nose import tools

SIGNALED_COMMENT = None
def handle_signal(comment, **kwargs):
    global SIGNALED_COMMENT
    SIGNALED_COMMENT = comment.id

def reset_signaled_comment():
    global SIGNALED_COMMENT
    SIGNALED_COMMENT = None

class TestSignals(TestCase):
    def setUp(self):
        super(TestSignals, self).setUp()
        reset_signaled_comment()
        comment_removed.connect(handle_signal)
        create_basic_categories(self)
        create_and_place_a_publishable(self)
        self.comment = create_comment(self.publishable, self.publishable.content_type)

    def tearDown(self):
        comment_removed.disconnect(handle_signal)
        reset_signaled_comment()
        super(TestSignals, self).tearDown()

    def test_deleted_comment_sends_signal(self):
        id = self.comment.id
        tools.assert_equals(SIGNALED_COMMENT, None)
        self.comment.delete()
        tools.assert_equals(SIGNALED_COMMENT, id)

    def test_moderated_comment_sends_signal(self):
        id = self.comment.id
        tools.assert_equals(SIGNALED_COMMENT, None)
        self.comment.is_removed = True
        self.comment.save()
        tools.assert_equals(SIGNALED_COMMENT, id)

    def test_general_comment_save_doesnt_send_signal(self):
        tools.assert_equals(SIGNALED_COMMENT, None)
        self.comment.save()
        tools.assert_equals(SIGNALED_COMMENT, None)
