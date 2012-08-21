from datetime import datetime
from django.test import TestCase

from ella.utils.test_helpers import create_basic_categories, create_and_place_a_publishable

from test_ella_comments.helpers import create_comment

from ella.core.cache.redis import client
from ella.utils.timezone import utc_localize, use_tz

from nose import tools, SkipTest

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

