from django.dispatch import Signal

comment_removed = Signal(providing_args=['comment'])
