from .abstract import AbstractSubscription
from django.core.urlresolvers import reverse


class Subscription(AbstractSubscription):

    @property
    def callback_url(self):
        return reverse('hubbubs_callback', args=[self.id, ])

