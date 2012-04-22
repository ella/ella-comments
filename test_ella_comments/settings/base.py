from os.path import dirname, join, normpath, pardir

FILE_ROOT = normpath(join(dirname(__file__), pardir))

USE_I18N = True

MEDIA_ROOT = join(FILE_ROOT, 'static')


# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'test_ella.template_loader.load_template_source',
)


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'test_ella_comments.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    join(FILE_ROOT, 'templates'),

)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.media',
    'django.contrib.auth.context_processors.auth',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.redirects',
    'django.contrib.admin',
    'django.contrib.comments',

    'threadedcomments',

    'ella.core',
    'ella.photos',
    'ella.articles',
    'ella_comments',
)

COMMENTS_APP = 'ella_comments'

LISTING_HANDLERS = {
        'default': 'ella.core.managers.ModelListingHandler',
        'most_commented': 'ella_comments.listing_handlers.MostCommentedListingHandler',
        'recently_commented': 'ella_comments.listing_handlers.RecentMostCommentedListingHandler',
        'last_commented': 'ella_comments.listing_handlers.LastCommentedListingHandler',
}

