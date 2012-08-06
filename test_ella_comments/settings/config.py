from tempfile import gettempdir
from os.path import join

ADMINS = ()
MANAGERS = ADMINS

DEBUG = False
TEMPLATE_DEBUG = DEBUG
DISABLE_CACHE_TEMPLATE = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': join(gettempdir(), 'ella_test_ella_comments.db'),
        'TEST_NAME': join(gettempdir(), 'test_ella_test_ella_comments.db'),
    }
}

TIME_ZONE = 'Europe/Prague'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# Make this unique, and don't share it with anybody.
SECRET_KEY = '88b-01f^x4lh$-s5-hdccnicekg07)niir2g6)93!0#k(=mfv$'

# we want to reset whole cache in test
# until we do that, don't use cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}


LISTINGS_REDIS = {'db': 2}
