from django.dispatch import Signal

comment_removed = Signal(providing_args=['comment'])
comment_updated = Signal(providing_args=['comment', 'updating_user', 'date_updated'])
