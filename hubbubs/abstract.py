from django.db import models
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.utils import crypto, timezone
from datetime import timedelta

from requests import Request, codes
from urlparse import urljoin

from .exceptions import SubscriptionError
from .settings import USE_SSL, LEASE_SECONDS


class AbstractSubscription(models.Model):

    topic = models.URLField(_('Topic'), max_length=255)
    hub = models.URLField(_('Hub'), max_length=255)
    # this token should be changed only when a new subscription is issued;
    #   the token is also used by the hub when it reaches lease_expiration
    #   and sends a new verification request
    verify_token = models.CharField(
        _('Verify Token'), max_length=255, null=True, blank=True)
    lease_expiration = models.DateTimeField(
        _('Lease expiration'), editable=False, null=True, blank=True)
    secret = models.CharField(
        _('Secret'), max_length=255, null=True, blank=True)

    # active and inactive statuses are set only when verification succeeded
    INACTIVE = 0
    ACTIVE = 1
    # verify status is set only when a async
    #   subscribe/unsubscribe action was submitted
    VERIFYING = 2
    # rejection status is set when async verification is rejected
    SUB_REJECTED = 3
    UNSUB_REJECTED = 4
    STATUS_CODES = {
        INACTIVE: u'inactive',
        ACTIVE: u'active',
        VERIFYING: u'verifying',
        SUB_REJECTED: u'subscribe action rejected',
        UNSUB_REJECTED: u'unsubscribe action rejected',
    }
    status = models.PositiveSmallIntegerField(
        editable=False, choices=STATUS_CODES.items(), default=INACTIVE)
    # used for debugging purposes and will show when the last activity
    #   for this subscription happened
    updated_at = models.DateTimeField(auto_now=True)
    site = models.ForeignKey(Site, blank=True, null=True)

    class Meta:
        abstract = True
        unique_together = (("topic", "site"), )

    def uses_ssl(self):
        return (
            USE_SSL or
            urlparse(self.topic or '').scheme == 'https' or
            urlparse(self.hub or '').scheme == 'https'
        )

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

    def set_expiry(self, seconds):
        if seconds is None:
            self.lease_expiration = None
            return
        self.lease_expiration = timezone.now() + timedelta(seconds=seconds)

    def _send_subscription(self, mode, verify_mode, lease_seconds=None):
        if verify_mode not in (u'sync', u'async'):
            verify_mode = u'sync'
        if self.uses_ssl() and not self.secret:
            # same length as UUID
            self.secret = crypto.get_random_string(length=36)
        if lease_seconds is None:
            lease_seconds = LEASE_SECONDS

        self.set_expiry(lease_seconds)
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

        self._update_status(succeeded, mode == u'subscribe', is_sync)
        self.save()

        if succeeded:
            return response

        err = u"Subscription to topic %s failed with %s status code: %s" % (
            self.topic, response.status_code, response.text)
        raise SubscriptionError(err)

    def _update_status(self, succeeded, is_subscribe, is_sync):
        if not is_sync:
            self.status = self.VERIFYING
            return

        choose = lambda s: s[0] if is_subscribe else s[1]
        if succeeded:
            self.status = choose((self.ACTIVE, self.INACTIVE))
        else:
            self.status = choose((self.SUB_REJECTED, self.UNSUB_REJECTED))

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
