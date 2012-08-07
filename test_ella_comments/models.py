from ella.core.models import Publishable


class ReverseCommentOrderingPublishable(Publishable):
    """
    This model is used in the test suite. It has explicitly
    set its `reverse_comment_ordering` property to False to override default
    ordering behavior in `views._get_comment_order()`.
    """
    reverse_comment_ordering = False

OVERRIDDEN_RESULTS_PER_PAGE = 18
class ResultsPerPagePublishable(Publishable):
    """
    This model is used in the test suite. It has explicitly
    set its `comment_results_per_page` property to 18 to override default
    ordering behavior in `views._get_results_per_page()`.
    """
    comment_results_per_page = OVERRIDDEN_RESULTS_PER_PAGE
