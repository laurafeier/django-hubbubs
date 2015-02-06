from django.db import router
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import classonlymethod
from django.utils.encoding import force_unicode
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.core.exceptions import ImproperlyConfigured
from hubbubs.abstract import AbstractSubscription
from hubbubs.signals import feed_available

import hmac
import hashlib
import feedparser


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

    def _get_object(self, object_id):
        try:
            return self.model.objects.db_manager(
                router.db_for_write(self.model)
            ).get(id=object_id)
        except (self.model.DoesNotExist, ):
            raise Http404

    def get(self, request, object_id, *args, **kwargs):
        subscription = self._get_object(object_id)

        challenge = request.GET.get(u'hub.challenge', '')
        mode = request.GET.get(u'hub.mode', '')
        topic = request.GET.get(u'hub.topic', '')
        verify_token = request.GET.get(u'hub.verify_token', '')
        try:
            lease_seconds = request.GET.get(u'hub.lease_seconds', '')
        except (ValueError, TypeError, ):
            lease_seconds = None

        allowed_modes = ('subscribe', 'unsubscribe', 'denied')
        is_subscribe = mode == 'subscribe'
        choose_status = lambda s: s[0] if is_subscribe else s[1]

        has_correct_token = (
            not subscription.verify_token or
            subscription.verify_token == verify_token)

        if (not all((challenge, mode, topic)) or
                subscription.topic != topic or
                mode not in allowed_modes or
                mode == 'denied' or
                not has_correct_token or
                (is_subscribe and lease_seconds is None)):
            subscription.status = choose_status(
                (AbstractSubscription.SUB_REJECTED,
                 AbstractSubscription.UNSUB_REJECTED)
            )
            subscription.set_expiry(None)
            subscription.save()
            raise Http404

        subscription.status = choose_status(
            (AbstractSubscription.ACTIVE, AbstractSubscription.INACTIVE))
        subscription.set_expiry(lease_seconds)
        subscription.save()

        return HttpResponse(challenge, content_type='text/plain')

    def post(self, request, object_id, *args, **kwargs):
        subscription = self._get_object(object_id)
        message = request.body

        if not message.strip():
            return HttpResponse('')

        if subscription.secret:
            signature = request.META.get('X-Hub-Signature', '')
            if not signature:
                return HttpResponse('')
            secret = subscription.secret.encode('utf-8')
            sha1 = hmac.new(secret, message, hashlib.sha1).hexdigest()
            if force_unicode(signature) != force_unicode("sha1=%s" % sha1):
                return HttpResponse('')

        feed_data = (feedparser.parse(message) or {})
        links = feed_data.get('feed', {}).get('links', [])
        rel_links = {
            (link or {}).get('rel', ''): (link or {}).get('href', '')
            for link in links
        }

        topic = rel_links.get('self', '')
        hub = rel_links.get('hub', '')
        if topic and topic != subscription.topic:
            subscription.topic = topic
        if hub and hub != subscription.hub:
            subscription.hub = hub
        subscription.save()

        # notify new feed available
        feed_available.send(
            sender=self,
            subscription=subscription,
            parsed_feed=feed_data,
            raw_feed=message
        )
        return HttpResponse('')
