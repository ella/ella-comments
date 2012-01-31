from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^', include('ella.core.urls')),
)
