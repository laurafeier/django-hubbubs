from django.template import Template, RequestContext
from django.forms.models import modelform_factory
from django.contrib import messages
from django.contrib import admin
from django.contrib.admin.util import flatten_fieldsets
from django.contrib.admin.views.main import IS_POPUP_VAR
from django.conf.urls.defaults import patterns, url
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import timesince_filter
from django.conf import settings
from .models import Subscription
from .forms import SubscribeForm, UnsubscribeForm
from .exceptions import SubscriptionError


class AbstractSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('topic', 'status',
                    'lease_expires_in', 'last_update', 'site',
                    'custom_actions')

    def lease_expires_in(self, subscription):
        return timesince_filter(subscription.lease_expiration)

    def last_update(self, subscription):
        return timesince_filter(subscription.updated_at)

    def custom_actions(self, subscription):
        link_html = "<li><a href='%s' class='link'>%s</a></li>"
        list_style = "float: none; margin: 0px; padding: 0px;"

        def for_html_link(action_name):
            info = (
                self.model._meta.app_label,
                self.model._meta.module_name,
                action_name
            )
            url_name = 'admin:hubbubs-%s-%s-%s' % info
            action_url = reverse(url_name, args=[subscription.pk])
            return (action_url, action_name.capitalize())

        return (
            '<ul style="%s" class="object-tools">' % list_style +
            link_html % for_html_link('subscribe') +
            link_html % for_html_link('unsubscribe') +
            '</ul>'
        )
    custom_actions.short_description = 'Actions'
    custom_actions.allow_tags = True

    def get_urls(self):
        urls = super(AbstractSubscriptionAdmin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.module_name
        url_patterns = patterns('',
            url(r'^(?P<sub_id>\d+)/subscribe/$',
                self.admin_site.admin_view(self.subscribe),
                name='hubbubs-%s-%s-subscribe' % info),
            url(r'^(?P<sub_id>\d+)/unsubscribe/$',
                self.admin_site.admin_view(self.unsubscribe),
                name='hubbubs-%s-%s-unsubscribe' % info),
        )
        url_patterns.extend(urls)
        return url_patterns

    def get_readonly_fields(self, request, obj=None):
        # site should not change after subscription is created since
        #   domain for that subscription will no longer match
        readonly_fields = ['secret', 'verify_token']
        if obj and obj.pk:
            readonly_fields.append('site')

        self.readonly_fields = readonly_fields
        return super(AbstractSubscriptionAdmin, self)\
            .get_readonly_fields(request, obj)

    def _custom_action_view(self, request, sub_id, formCls, action_name):
        subscription = get_object_or_404(self.model, pk=sub_id)
        is_popup = IS_POPUP_VAR in request.REQUEST
        if (request.method not in ('POST', 'GET') or is_popup or
                not self.has_change_permission(request, subscription)):
            raise PermissionDenied

        opts = self.model._meta

        formCls = modelform_factory(self.model, form=formCls)
        data, files = None, None
        if request.method == 'POST':
            data, files = request.POST, request.FILES
        form = formCls(data, files, instance=subscription)

        if hasattr(form, 'required_fields'):
            required_fields = getattr(form, 'required_fields') or ()
            for field in form.fields.values():
                field.required = field in required_fields

        if request.method == 'POST' and form.is_valid():
            try:
                new_object = form.save(commit=True)
            except (SubscriptionError, ) as err:
                messages.error(request, str(err))
            else:
                changed_fields = getattr(
                    form, 'get_changed_fields_msg',
                    lambda: form.changed_data
                )
                change_message = "%s requested for topic %s: %s" % (
                    action_name.capitalize(),
                    new_object.topic,
                    changed_fields()
                )
                self.log_change(request, new_object, change_message)
                messages.info(request, change_message)
                return HttpResponseRedirect(
                    reverse('admin:%s_%s_changelist' % (
                        opts.app_label, opts.module_name)
                    )
                )

        adminForm = admin.helpers.AdminForm(
            form,
            getattr(form, 'fieldsets', [(None, {'fields': form.fields})]),
            getattr(form, 'prepopulated', {}),
            getattr(form, 'readonly', []),
            model_admin=self
        )

        context = RequestContext(request)
        context.update({
            'title': 'Topic %s' % action_name,
            'adminform': adminForm,
            'object_id': subscription.id,
            'original': subscription,
            'media': self.media + adminForm.media,
            'errors': admin.helpers.AdminErrorList(form, []),
            'is_popup': is_popup,
            'app_label': opts.app_label,
            'opts': opts,
            'change': True,
            'add': False
        })

        no_submit_row_template = Template(
            "{% extends 'admin/change_form.html' %}" +
            "{% block submit_buttons_bottom %}{% endblock %}"
        )
        content = no_submit_row_template.render(context)
        return HttpResponse(content)

    def subscribe(self, request, sub_id):
        return self._custom_action_view(
            request, sub_id, SubscribeForm, 'subscription')

    def unsubscribe(self, request, sub_id):
        return self._custom_action_view(
            request, sub_id, UnsubscribeForm, 'unsubscription')


class SubscriptionAdmin(AbstractSubscriptionAdmin):
    pass


if 'hubbubs' in settings.INSTALLED_APPS:
    admin.site.register(Subscription, SubscriptionAdmin)
