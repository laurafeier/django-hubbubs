from django.dispatch import Signal

feed_available = Signal(
    providing_args=["subscription", "parsed_feed", "raw_feed"]
)
