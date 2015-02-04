from django.db import models
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from requests import Request, codes
from urlparse import urljoin

from .exceptions import SubscriptionError


class AbstractSubscription(models.Model):

    topic = models.URLField(_('Topic'), max_length=255)
    hub = models.URLField(_('Hub'), max_length=255)

    # todo token
    verify_token = models.CharField(
        _('Verify Token'), max_length=255, null=True, blank=True)
    # todo secret
    secret = models.CharField(
        _('Secret'), max_length=255, null=True, blank=True)
    # todo lease_expiration
    lease_expiration = models.DateTimeField(
        _('Lease expiration'), null=True, blank=True)

    INACTIVE = 0
    ACTIVE = 1
    VERIFYING = 2
    DENIED = 3
    STATUS_CODES = {
        INACTIVE: u'inactive',
        ACTIVE: u'active',
        VERIFYING: u'verifying',
        DENIED: u'denied',
    }
    status = models.PositiveSmallIntegerField(
        editable=False, choices=STATUS_CODES.items(), default=INACTIVE)
    verified = models.BooleanField(_('Verified'), default=False)
    updated_at = models.DateTimeField(auto_now=True)
    site = models.ForeignKey(Site, blank=True, null=True)

    @property
    def callback_url(self):
        raise NotImplementedError()

    def full_callback_url(self):
        domain = (self.site or Site.objects.get_current()).domain
        return urljoin("http://" + domain, self.callback_url)

    def subscribe(self, verify_mode=u'sync', lease_seconds=None):
        return self._send_subscription(
            u'subscribe',
            verify_mode=verify_mode,
            lease_seconds=lease_seconds
        )
    subscribe.alters_data = True

    def unsubscribe(self, verify_mode=u'sync'):
        return self._send_subscription(
            u'unsubscribe',
            verify_mode=verify_mode,
        )
    unsubscribe.alters_data = True

    def _send_subscription(self, mode, verify_mode, lease_seconds=None):
        if verify_mode not in (u'sync', u'async'):
            verify_mode = u'sync'
        data = {
            u'hub.callback': self.full_callback_url(),
            u'hub.mode': mode,
            u'hub.topic': self.topic,
            u'hub.verify': verify_mode,
        }
        if self.secret:
            data[u'hub.secret'] = self.secret
        if self.verify_token:
            data[u'hub.verify_token'] = self.verify_token
        if lease_seconds is not None:
            data[u'hub.lease_seconds'] = lease_seconds

        response = self._dispatch(Request(method=u'POST', data=data))

        is_sync = verify_mode == u'sync'
        expected_code = codes.NO_CONTENT if is_sync else codes.ACCEPTED
        succeeded = response.status_code == expected_code

        self._update_subscription_status(
            succeeded, mode == u'subscribe', is_sync)

        if succeeded:
            return response

        err = u"Subscription to topic %s failed with %s status code: %s" % (
            self.topic, response.status_code, response.text)
        raise SubscriptionError(err)

    def _update_subscription_status(self, succeeded, is_subscribe, is_sync):
        if not is_sync:
            # on async, success is returned regardless of verification
            self.verified = False
            self.status = self.VERIFYING
        else:
            # wheather succeeded, verification failed or subscription failed
            self.verified = succeeded
            if succeeded:
                # status changes only if verification succeeded
                self.status = self.ACTIVE if is_subscribe else self.INACTIVE

        self.save()

    def _prep_request(self, request):
        # overwrite to add special auth, headers, data, etc before preparing
        return request.prepare()

    def _dispatch(self, request):
        preped = self._prep_request(request)
        response = Session().send(preped)
        return response

    def __unicode__(self):
        return u"%s %s: %s" % (
            self.topic,
            self.hub,
            self.STATUS_CODES.get(self.status, '')
        )

    class Meta:
        abstract = True
        unique_together = (("topic", "site"),)
