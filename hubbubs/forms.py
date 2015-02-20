from django import forms
from django.utils import crypto, html
from django.utils.safestring import mark_safe
from django.utils.text import get_text_list
from django.utils.translation import ugettext as _
from .settings import LEASE_SECONDS, USE_SSL

# thanks to https://djangosnippets.org/snippets/2312/
class SubmitButtonWidget(forms.CheckboxInput):

    def render(self, name, value, attrs=None):
        return mark_safe(
            '<input type="submit" class="default" name="%s" value="%s">' % (
            html.escape(name), html.escape(value)
        ))


class SubmitButtonField(forms.Field):

    def __init__(self, *args, **kwargs):
        kwargs = kwargs or {}
        kwargs.update({
            "widget": SubmitButtonWidget,
            "required": False,
            "label": ''
        })
        super(SubmitButtonField, self).__init__(*args, **kwargs)

    def clean(self, value):
        return value


class SubscribeForm(forms.ModelForm):
    verify_mode = forms.ChoiceField(
        initial='async', choices=[('sync', ) * 2, ('async', ) * 2])
    lease_seconds = forms.IntegerField(
        initial=LEASE_SECONDS, min_value=1)

    generate_verification_token = forms.BooleanField(initial=True)
    custom_verification_token = forms.CharField(max_length=255)

    generate_secret_key = forms.BooleanField(initial=USE_SSL)
    custom_secret_key = forms.CharField(max_length=255)

    subscribe = SubmitButtonField(initial='Subscribe to topic')

    fieldsets = [
        (None, {
            'fields': [
                ('topic', 'hub', 'site'),
                ('verify_mode', 'lease_seconds'),
                ('generate_verification_token', 'custom_verification_token'),
                ('generate_secret_key', 'custom_secret_key'),
                'subscribe'
            ]
        })
    ]
    readonly = ('topic', 'hub', 'site')
    required_fields = ()

    def clean(self):
        data = self.cleaned_data
        # these should be unchanged
        data.update({
            'hub': self.instance.hub,
            'topic': self.instance.topic,
            'site': self.instance.site,
        })
        if data.get('lease_seconds', None) < 1:
            data['lease_seconds'] = None

        if data.get('generate_verification_token', False):
            data['verify_token'] = crypto.get_random_string(length=36)
        else:
            data['verify_token'] = data.get(
                'custom_verification_token', ''
            ).strip()

        if data.get('generate_secret_key', False):
            data['secret'] = crypto.get_random_string(length=36)
        else:
            data['secret'] = data.get('custom_secret_key', '').strip()

        return data

    def get_changed_fields_msg(self):
        fields = ['lease_seconds', 'verify_mode', 'verify_token', 'secret']
        fields_data = {
            f: self.cleaned_data.get(f, getattr(self.instance, f, ''))
            for f in fields
        }
        fields_changed = [
            "%s: %s" % (f, val) for f, val in fields_data.items() if val]
        return get_text_list(fields_changed, _('and'))

    def save(self, *args, **kwargs):
        commit = kwargs.get('commit', True)
        if not commit:
            return self.instance

        self.instance.subscribe(
            verify_mode=self.cleaned_data.get('verify_mode', 'async'),
            lease_seconds=self.cleaned_data.get('lease_seconds', None)
        )
        return self.instance


class UnsubscribeForm(SubscribeForm):

    subscribe = SubmitButtonField(initial='Unsubscribe from topic')

    fieldsets = [
        (None, {
            'fields': [
                ('topic', 'hub', 'site'),
                'verify_mode',
                ('generate_verification_token', 'custom_verification_token'),
                'subscribe'
            ]
        })
    ]
    readonly = ('topic', 'hub', 'site')
    required_fields = ()

    def save(self, *args, **kwargs):
        commit = kwargs.get('commit', True)
        if not commit:
            return self.instance

        self.instance.unsubscribe(
            verify_mode=self.cleaned_data.get('verify_mode', 'async')
        )
        return self.instance
