from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import classonlymethod
from django.shortcuts import get_object_or_404
from django.core.exceptions import ImproperlyConfigured
from hubbubs.abstract import AbstractSubscription


class AbstractSubscriberCallback(generic.View):

    model = None

    @classonlymethod
    def as_view(cls, **initkwargs):
        model = initkwargs.pop('model', None)
        cls.model = cls.model or model
        if not cls.model or not issubclass(cls.model, AbstractSubscription):
            raise ImproperlyConfigured(
                "%s is missing a concrete model, subclass of %s." % (
                    cls.__name__,
                    AbstractSubscription.__name__
                )
            )
        return super(AbstractSubscriberCallback, cls).as_view(**initkwargs)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(SubscriberCallback, self).dispatch(*args, **kwargs)

    def get(self, request, object_id, *args, **kwargs):
        subscription = get_object_or_404(self.model, id=object_id)

    def post(self, request, object_id, *args, **kwargs):
        subscription = get_object_or_404(self.model, id=object_id)
