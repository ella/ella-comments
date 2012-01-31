"""  
Change the attributes you want to customize
"""

VERSION = (1, 0, 0)

__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))


from threadedcomments.models import ThreadedComment
from threadedcomments.forms import ThreadedCommentForm

def get_model():
    return ThreadedComment

def get_form():
    return ThreadedCommentForm

